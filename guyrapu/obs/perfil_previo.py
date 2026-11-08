"""Vuelta al perfil de OBS que estaba activo antes de preparar un directo.

La app guarda en memoria un solo nombre pendiente, con un cerrojo, y solo
lo devuelve cuando OBS ya no tiene ninguna salida ni el búfer de clips en
marcha. Habla con OBS a través de un cliente con `pedir`, como
`obs_destinos`, y no importa wx ni conoce los anuncios.
"""

from __future__ import annotations

import threading

from guyrapu.core import diagnostico
from guyrapu.obs import obs_cliente

logger = diagnostico.obtener_logger(__name__)

_PENDIENTE = ""
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


def _hay_pendiente():
    with _CERROJO:
        return bool(_PENDIENTE)


def _olvidar(pendiente):
    global _PENDIENTE
    with _CERROJO:
        if _PENDIENTE == pendiente:
            _PENDIENTE = ""


def volver(cliente):
    """Vuelve al perfil pendiente si OBS no tiene salidas y lo devuelve.

    Devuelve "" si no hay nada pendiente, si alguna salida sigue activa o
    si OBS no responde. Un perfil que ya no existe se olvida.
    """
    with _CERROJO:
        pendiente = _PENDIENTE
    if not pendiente:
        return ""
    try:
        if (_activo(cliente, "GetStreamStatus")
                or _activo(cliente, "GetRecordStatus")
                or _buffer_activo(cliente)):
            return ""
        datos = _datos(cliente.pedir("GetProfileList"))
        perfiles = [str(nombre) for nombre in (datos.get("profiles") or [])]
        if pendiente not in perfiles:
            logger.debug("el perfil %s ya no existe en OBS: no se vuelve",
                         pendiente)
            _olvidar(pendiente)
            return ""
        cliente.pedir("SetCurrentProfile", {"profileName": pendiente})
    except obs_cliente.ObsError as error:
        logger.debug("no se pudo volver al perfil %s de OBS: %s",
                     pendiente, error)
        return ""
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
