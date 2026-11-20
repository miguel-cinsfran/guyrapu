# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Muestra una encuesta y un mensaje automático en el OBS real de esta PC.

Abre OBS si está cerrado, crea una `CapaVideo`, fija una encuesta, la pone al
día con un voto más y comprueba que la fuente de texto cambia sin ocultarse.
Después le suma dos mensajes de tres segundos con los estilos Tarjeta y Banda
y comprueba con capturas de la escena del programa que la tarjeta no se ve
antes de la entrada, que se ve a mitad de sus segundos y que al final no queda
la escena «Guyrapu» al aire. Después quita todo y, si abrió OBS, lo cierra.
Una línea por comprobación y sale con 1 si alguna falla.

Se corre a mano, porque abre OBS:

    python qa/capa_video_real.py
"""

from __future__ import annotations

import base64
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import wx  # noqa: E402

from guyrapu.obs import escena_guyrapu, obs_activacion, obs_cliente  # noqa: E402
from guyrapu.obs import obs_lanzador  # noqa: E402
from guyrapu.ui.capa_video import CapaVideo  # noqa: E402

SALIDA = RAIZ / "qa" / "salida" / "capa_video"
ESPERA_TRAS_ABRIR = 5.0
TOPE_VIDEO = 20.0


def _datos(respuesta):
    return (respuesta or {}).get("responseData", respuesta or {}) or {}


def _pedir(cliente, tipo, datos=None):
    return _datos(cliente.pedir(tipo, datos))


def _programa(cliente) -> str:
    return _pedir(cliente, "GetCurrentProgramScene").get(
        "currentProgramSceneName", "") or ""


def _fuentes_de(cliente, escena) -> list:
    datos = _pedir(cliente, "GetSceneItemList", {"sceneName": escena})
    return [item.get("sourceName", "") for item in datos.get("sceneItems", ())]


def _captura(cliente, clave) -> Path:
    escena = _programa(cliente)
    datos = _pedir(cliente, "GetSourceScreenshot", {
        "sourceName": escena, "imageFormat": "png"})
    imagen = str(datos.get("imageData", "") or "")
    if "," in imagen:
        imagen = imagen.split(",", 1)[1]
    SALIDA.mkdir(parents=True, exist_ok=True)
    ruta = SALIDA / f"{clave}.png"
    ruta.write_bytes(base64.b64decode(imagen))
    return ruta


def _iguales(una, otra) -> bool:
    primera = wx.Image(str(una), wx.BITMAP_TYPE_PNG)
    segunda = wx.Image(str(otra), wx.BITMAP_TYPE_PNG)
    return bytes(primera.GetData()) == bytes(segunda.GetData())


def _paso(bucle) -> None:
    while bucle.Pending():
        bucle.Dispatch()
    bucle.ProcessIdle()
    time.sleep(0.02)


def _bombear(bucle, segundos) -> None:
    limite = time.monotonic() + segundos
    while time.monotonic() < limite:
        _paso(bucle)


def _esperar(bucle, condicion, segundos) -> bool:
    limite = time.monotonic() + segundos
    while time.monotonic() < limite:
        if condicion():
            return True
        _paso(bucle)
    return condicion()


def _comprobar(nombre, bien, fallos) -> None:
    if bien:
        print(f"Bien: {nombre}.")
    else:
        print(f"Falla: {nombre}.")
        fallos.append(nombre)


def _limpiar(capa) -> None:
    for que, accion in (
            ("detener el temporizador", capa._timer.Stop),
            ("cerrar el animador", capa._animador.cerrar),
            ("quitar todo de OBS", capa._escena.quitar_todo),
            ("cerrar la conexión con OBS", capa._cliente.cerrar)):
        try:
            accion()
        except Exception as error:
            print(f"Aviso: no se pudo {que}: {error}")


def _texto_del_video(cliente) -> str:
    """El texto que tiene ahora la fuente de texto de la tarjeta."""
    datos = _pedir(cliente, "GetInputSettings",
                   {"inputName": escena_guyrapu.TEXTO})
    texto = str(datos.get("inputSettings", {}).get("text", "") or "")
    return " ".join(texto.split())


def _fuente_de_texto_visible(cliente) -> bool:
    """Si la fuente de texto de la tarjeta está habilitada en su escena."""
    datos = _pedir(cliente, "GetSceneItemList",
                   {"sceneName": escena_guyrapu.TARJETA})
    item = next((candidato for candidato in datos.get("sceneItems", ())
                 if candidato.get("sourceName") == escena_guyrapu.TEXTO), None)
    return bool(item is not None and item.get("sceneItemEnabled"))


def _probar_encuesta(marco, cliente, fallos) -> None:
    """Fija una encuesta, la pone al día y comprueba que el texto no parpadea."""
    from guyrapu.interaction.cola_pantalla import Pieza

    capa = CapaVideo(marco)
    bucle = wx.GUIEventLoop()
    encuesta = Pieza(tipo="encuesta", texto="Encuesta de prueba", segundos=0,
                     datos={"estilo": "tarjeta"})
    al_dia = Pieza(tipo="encuesta", texto="Encuesta de prueba, 2 votos",
                   segundos=0, datos={"estilo": "tarjeta"})
    try:
        with wx.EventLoopActivator(bucle):
            capa.fijar_encuesta(encuesta)
            _comprobar(
                "la encuesta queda fija y se ve",
                _esperar(bucle, lambda: "Encuesta en el vídeo: "
                         "Encuesta de prueba" in capa.describir(), TOPE_VIDEO),
                fallos)
            _comprobar(
                "la fuente de texto tiene la encuesta",
                "Encuesta de prueba" in _texto_del_video(cliente), fallos)
            capa.poner_al_dia_encuesta(al_dia)
            visibles = []
            actualizada = False
            limite = time.monotonic() + TOPE_VIDEO
            while time.monotonic() < limite:
                visibles.append(_fuente_de_texto_visible(cliente))
                if "Encuesta de prueba, 2 votos" in _texto_del_video(cliente):
                    actualizada = True
                    break
                _paso(bucle)
            visibles.append(_fuente_de_texto_visible(cliente))
            _comprobar("la encuesta se pone al día con el texto nuevo",
                       actualizada, fallos)
            _comprobar("la fuente de texto no se oculta al ponerse al día",
                       all(visibles), fallos)
            capa.quitar_encuesta()
            _comprobar(
                "al quitarla deja de verse",
                _esperar(bucle, lambda: capa.describir()
                         == "No hay nada en el vídeo.", TOPE_VIDEO),
                fallos)
            programa = _programa(cliente)
            _comprobar("al quitarla no queda la escena Guyrapu al aire",
                       escena_guyrapu.ESCENA not in _fuentes_de(
                           cliente, programa), fallos)
    finally:
        _limpiar(capa)


def _probar(marco, cliente, fallos) -> None:
    _probar_encuesta(marco, cliente, fallos)
    capa = CapaVideo(marco)
    bucle = wx.GUIEventLoop()
    try:
        with wx.EventLoopActivator(bucle):
            antes = _captura(cliente, "antes")
            capa.agregar({"texto": "Mensaje de prueba en Tarjeta",
                          "nombre": "Tarjeta", "estilo": "tarjeta",
                          "segundos_pantalla": 3})
            capa.agregar({"texto": "Mensaje de prueba en Banda",
                          "nombre": "Banda", "estilo": "banda",
                          "segundos_pantalla": 3})
            previa = _captura(cliente, "previa")
            _comprobar("antes de la entrada no se ve nada de la tarjeta",
                       _iguales(antes, previa), fallos)
            _esperar(bucle, lambda: "En el vídeo:" in capa.describir(),
                     TOPE_VIDEO)
            _bombear(bucle, 0.5)
            medio = _captura(cliente, "medio")
            _comprobar("a mitad de los segundos se ve la tarjeta",
                       not _iguales(antes, medio), fallos)
            _esperar(bucle, lambda: capa.describir()
                     == "En el vídeo: Mensaje de prueba en Banda.", TOPE_VIDEO)
            _esperar(bucle, lambda: capa.describir() == "No hay nada en el vídeo.",
                     TOPE_VIDEO)
            programa = _programa(cliente)
            al_aire = escena_guyrapu.ESCENA in _fuentes_de(cliente, programa)
            _comprobar("al final no queda la escena Guyrapu al aire",
                       not al_aire, fallos)
    finally:
        _limpiar(capa)


def principal():
    _app = wx.App(False)
    marco = wx.Frame(None, title="Capa de vídeo de prueba")
    marco.Hide()
    estaba_abierto = obs_activacion.obs_esta_en_ejecucion()
    cliente = obs_cliente.ClienteObs(obs_cliente.leer_ajustes())
    fallos = []
    try:
        obs_lanzador.asegurar_obs(cliente.conectar)
        if not estaba_abierto:
            time.sleep(ESPERA_TRAS_ABRIR)
        if not cliente.conectado:
            cliente.conectar()
        _probar(marco, cliente, fallos)
    except Exception as error:
        print(f"Falla: {error}")
        fallos.append(str(error))
    finally:
        try:
            cliente.cerrar()
        except Exception as error:
            print(f"Aviso: no se pudo cerrar la conexión con OBS: {error}")
        try:
            marco.Destroy()
        except Exception as error:
            print(f"Aviso: no se pudo cerrar el marco de prueba: {error}")
        if not estaba_abierto:
            obs_lanzador.cerrar_obs()
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(principal())
