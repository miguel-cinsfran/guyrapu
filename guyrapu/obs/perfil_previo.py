# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Vuelta al perfil y a la escena de OBS que había antes de un directo.

La app guarda en memoria un solo perfil pendiente y una sola escena
pendiente, con un cerrojo, y solo los devuelve cuando OBS ya no tiene
ninguna salida ni el búfer de clips en marcha. Habla con OBS a través de
un cliente con `pedir`, como `obs_destinos`, y no importa wx ni conoce los
anuncios.
"""

from __future__ import annotations

import threading

from guyrapu.core import diagnostico
from guyrapu.obs import audio_de_perfil, obs_cliente

logger = diagnostico.obtener_logger(__name__)

_PENDIENTE = ""
_ESCENA_PENDIENTE = ()
_CERROJO = threading.Lock()


def _datos(respuesta):
    return (respuesta or {}).get("responseData", respuesta or {})


def _activo(cliente, tipo):
    return bool(_datos(cliente.pedir(tipo)).get("outputActive"))


def _buffer_activo(cliente):
    """El búfer apagado hace fallar la consulta; eso significa apagado."""
    try:
        return _activo(cliente, "GetReplayBufferStatus")
    except obs_cliente.ObsError as error:
        logger.debug("OBS no informó el búfer, se toma como apagado: %s",
                     error)
        return False


def recordar(actual, nuevo):
    """Guarda el perfil que había antes, si el directo lo va a cambiar."""
    global _PENDIENTE
    with _CERROJO:
        if not actual or actual == nuevo or _PENDIENTE:
            return
        _PENDIENTE = actual


def recordar_escena(anterior, puesta):
    """Guarda la escena que había antes de poner al aire la de la app."""
    global _ESCENA_PENDIENTE
    if not anterior or not puesta or anterior == puesta:
        return
    with _CERROJO:
        if _ESCENA_PENDIENTE:
            return
        _ESCENA_PENDIENTE = (anterior, puesta)


def _hay_pendiente():
    with _CERROJO:
        return bool(_PENDIENTE or _ESCENA_PENDIENTE)


def _olvidar(pendiente):
    global _PENDIENTE
    with _CERROJO:
        if _PENDIENTE == pendiente:
            _PENDIENTE = ""


def _olvidar_escena(pendiente):
    global _ESCENA_PENDIENTE
    with _CERROJO:
        if _ESCENA_PENDIENTE == pendiente:
            _ESCENA_PENDIENTE = ()


def _volver_escena(cliente, pendiente):
    """Devuelve la escena de antes, si nadie la cambió y todavía existe."""
    anterior, puesta = pendiente
    al_aire = _datos(cliente.pedir("GetCurrentProgramScene")).get(
        "currentProgramSceneName", "") or ""
    if al_aire != puesta:
        _olvidar_escena(pendiente)
        return
    datos = _datos(cliente.pedir("GetSceneList"))
    escenas = {str(escena.get("sceneName", ""))
               for escena in (datos.get("scenes") or ())}
    if anterior not in escenas:
        logger.debug("la escena %s ya no existe en OBS: no se vuelve",
                     anterior)
        _olvidar_escena(pendiente)
        return
    cliente.pedir("SetCurrentProgramScene", {"sceneName": anterior})
    _olvidar_escena(pendiente)


def _volver_perfil(cliente, pendiente):
    """Vuelve al perfil pendiente; "" si ya no existe."""
    datos = _datos(cliente.pedir("GetProfileList"))
    perfiles = [str(nombre) for nombre in (datos.get("profiles") or [])]
    if pendiente not in perfiles:
        logger.debug("el perfil %s ya no existe en OBS: no se vuelve",
                     pendiente)
        _olvidar(pendiente)
        return ""
    audio_de_perfil.igualar(cliente, pendiente)
    cliente.pedir("SetCurrentProfile", {"profileName": pendiente})
    return pendiente


def volver(cliente):
    """Vuelve al perfil y a la escena pendientes, si no hay salidas.

    Devuelve el perfil al que volvió, o "" si no había perfil pendiente,
    si alguna salida sigue activa o si OBS no responde. Un perfil o una
    escena que ya no existen se olvidan.
    """
    with _CERROJO:
        pendiente = _PENDIENTE
        escena = _ESCENA_PENDIENTE
    if not pendiente and not escena:
        return ""
    try:
        if (_activo(cliente, "GetStreamStatus")
                or _activo(cliente, "GetRecordStatus")
                or _buffer_activo(cliente)):
            return ""
        if pendiente:
            pendiente = _volver_perfil(cliente, pendiente)
        if escena:
            _volver_escena(cliente, escena)
    except obs_cliente.ObsError as error:
        logger.debug("no se pudo volver al perfil %s de OBS: %s",
                     pendiente, error)
        return ""
    if pendiente:
        _olvidar(pendiente)
    return pendiente


def _volver_en_hilo():
    gestor = None
    try:
        # Import local: obs_panel importa obs_destinos, que importa este módulo.
        from guyrapu.obs.obs_panel import GestorPanelObs
        gestor = GestorPanelObs()
        gestor.conectar()
        volver(gestor._cliente)
    except Exception as error:
        logger.debug("no se pudo conectar con OBS para volver al perfil: %s",
                     error)
    finally:
        if gestor is not None:
            try:
                gestor.cerrar()
            except Exception as error:
                logger.debug("no se pudo cerrar el gestor de OBS: %s", error)


def volver_sin_directo():
    """Lanza la vuelta al perfil pendiente, si todavía hay uno."""
    if _hay_pendiente():
        diagnostico.crear_hilo(_volver_en_hilo, "VolverPerfilObs").start()


def tras_supervision(original):
    """Envuelve el aviso de fin para volver al perfil cuando OBS se apague."""
    def al_terminar():
        try:
            if original is not None:
                original()
        finally:
            volver_sin_directo()
    return al_terminar
