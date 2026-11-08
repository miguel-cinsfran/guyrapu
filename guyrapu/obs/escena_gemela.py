# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Relación entre una escena de OBS y su versión vertical.

OBS guarda una sola posición por fuente, así que la escena horizontal no
sirve para un lienzo vertical. La versión vertical es otra escena de la
misma colección con las mismas fuentes. Recibe un cliente con `pedir(tipo,
datos=None, parada=None)` como `obs_destinos` y no crea conexiones.
"""

from __future__ import annotations

from guyrapu.core import diagnostico
from guyrapu.obs import obs_cliente, perfiles_obs

logger = diagnostico.obtener_logger(__name__)

# Fijo, sin traducir: los nombres de escena son del usuario y la búsqueda
# tiene que encontrar la versión vertical con cualquier idioma de la interfaz.
SUFIJO = " vertical"


def nombre_gemela(escena) -> str:
    """El nombre de la versión vertical de una escena."""
    return f"{escena}{SUFIJO}"


def original_de(escena, escenas):
    """La escena original de una versión vertical, o None si no la hay."""
    if not escena.endswith(SUFIJO):
        return None
    original = escena[:-len(SUFIJO)]
    return original if original in (escenas or ()) else None


def _datos(respuesta):
    return (respuesta or {}).get("responseData", respuesta or {})


def _al_aire(cliente, parada):
    return _datos(cliente.pedir("GetCurrentProgramScene", parada=parada)).get(
        "currentProgramSceneName", "") or ""


def _escenas(cliente, parada):
    datos = _datos(cliente.pedir("GetSceneList", parada=parada))
    return {escena.get("sceneName", "")
            for escena in (datos.get("scenes") or ())}


def en_perfil(cliente, perfil, accion, parada=None):
    """Corre la acción con el perfil indicado y vuelve siempre al de antes.

    Comprueba primero que no haya una salida en marcha, como el resto de
    los cambios de perfil. Devuelve lo que devuelva la acción.
    """
    perfiles_obs.comprobar_salidas(cliente, parada)
    anterior = perfiles_obs.listar_perfiles(cliente, parada)[1]
    try:
        if perfil:
            perfiles_obs.cambiar(cliente, perfil, parada)
        return accion()
    finally:
        if anterior and anterior != perfil:
            try:
                perfiles_obs.cambiar(cliente, anterior, parada)
            except obs_cliente.ObsError as error:
                logger.debug("no se pudo volver al perfil de OBS %s: %s",
                             anterior, error)


def poner_segun_lienzo(cliente, parada=None):
    """Pone al aire la escena que corresponde al lienzo activo.

    Con el lienzo vertical pone la versión vertical de la escena al aire;
    con el horizontal, la original de una versión vertical. Devuelve la
    escena que quitó del aire, o None si no cambió nada.
    """
    lienzo = _datos(cliente.pedir("GetVideoSettings", parada=parada))
    ancho = lienzo.get("baseWidth") or 0
    alto = lienzo.get("baseHeight") or 0
    actual = _al_aire(cliente, parada)
    if not actual:
        return None
    try:
        escenas = _escenas(cliente, parada)
    except obs_cliente.ObsError as error:
        logger.debug("OBS no informó las escenas, no se cambia la del aire: %s",
                     error)
        return None
    if alto > ancho:
        gemela = nombre_gemela(actual)
        if gemela in escenas:
            cliente.pedir("SetCurrentProgramScene", {"sceneName": gemela},
                          parada)
            return actual
        return None
    if ancho > alto:
        original = original_de(actual, escenas)
        if original is not None:
            cliente.pedir("SetCurrentProgramScene", {"sceneName": original},
                          parada)
            return actual
    return None
