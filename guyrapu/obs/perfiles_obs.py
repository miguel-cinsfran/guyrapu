# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Crear, duplicar, eliminar y editar perfiles de OBS por el WebSocket.

Recibe un cliente con `pedir(tipo, datos=None, parada=None)` como
`obs_destinos` y no crea conexiones. Los ajustes del perfil viven en
`ajustes_perfil`; los codificadores de la PC, en `codificadores_obs`.
"""

from __future__ import annotations

import time
import uuid

from guyrapu.core import diagnostico
from guyrapu.core.idioma import N_, _
from guyrapu.obs import ajustes_perfil, codificadores_obs, obs_cliente

logger = diagnostico.obtener_logger(__name__)

_ESPERA_CAMBIO = 60.0
_INTERVALO_CAMBIO = 0.05

# Traductores: {perfil} es el nombre de un perfil de OBS.
MENSAJE_SIN_PERFIL = N_("OBS no tiene un perfil llamado {perfil}.")
MENSAJE_SALIDA_ACTIVA = N_(
    "No se puede cambiar el perfil de OBS con una salida en marcha. Detén "
    "la transmisión, la grabación y el búfer de clips y vuelve a intentarlo.")
MENSAJE_EN_USO = N_(
    "No se puede eliminar el perfil de OBS que está en uso.")
MENSAJE_UNICO = N_("No se puede eliminar el único perfil de OBS.")
MENSAJE_EXISTE = N_("Ya existe un perfil de OBS con ese nombre.")
MENSAJE_CAMBIO = N_("OBS no terminó de cambiar de perfil.")


def _datos(respuesta):
    return (respuesta or {}).get("responseData", respuesta or {})


def _activo(cliente, tipo, parada):
    return bool(_datos(cliente.pedir(tipo, parada=parada)).get("outputActive"))


def _buffer_activo(cliente, parada):
    """El búfer apagado hace fallar la consulta; eso significa apagado."""
    try:
        return _activo(cliente, "GetReplayBufferStatus", parada)
    except obs_cliente.ObsError as error:
        logger.debug("OBS no informó el búfer, se toma como apagado: %s",
                     error)
        return False


def _comprobar_salidas(cliente, parada):
    """Con una salida en marcha no se toca ningún perfil."""
    for tipo in ("GetStreamStatus", "GetRecordStatus"):
        if _activo(cliente, tipo, parada):
            raise obs_cliente.ObsError(_(MENSAJE_SALIDA_ACTIVA))
    if _buffer_activo(cliente, parada):
        raise obs_cliente.ObsError(_(MENSAJE_SALIDA_ACTIVA))


def _lista(cliente, parada):
    datos = _datos(cliente.pedir("GetProfileList", parada=parada))
    perfiles = [str(nombre) for nombre in (datos.get("profiles") or ())]
    return perfiles, str(datos.get("currentProfileName") or "")


def _parametro(cliente, categoria, nombre, parada):
    respuesta = cliente.pedir(
        "GetProfileParameter",
        {"parameterCategory": categoria, "parameterName": nombre},
        parada)
    datos = _datos(respuesta)
    valor = datos.get("parameterValue")
    if valor is None or valor == "":
        valor = datos.get("defaultParameterValue")
    return "" if valor is None else str(valor)


def _fijar_parametro(cliente, categoria, nombre, valor, parada):
    cliente.pedir("SetProfileParameter", {
        "parameterCategory": categoria,
        "parameterName": nombre,
        "parameterValue": valor,
    }, parada)


def _esperar(cliente, cumple, parada):
    inicio = time.monotonic()
    while True:
        if parada is not None and parada.is_set():
            raise obs_cliente.ObsError(_("Operación cancelada."))
        perfiles, actual = _lista(cliente, parada)
        if cumple(perfiles, actual):
            return
        if time.monotonic() - inicio >= _ESPERA_CAMBIO:
            raise obs_cliente.ObsError(_(MENSAJE_CAMBIO))
        time.sleep(_INTERVALO_CAMBIO)


def _cambiar(cliente, nombre, parada):
    perfiles, actual = _lista(cliente, parada)
    if actual == nombre:
        return
    if nombre not in perfiles:
        raise obs_cliente.ObsError(
            _(MENSAJE_SIN_PERFIL).format(perfil=nombre))
    cliente.pedir("SetCurrentProfile", {"profileName": nombre}, parada)
    _esperar(cliente, lambda perfiles, actual: actual == nombre, parada)


def _crear(cliente, nombre, parada):
    cliente.pedir("CreateProfile", {"profileName": nombre}, parada)
    _esperar(cliente,
             lambda perfiles, actual: (nombre in perfiles
                                       or actual == nombre), parada)
    _cambiar(cliente, nombre, parada)


def _intentar_volver(cliente, original, parada):
    if not original:
        return
    try:
        _cambiar(cliente, original, parada)
    except obs_cliente.ObsError as error:
        logger.debug("no se pudo volver al perfil de OBS %s: %s",
                     original, error)


def _borrar_si_existe(cliente, nombre, parada):
    """Borra el perfil nuevo que quedó a medias, sin tapar el error original."""
    try:
        perfiles, _actual = _lista(cliente, parada)
        if nombre in perfiles:
            cliente.pedir("RemoveProfile", {"profileName": nombre}, parada)
    except obs_cliente.ObsError as error:
        logger.debug("no se pudo borrar el perfil de OBS %s: %s",
                     nombre, error)


def _recargar(cliente, actual, perfiles, parada):
    """Pasa a otro perfil y vuelve para que OBS lea codificador y bitrates."""
    otro = next((nombre for nombre in perfiles if nombre != actual), "")
    if otro:
        _cambiar(cliente, otro, parada)
        _cambiar(cliente, actual, parada)
        return
    temporal = "Guyrapu " + uuid.uuid4().hex[:8]
    _crear(cliente, temporal, parada)
    try:
        _cambiar(cliente, actual, parada)
    finally:
        try:
            cliente.pedir("RemoveProfile", {"profileName": temporal}, parada)
        except obs_cliente.ObsError as error:
            logger.debug("no se pudo borrar el perfil temporal %s: %s",
                         temporal, error)


def _leer_actual(cliente, parada):
    video = _datos(cliente.pedir("GetVideoSettings", parada=parada))
    servicio = _datos(cliente.pedir("GetStreamServiceSettings", parada=parada))
    carpeta = _datos(cliente.pedir("GetRecordDirectory", parada=parada)).get(
        "recordDirectory", "")
    codificador = _parametro(cliente, "SimpleOutput", "StreamEncoder", parada)
    parametros = {}
    for categoria, nombre in ajustes_perfil.claves_de_lectura(codificador):
        parametros[(categoria, nombre)] = _parametro(
            cliente, categoria, nombre, parada)
    return ajustes_perfil.desde_obs(video, servicio, carpeta, parametros)


def _escribir_video(cliente, ajustes, parada):
    cliente.pedir("SetVideoSettings", ajustes_perfil.datos_video(ajustes),
                  parada)


def _escribir_servicio(cliente, ajustes, parada):
    if not ajustes.servidor or not ajustes.clave:
        return
    actual = _datos(cliente.pedir("GetStreamServiceSettings", parada=parada))
    cliente.pedir("SetStreamServiceSettings",
                  ajustes_perfil.datos_servicio(actual, ajustes), parada)


def _escribir_actual(cliente, ajustes, parada, escribir_servicio=True):
    ajustes_perfil.validar(ajustes)
    _escribir_video(cliente, ajustes, parada)
    if escribir_servicio:
        _escribir_servicio(cliente, ajustes, parada)
    for categoria, nombre, valor in ajustes_perfil.parametros_obs(ajustes):
        _fijar_parametro(cliente, categoria, nombre, valor, parada)
    if ajustes.carpeta_grabacion:
        cliente.pedir("SetRecordDirectory", {
            "recordDirectory": ajustes.carpeta_grabacion}, parada)


def _leer_de(cliente, objetivo, actual, parada):
    if actual != objetivo:
        _cambiar(cliente, objetivo, parada)
    try:
        ajustes = _leer_actual(cliente, parada)
    except Exception:
        if actual != objetivo:
            _intentar_volver(cliente, actual, parada)
        raise
    if actual != objetivo:
        _cambiar(cliente, actual, parada)
    return ajustes


def leer_ajustes(cliente, perfil=None, parada=None):
    """Lee los ajustes de un perfil y deja OBS en el que estaba."""
    _comprobar_salidas(cliente, parada)
    perfiles, actual = _lista(cliente, parada)
    objetivo = perfil or actual
    if objetivo not in perfiles:
        raise obs_cliente.ObsError(
            _(MENSAJE_SIN_PERFIL).format(perfil=objetivo))
    return _leer_de(cliente, objetivo, actual, parada)


def guardar_ajustes(cliente, ajustes, perfil=None, parada=None):
    """Guarda los ajustes en un perfil y deja OBS en el que estaba."""
    _comprobar_salidas(cliente, parada)
    perfiles, actual = _lista(cliente, parada)
    objetivo = perfil or actual
    if objetivo not in perfiles:
        raise obs_cliente.ObsError(
            _(MENSAJE_SIN_PERFIL).format(perfil=objetivo))
    if actual != objetivo:
        _cambiar(cliente, objetivo, parada)
    try:
        _escribir_actual(cliente, ajustes, parada)
        if objetivo == actual:
            _recargar(cliente, objetivo, perfiles, parada)
    except Exception:
        _intentar_volver(cliente, actual, parada)
        raise
    if objetivo != actual:
        _cambiar(cliente, actual, parada)


def crear_perfil(cliente, nombre, vertical=False, codificadores=None,
                 parada=None):
    """Crea un perfil horizontal o vertical y lo deja como actual."""
    _comprobar_salidas(cliente, parada)
    perfiles, actual = _lista(cliente, parada)
    if nombre in perfiles:
        raise obs_cliente.ObsError(_(MENSAJE_EXISTE))
    disponibles = (tuple(codificadores) if codificadores is not None
                   else codificadores_obs.codificadores_disponibles())
    ajustes = ajustes_perfil.valores_iniciales(
        vertical, ajustes_perfil.mejor_codificador(disponibles))
    try:
        _crear(cliente, nombre, parada)
        _escribir_actual(cliente, ajustes, parada, escribir_servicio=False)
        perfiles, _actual = _lista(cliente, parada)
        _recargar(cliente, nombre, perfiles, parada)
    except Exception:
        _intentar_volver(cliente, actual, parada)
        _borrar_si_existe(cliente, nombre, parada)
        raise
    return ajustes


def duplicar_perfil(cliente, origen, nuevo, parada=None):
    """Duplica un perfil con otro nombre y deja OBS en el que estaba."""
    _comprobar_salidas(cliente, parada)
    perfiles, actual = _lista(cliente, parada)
    if origen not in perfiles:
        raise obs_cliente.ObsError(
            _(MENSAJE_SIN_PERFIL).format(perfil=origen))
    if nuevo in perfiles:
        raise obs_cliente.ObsError(_(MENSAJE_EXISTE))
    try:
        ajustes = _leer_de(cliente, origen, actual, parada)
        _crear(cliente, nuevo, parada)
        _escribir_actual(cliente, ajustes, parada)
        _cambiar(cliente, actual, parada)
    except Exception:
        _intentar_volver(cliente, actual, parada)
        _borrar_si_existe(cliente, nuevo, parada)
        raise
    return ajustes


def eliminar_perfil(cliente, nombre, parada=None):
    """Elimina un perfil que no sea el actual ni el único."""
    _comprobar_salidas(cliente, parada)
    perfiles, actual = _lista(cliente, parada)
    if nombre not in perfiles:
        raise obs_cliente.ObsError(
            _(MENSAJE_SIN_PERFIL).format(perfil=nombre))
    if len(perfiles) <= 1:
        raise obs_cliente.ObsError(_(MENSAJE_UNICO))
    if nombre == actual:
        raise obs_cliente.ObsError(_(MENSAJE_EN_USO))
    cliente.pedir("RemoveProfile", {"profileName": nombre}, parada)


def cambiar_perfil(cliente, nombre, parada=None):
    """Deja activo el perfil elegido."""
    _comprobar_salidas(cliente, parada)
    _cambiar(cliente, nombre, parada)


def _modo(cliente, parada):
    return _parametro(cliente, "Output", "Mode", parada).strip().lower()


def esta_en_avanzado(cliente, perfil=None, parada=None):
    """Dice si el perfil está en modo Avanzado y deja OBS como estaba."""
    _comprobar_salidas(cliente, parada)
    perfiles, actual = _lista(cliente, parada)
    objetivo = perfil or actual
    if objetivo not in perfiles:
        raise obs_cliente.ObsError(
            _(MENSAJE_SIN_PERFIL).format(perfil=objetivo))
    if actual != objetivo:
        _cambiar(cliente, objetivo, parada)
    try:
        modo = _modo(cliente, parada)
    except Exception:
        if actual != objetivo:
            _intentar_volver(cliente, actual, parada)
        raise
    if actual != objetivo:
        _cambiar(cliente, actual, parada)
    return modo == "advanced"


def _convertir(cliente, objetivo, actual, perfiles, parada):
    if _modo(cliente, parada) != "advanced":
        return False
    codificador = codificadores_obs.codificador_simple(
        _parametro(cliente, "AdvOut", "Encoder", parada))
    bitrate = codificadores_obs.bitrate_avanzado(objetivo)
    _fijar_parametro(cliente, "SimpleOutput", "StreamEncoder", codificador,
                     parada)
    _fijar_parametro(cliente, "SimpleOutput", "VBitrate", str(bitrate), parada)
    _fijar_parametro(cliente, "Output", "Mode", "Simple", parada)
    if objetivo == actual:
        _recargar(cliente, objetivo, perfiles, parada)
    return True


def pasar_a_sencillo(cliente, perfil=None, parada=None):
    """Pasa el perfil a modo Sencillo copiando codificador y bitrate."""
    _comprobar_salidas(cliente, parada)
    perfiles, actual = _lista(cliente, parada)
    objetivo = perfil or actual
    if objetivo not in perfiles:
        raise obs_cliente.ObsError(
            _(MENSAJE_SIN_PERFIL).format(perfil=objetivo))
    if actual != objetivo:
        _cambiar(cliente, objetivo, parada)
    try:
        convertido = _convertir(cliente, objetivo, actual, perfiles, parada)
    except Exception:
        _intentar_volver(cliente, actual, parada)
        raise
    if actual != objetivo:
        _cambiar(cliente, actual, parada)
    return convertido
