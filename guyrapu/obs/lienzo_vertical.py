# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Conversación con el lienzo vertical del plugin Aitum Vertical Canvas.

El plugin se habla por `CallVendorRequest` con el vendor fijo
`aitum-vertical-canvas`. Las respuestas traen los datos del plugin en
`responseData.responseData`; un `success` falso se convierte en
`obs_cliente.ObsError` con un mensaje para el usuario.
"""

from __future__ import annotations

from guyrapu.core.idioma import N_, _
from guyrapu.obs import obs_cliente


VENDOR = "aitum-vertical-canvas"

MENSAJE_FALLO = N_("OBS no pudo completar la operación. Vuelve a intentarlo.")


def _datos(respuesta):
    return (respuesta or {}).get("responseData", respuesta or {}) or {}


def _pedir_vendor(cliente, tipo, datos=None, parada=None):
    respuesta = cliente.pedir("CallVendorRequest", {
        "vendorName": VENDOR,
        "requestType": tipo,
        "requestData": datos or {},
    }, parada)
    resultado = _datos(respuesta).get("responseData") or {}
    if resultado.get("success") is False:
        raise obs_cliente.ObsError(_(MENSAJE_FALLO))
    return resultado


def detectar(cliente, parada=None):
    """El lienzo vertical del plugin, o None si el plugin no está cargado."""
    try:
        _pedir_vendor(cliente, "version", {}, parada)
        datos = _datos(cliente.pedir("GetCanvasList", {}, parada))
    except obs_cliente.ObsError:
        return None
    for canvas in datos.get("canvases") or ():
        if (canvas.get("canvasFlags") or {}).get("MAIN"):
            continue
        video = canvas.get("canvasVideoSettings") or {}
        return {
            "canvasUuid": canvas.get("canvasUuid", ""),
            "canvasName": canvas.get("canvasName", ""),
            "ancho": video.get("baseWidth", 0),
            "alto": video.get("baseHeight", 0),
        }
    return None


def estado(cliente, parada=None) -> dict:
    """Dice si el lienzo vertical transmite, graba y tiene búfer."""
    datos = _pedir_vendor(cliente, "status", {}, parada)
    return {
        "transmitiendo": bool(datos.get("streaming")),
        "grabando": bool(datos.get("recording")),
        "bufer": bool(datos.get("backtrack")),
    }


def arrancar(cliente, parada=None):
    """Inicia la transmisión del lienzo vertical."""
    return _pedir_vendor(cliente, "start_streaming", {}, parada)


def detener(cliente, parada=None):
    """Detiene la transmisión del lienzo vertical."""
    return _pedir_vendor(cliente, "stop_streaming", {}, parada)


def arrancar_grabacion(cliente, parada=None):
    """Inicia la grabación del lienzo vertical."""
    return _pedir_vendor(cliente, "start_recording", {}, parada)


def detener_grabacion(cliente, parada=None):
    """Detiene la grabación del lienzo vertical."""
    return _pedir_vendor(cliente, "stop_recording", {}, parada)


def apagar_bufer(cliente, parada=None):
    """Apaga el búfer de clips del lienzo vertical."""
    return _pedir_vendor(cliente, "stop_backtrack", {}, parada)


def cambiar_servidor(cliente, indice, servidor, parada=None):
    """Cambia el servidor de la salida que está en esa posición."""
    return _pedir_vendor(cliente, "update_stream_server", {
        "stream_server": servidor, "index": indice}, parada)


def cambiar_clave(cliente, indice, clave, parada=None):
    """Cambia la clave de la salida que está en esa posición."""
    return _pedir_vendor(cliente, "update_stream_key", {
        "stream_key": clave, "index": indice}, parada)


def escena_actual(cliente, parada=None) -> str:
    """El nombre de la escena que el lienzo vertical tiene al aire."""
    return (_pedir_vendor(cliente, "current_scene", {}, parada).get(
        "scene", "") or "")


def cambiar_escena(cliente, escena, parada=None):
    """Pone al aire la escena indicada en el lienzo vertical."""
    return _pedir_vendor(cliente, "switch_scene", {"scene": escena}, parada)
