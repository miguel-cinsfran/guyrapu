# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Prueba el medio de la escena de Guyrapu contra el OBS real de esta PC.

Abre OBS si está cerrado, arma un PNG de un color sólido y comprueba con una
captura de la escena que el centro tiene ese color. Después arma un WAV de
tres segundos con una ganancia, comprueba que reproduce y que su volumen es
esa ganancia, lo arma otra vez y comprueba que el cursor volvió cerca de cero.
También comprueba que sin tarjeta el elemento queda apagado y que mostrarla
lo vuelve a encender. Al final suelta el medio, quita las dos entradas y
comprueba que no quedó ninguna.

Se corre a mano, porque abre OBS:

    python qa/medio_obs_real.py
"""

from __future__ import annotations

import array
import base64
import math
import struct
import sys
import tempfile
import time
import wave
import zlib
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from guyrapu.obs import escena_guyrapu  # noqa: E402
from guyrapu.obs import estilos_aviso  # noqa: E402
from guyrapu.obs import medio_obs  # noqa: E402
from guyrapu.obs import obs_activacion  # noqa: E402
from guyrapu.obs import obs_cliente  # noqa: E402
from guyrapu.obs import obs_lanzador  # noqa: E402

COLOR = (0x11, 0x22, 0xCC)
ESPERA_TRAS_ABRIR = 5.0
SEGUNDOS_WAV = 3
MUESTRAS_POR_SEGUNDO = 44100


def _datos(respuesta):
    return (respuesta or {}).get("responseData", respuesta or {})


def _pedir(cliente, tipo, datos=None):
    return _datos(cliente.pedir(tipo, datos))


def _trozos(nombre, cuerpo):
    return (struct.pack(">I", len(cuerpo)) + nombre + cuerpo
            + struct.pack(">I", zlib.crc32(nombre + cuerpo) & 0xFFFFFFFF))


def _png_plano(ancho, alto, color):
    """Un PNG RGB de un color sólido, armado con la biblioteca estándar."""
    crudo = (b"\x00" + bytes(color) * ancho) * alto
    return (b"\x89PNG\r\n\x1a\n"
            + _trozos(b"IHDR", struct.pack(">IIBBBBB", ancho, alto, 8, 2,
                                           0, 0, 0))
            + _trozos(b"IDAT", zlib.compress(crudo))
            + _trozos(b"IEND", b""))


def _escribir_wav(ruta):
    with wave.open(str(ruta), "w") as oleada:
        oleada.setnchannels(1)
        oleada.setsampwidth(2)
        oleada.setframerate(MUESTRAS_POR_SEGUNDO)
        muestras = array.array(
            "h", (int(16383 * math.sin(
                2 * math.pi * 440 * i / MUESTRAS_POR_SEGUNDO))
                for i in range(MUESTRAS_POR_SEGUNDO * SEGUNDOS_WAV)))
        oleada.writeframes(muestras.tobytes())


def _captura_bmp(cliente, fuente):
    datos = _pedir(cliente, "GetSourceScreenshot", {
        "sourceName": fuente, "imageFormat": "bmp", "imageWidth": 160})
    imagen = str(datos.get("imageData", "") or "")
    if "," in imagen:
        imagen = imagen.split(",", 1)[1]
    return base64.b64decode(imagen)


def _pixel_central(bmp):
    if len(bmp) < 54 or bmp[:2] != b"BM":
        return None
    ancho, alto = struct.unpack("<ii", bmp[18:26])
    bits = struct.unpack("<H", bmp[28:30])[0]
    inicio = struct.unpack("<I", bmp[10:14])[0]
    if ancho <= 0 or not alto or bits not in (24, 32):
        return None
    paso = ((ancho * (bits // 8) + 3) // 4) * 4
    base = inicio + (abs(alto) // 2) * paso + (ancho // 2) * (bits // 8)
    return (bmp[base + 2], bmp[base + 1], bmp[base])


def _parecido(pixel, color):
    return (pixel is not None
            and all(abs(uno - otro) <= 8 for uno, otro in zip(pixel, color)))


def _entradas(cliente):
    return {entrada.get("inputName", "") for entrada in
            _pedir(cliente, "GetInputList").get("inputs", ())}


def _habilitada(cliente, nombre):
    item = next((item for item in _pedir(cliente, "GetSceneItemList", {
        "sceneName": escena_guyrapu.ESCENA}).get("sceneItems", ())
        if item.get("sourceName") == nombre), None)
    return bool(item and item.get("sceneItemEnabled"))


def _estado(cliente):
    return _pedir(cliente, "GetMediaInputStatus",
                  {"inputName": medio_obs.MEDIO})


def _volumen(cliente):
    return float(_pedir(cliente, "GetInputVolume", {
        "inputName": medio_obs.MEDIO}).get("inputVolumeDb") or 0)


def _reproduciendo(estado):
    return "PLAYING" in str(estado.get("mediaState", "")).upper()


def _esperar_cursor(cliente, minimo, tope=5.0):
    limite = time.monotonic() + tope
    cursor = 0.0
    while time.monotonic() < limite:
        estado = _estado(cliente)
        cursor = float(estado.get("mediaCursor") or 0)
        if _reproduciendo(estado) and cursor >= minimo:
            return cursor
        time.sleep(0.2)
    return cursor


def _esperar_color(cliente, color, tope=5.0):
    limite = time.monotonic() + tope
    pixel = None
    while time.monotonic() < limite:
        pixel = _pixel_central(_captura_bmp(cliente, escena_guyrapu.ESCENA))
        if _parecido(pixel, color):
            return pixel
        time.sleep(0.2)
    return pixel


def _restos(cliente):
    nombres = {medio_obs.IMAGEN, medio_obs.MEDIO}
    return sorted(_entradas(cliente) & nombres)


def _esperar_restos(cliente, esperar=time.sleep):
    limite = time.monotonic() + 5
    while True:
        restos = _restos(cliente)
        if not restos or time.monotonic() >= limite:
            return restos
        esperar(0.5)


def _comprobar(nombre, bien, fallos):
    if bien:
        print(f"Bien: {nombre}.")
    else:
        print(f"Falla: {nombre}.")
        fallos.append(nombre)


def _probar(cliente, capa, fallos):
    capa.preparar()
    medio = medio_obs.MedioObs(cliente)
    carpeta = Path(tempfile.mkdtemp(prefix="qa-medio-obs-"))
    png = carpeta / "color.png"
    png.write_bytes(_png_plano(320, 180, COLOR))
    wav = carpeta / "tono.wav"
    _escribir_wav(wav)
    try:
        medio.armar(png, "imagen")
        pixel = _esperar_color(cliente, COLOR)
        _comprobar("imagen: el centro de la escena tiene el color",
                   _parecido(pixel, COLOR), fallos)
        capa.mostrar_sin_tarjeta()
        _comprobar("escena: sin tarjeta el elemento queda apagado",
                   not _habilitada(cliente, escena_guyrapu.TARJETA), fallos)
        capa.mostrar("prueba", estilos_aviso.FABRICA[0])
        _comprobar("escena: mostrar vuelve a encender la tarjeta",
                   _habilitada(cliente, escena_guyrapu.TARJETA), fallos)
        medio.armar(wav, "sonido", -6.0)
        cursor = _esperar_cursor(cliente, 250)
        _comprobar("sonido: reproduce desde el principio", cursor >= 250,
                   fallos)
        _comprobar("sonido: el volumen es la ganancia del medio",
                   abs(_volumen(cliente) + 6.0) <= 0.1, fallos)
        medio.armar(wav, "sonido", -6.0)
        estado = _estado(cliente)
        cursor = float(estado.get("mediaCursor") or 0)
        _comprobar("sonido: al armarlo otra vez volvió cerca de cero",
                   _reproduciendo(estado) and cursor < 1000, fallos)
        capa.ocultar()
        medio.soltar()
        _comprobar("soltar: las dos entradas quedaron apagadas",
                   not _habilitada(cliente, medio_obs.IMAGEN)
                   and not _habilitada(cliente, medio_obs.MEDIO), fallos)
        _comprobar("soltar: no borró las dos entradas",
                   {medio_obs.IMAGEN, medio_obs.MEDIO} <= _entradas(cliente),
                   fallos)
        capa.quitar_todo()
        restos = _esperar_restos(cliente)
        if restos:
            print("Quedó: " + ", ".join(restos))
        _comprobar("quitar todo: no quedó ninguna de las dos entradas",
                   not restos, fallos)
    finally:
        capa.quitar_todo()


def main():
    estaba_abierto = obs_activacion.obs_esta_en_ejecucion()
    cliente = obs_cliente.ClienteObs(obs_cliente.leer_ajustes())
    capa = escena_guyrapu.EscenaGuyrapu(cliente)
    fallos = []
    codigo = 0
    try:
        obs_lanzador.asegurar_obs(cliente.conectar)
        if not estaba_abierto:
            time.sleep(ESPERA_TRAS_ABRIR)
        if not cliente.conectado:
            cliente.conectar()
        _probar(cliente, capa, fallos)
    except Exception as error:
        print(f"Falla: {error}")
        codigo = 1
    finally:
        try:
            cliente.cerrar()
        except Exception as error:
            print(f"Aviso: no se pudo cerrar la conexión con OBS: {error}")
        if not estaba_abierto:
            obs_lanzador.cerrar_obs()
    return codigo or (1 if fallos else 0)


if __name__ == "__main__":
    sys.exit(main())
