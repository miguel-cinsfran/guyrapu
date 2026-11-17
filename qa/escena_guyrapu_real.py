# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Prueba la escena propia de Guyrapu contra el OBS real de esta PC.

Abre OBS si está cerrado, arma la capa, muestra cada estilo de fábrica con
la misma frase, guarda la captura de la escena del programa, comprueba que
la tarjeta cae dentro del área segura y oculta. Después prueba un texto de
200 caracteres con el estilo Tarjeta. Al final quita todo y comprueba que no
quedó ninguna escena, entrada ni PNG.

Se corre a mano, porque abre ventanas:

    python qa/escena_guyrapu_real.py
"""

from __future__ import annotations

import base64
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from guyrapu.core import paths  # noqa: E402
from guyrapu.interaction import zonas  # noqa: E402
from guyrapu.obs import escena_guyrapu  # noqa: E402
from guyrapu.obs import estilos_aviso  # noqa: E402
from guyrapu.obs import obs_activacion  # noqa: E402
from guyrapu.obs import obs_cliente  # noqa: E402
from guyrapu.obs import obs_lanzador  # noqa: E402

FRASE = ("Seguime en Instagram: @guyrapu. Directo nuevo todos los viernes "
         "a las 21.")
TEXTO_LARGO = ("Seguime en Instagram y no te pierdas el directo de los "
               "viernes a las 21. " * 3)[:200]
SALIDA = RAIZ / "qa" / "salida" / "capa"
ESPERA_TRAS_ABRIR = 5.0


def _datos(respuesta):
    return (respuesta or {}).get("responseData", respuesta or {})


def _pedir(cliente, tipo, datos=None, parada=None):
    return _datos(cliente.pedir(tipo, datos, parada))


def _programa(cliente):
    datos = _pedir(cliente, "GetCurrentProgramScene")
    return datos.get("currentProgramSceneName", "") or ""


def _capturar(cliente, fuente):
    datos = _pedir(cliente, "GetSourceScreenshot", {
        "sourceName": fuente, "imageFormat": "png"})
    imagen = str(datos.get("imageData", "") or "")
    if "," in imagen:
        imagen = imagen.split(",", 1)[1]
    return base64.b64decode(imagen)


def _guardar(png, clave):
    SALIDA.mkdir(parents=True, exist_ok=True)
    (SALIDA / f"{clave}.png").write_bytes(png)


def _dentro_del_area(area, tarjeta):
    x, y, ancho, alto = area
    return (tarjeta.x >= x and tarjeta.y >= y
            and tarjeta.x + tarjeta.ancho <= x + ancho
            and tarjeta.alto + tarjeta.y <= y + alto)


def _lineas(cliente):
    datos = _pedir(cliente, "GetInputSettings",
                   {"inputName": escena_guyrapu.TEXTO})
    escrito = str(datos.get("inputSettings", {}).get("text", "") or "")
    return escrito.count("\n") + 1


def _restos(cliente):
    escenas = {escena.get("sceneName", "") for escena in
               _pedir(cliente, "GetSceneList").get("scenes", ())}
    entradas = {entrada.get("inputName", "") for entrada in
                _pedir(cliente, "GetInputList").get("inputs", ())}
    nuestras = sorted({escena_guyrapu.ESCENA, escena_guyrapu.TARJETA}
                      & escenas)
    fuentes = sorted({escena_guyrapu.TEXTO, escena_guyrapu.FONDO}
                     & entradas)
    pngs = sorted(ruta.name for ruta in
                  paths.fondos_de_avisos().glob("*.png"))
    restos = []
    if nuestras:
        restos.append("escenas: " + ", ".join(nuestras))
    if fuentes:
        restos.append("entradas: " + ", ".join(fuentes))
    if pngs:
        restos.append("PNG: " + ", ".join(pngs))
    return restos


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
    lienzo = _pedir(cliente, "GetVideoSettings")
    area = zonas.area_segura(int(lienzo.get("baseWidth") or 0),
                             int(lienzo.get("baseHeight") or 0))
    for estilo in estilos_aviso.FABRICA:
        tarjeta = capa.mostrar(FRASE, estilo)
        _guardar(_capturar(cliente, _programa(cliente)), estilo["clave"])
        _comprobar(f"estilo {estilo['clave']}: tarjeta dentro del área segura",
                   _dentro_del_area(area, tarjeta), fallos)
        capa.ocultar()
    tarjeta = capa.mostrar(TEXTO_LARGO, estilos_aviso.FABRICA[2])
    _comprobar("texto largo: quedó en más de una línea",
               _lineas(cliente) > 1, fallos)
    _comprobar("texto largo: tarjeta dentro del área segura",
               _dentro_del_area(area, tarjeta), fallos)
    capa.ocultar()
    capa.quitar_todo()
    restos = _esperar_restos(cliente)
    if restos:
        print("Quedó: " + " ".join(restos))
    _comprobar("quitar todo: no queda nada de Guyrapu",
               not restos, fallos)


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
