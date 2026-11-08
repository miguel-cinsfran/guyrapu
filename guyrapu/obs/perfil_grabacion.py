# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Con qué perfil de OBS se graba desde la app.

Si hay un perfil para grabar elegido, distinto del actual y sin ninguna
salida en marcha, se cambia antes de iniciar y se vuelve al anterior al
detener. Con el directo o los clips activos OBS no cambia de perfil: se
graba con el que tiene y se avisa.
"""

from __future__ import annotations

from guyrapu.core import diagnostico
from guyrapu.core.idioma import N_, _
from guyrapu.obs import obs_cliente, obs_destinos, obs_grabacion, perfil_previo

logger = diagnostico.obtener_logger(__name__)

# Traductores: {perfil} es el perfil de OBS que está activo.
AVISO_DIRECTO = N_(
    "Con el directo en marcha, se graba con el perfil {perfil}.")
# Traductores: {perfil} es el perfil de OBS que está activo.
AVISO_CLIPS = N_(
    "Con los clips en marcha, se graba con el perfil {perfil}.")
# Traductores: {elegido} es el perfil para grabar que ya no está en OBS y
# {perfil} el que está activo.
AVISO_SIN_PERFIL = N_(
    "OBS no tiene el perfil {elegido}: se graba con el perfil {perfil}.")


def _datos(respuesta):
    return (respuesta or {}).get("responseData", respuesta or {})


def _activo(cliente, tipo, parada=None):
    return bool(_datos(cliente.pedir(tipo, parada=parada)).get("outputActive"))


def _buffer_activo(cliente, parada=None):
    """El búfer apagado hace fallar la consulta; eso significa apagado."""
    try:
        return _activo(cliente, "GetReplayBufferStatus", parada)
    except obs_cliente.ObsError as error:
        logger.debug("OBS no informó el búfer, se toma como apagado: %s",
                     error)
        return False


def _preparar(cliente, perfil, parada):
    """Cambia al perfil para grabar si se puede; devuelve el aviso."""
    datos = _datos(cliente.pedir("GetProfileList", parada=parada))
    actual = str(datos.get("currentProfileName") or "")
    perfiles = [str(nombre) for nombre in (datos.get("profiles") or [])]
    if actual == perfil:
        return ""
    if _activo(cliente, "GetStreamStatus", parada):
        return _(AVISO_DIRECTO).format(perfil=actual)
    if _buffer_activo(cliente, parada):
        return _(AVISO_CLIPS).format(perfil=actual)
    if perfil not in perfiles:
        return _(AVISO_SIN_PERFIL).format(elegido=perfil, perfil=actual)
    perfil_previo.recordar(actual, perfil)
    obs_destinos.preparar_perfil(
        cliente, obs_destinos.Destino(perfil), perfil, parada)
    return ""


def alternar(cliente, perfil, parada=None):
    """Inicia o detiene la grabación y devuelve (activa, ruta, aviso)."""
    estado = _datos(cliente.pedir("GetRecordStatus", parada=parada))
    aviso = ""
    if not bool(estado.get("outputActive")) and perfil:
        aviso = _preparar(cliente, perfil, parada)
    activa, ruta = obs_grabacion.alternar_con_ruta(cliente.pedir, parada)
    if not activa:
        perfil_previo.volver(cliente)
    return activa, ruta, aviso
