# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""La prueba de conexión contra YouTube: cómo se transmite y se mide la red.

Crea un directo privado y un flujo propios de la prueba, transmite unos
segundos con cada bitrate y mide los cuadros que se pierden por la red. Nunca
sale al aire y siempre deja OBS y YouTube como estaban, también cuando falla o
se cancela.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, replace
from datetime import datetime, timezone

from guyrapu.core import diagnostico
from guyrapu.core.idioma import N_, _
from guyrapu.obs import escalones_red, obs_cliente, perfiles_obs
from guyrapu.youtube import emision, flujo_prueba

logger = diagnostico.obtener_logger(__name__)

TITULO_DIRECTO = N_("Prueba de conexión de Guyrapu")
CALENTAMIENTO = 5.0
MEDICION = 15.0
_ESPERA_DETENCION = 10.0
_PASO_DETENCION = 0.2

MENSAJE_SIN_SESION = N_(
    "No se puede probar la conexión sin una sesión de YouTube. Inicia sesión "
    "en Preferencias, categoría YouTube.")
MENSAJE_AVANZADO = N_(
    "No se puede probar la conexión con un perfil de OBS en modo Avanzado. "
    "Pásalo a modo Sencillo y vuelve a intentarlo.")
MENSAJE_SIN_FLUJO = N_(
    "YouTube no devolvió el flujo de transmisión de la prueba.")
MENSAJE_ERROR_RESTABLECER = N_(
    "La prueba dio un error: {error} Además quedó pendiente: {errores}.")


@dataclass(frozen=True)
class Preparacion:
    """Lo que hace falta para mostrar el cuadro previo y arrancar la prueba."""

    perfil: str
    bitrate: int
    segundos_maximos: int


@dataclass(frozen=True)
class PasoRed:
    """Lo medido con un bitrate, con la diferencia de los contadores."""

    bitrate: int
    perdidos: int
    totales: int

    @property
    def porcentaje(self) -> int:
        if self.totales <= 0:
            return 0
        return int(round(100 * max(0, self.perdidos) / self.totales))

    @property
    def aguanta(self) -> bool:
        return escalones_red.aguanta(self.perdidos, self.totales)


@dataclass(frozen=True)
class ResultadoConexion:
    """Los intentos medidos y hasta dónde llegó la conexión."""

    perfil: str
    original: object
    bitrate_perfil: int
    aguantaron: int | None
    mayor: int | None
    pasos: tuple
    cancelada: bool = False
    errores: tuple = ()

    @property
    def aguanta_tal_cual(self) -> bool:
        return (self.aguantaron is not None
                and self.aguantaron == self.bitrate_perfil)

    @property
    def puede_guardar(self) -> bool:
        return (self.aguantaron is not None
                and self.aguantaron < self.bitrate_perfil)

    @property
    def ultimo(self):
        return self.pasos[-1] if self.pasos else None


class ErrorPruebaConexion(obs_cliente.ObsError):
    """La prueba dio un error y el restablecimiento no quedó completo."""

    def __init__(self, mensaje, errores=()):
        super().__init__(mensaje)
        self.errores = tuple(errores)


def _datos(cliente, tipo, datos=None, parada=None):
    respuesta = cliente.pedir(tipo, datos, parada) or {}
    return respuesta.get("responseData", respuesta or {})


def _entero(valor):
    try:
        return max(0, int(valor or 0))
    except (TypeError, ValueError):
        return 0


def _diferencia(despues, antes, clave):
    return max(0, despues.get(clave, 0) - antes.get(clave, 0))


def _stats(cliente, parada):
    datos = _datos(cliente, "GetStreamStatus", parada=parada)
    return {clave: _entero(datos.get(clave)) for clave in (
        "outputSkippedFrames", "outputTotalFrames")}


def _esperar(parada, segundos, dormir):
    if parada is None:
        dormir(segundos)
        return False
    return parada.wait(segundos)


def _esperar_detencion(cliente, dormir=time.sleep):
    limite = time.monotonic() + _ESPERA_DETENCION
    while time.monotonic() < limite:
        try:
            if not _datos(cliente, "GetStreamStatus").get("outputActive"):
                return True
        except obs_cliente.ObsError as error:
            logger.debug("OBS no informó el fin de la transmisión: %s", error)
            return False
        dormir(_PASO_DETENCION)
    return False


def _detener(cliente):
    if not _datos(cliente, "GetStreamStatus").get("outputActive"):
        return
    _datos(cliente, "StopStream")
    _esperar_detencion(cliente)


def _poner_servicio(cliente, servicio, parada=None):
    if not servicio:
        return
    cliente.pedir("SetStreamServiceSettings", {
        "streamServiceType": servicio.get("streamServiceType") or "rtmp_custom",
        "streamServiceSettings": dict(
            servicio.get("streamServiceSettings") or {}),
    }, parada)


def intentos_maximos(bitrate) -> int:
    """Cuántos intentos puede llegar a hacer la prueba como mucho."""
    return 1 + max(len(escalones_red.hacia_abajo(bitrate)),
                   len(escalones_red.hacia_arriba(bitrate)))


def segundos_maximos(bitrate, calentamiento=CALENTAMIENTO,
                     medicion=MEDICION) -> int:
    """Cuánto puede durar la prueba si hace todos los intentos."""
    return int(round(intentos_maximos(bitrate) * (calentamiento + medicion)))


def preparar(cliente_obs, hay_sesion=True, parada=None,
             calentamiento=CALENTAMIENTO, medicion=MEDICION) -> Preparacion:
    """Comprueba que se pueda probar y arma los datos del cuadro previo."""
    if not hay_sesion:
        raise ErrorPruebaConexion(_(MENSAJE_SIN_SESION))
    ajustes = perfiles_obs.leer_ajustes(cliente_obs, parada=parada)
    if perfiles_obs.esta_en_avanzado(cliente_obs, parada=parada):
        raise ErrorPruebaConexion(_(MENSAJE_AVANZADO))
    _perfiles, perfil = perfiles_obs.listar_perfiles(cliente_obs, parada)
    bitrate = int(ajustes.bitrate_video)
    return Preparacion(perfil, bitrate,
                       segundos_maximos(bitrate, calentamiento, medicion))


def _inicio_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _crear_directo(cliente_yt, servicio_yt, estado):
    cuerpo = emision.cuerpo_emision(
        _(TITULO_DIRECTO), "", "private", _inicio_iso())
    cuerpo["contentDetails"]["enableAutoStart"] = False
    cuerpo["contentDetails"]["enableAutoStop"] = False
    estado["id_video"] = cliente_yt.crear_emision(cuerpo)
    id_flujo, servidor, clave = flujo_prueba.crear(
        servicio_yt, _(TITULO_DIRECTO))
    estado["id_flujo"] = id_flujo
    if not id_flujo or not servidor or not clave:
        raise ErrorPruebaConexion(_(MENSAJE_SIN_FLUJO))
    cliente_yt.vincular_emision(estado["id_video"], id_flujo)
    return servidor, clave


def _probar(cliente, perfil, base, bitrate, parada, calentamiento, medicion,
            dormir, al_bitrate):
    """Un intento: guarda el bitrate, transmite y mide; None si se paró."""
    if parada is not None and parada.is_set():
        return None
    ajustes = replace(base, bitrate_video=bitrate)
    perfiles_obs.guardar_ajustes(cliente, ajustes, perfil, parada)
    if al_bitrate is not None:
        al_bitrate(bitrate)
    paso = None
    _datos(cliente, "StartStream", parada=parada)
    try:
        if not _esperar(parada, calentamiento, dormir):
            antes = _stats(cliente, parada)
            if not _esperar(parada, medicion, dormir):
                despues = _stats(cliente, parada)
                paso = PasoRed(
                    bitrate,
                    _diferencia(despues, antes, "outputSkippedFrames"),
                    _diferencia(despues, antes, "outputTotalFrames"))
    finally:
        _detener(cliente)
    return paso


def _recorrido(cliente, perfil, base, bitrate, parada, calentamiento,
               medicion, dormir, al_bitrate, estado):
    """Primer intento y, según aguante, la escalera que corresponda."""

    def intentar(valor):
        paso = _probar(cliente, perfil, base, valor, parada, calentamiento,
                       medicion, dormir, al_bitrate)
        if paso is None:
            estado["cancelada"] = True
        else:
            estado["pasos"].append(paso)
        return paso

    paso = intentar(bitrate)
    if paso is None:
        return
    if paso.aguanta:
        estado["aguantaron"] = estado["mayor"] = bitrate
        for subida in escalones_red.hacia_arriba(bitrate):
            if estado["cancelada"]:
                return
            paso = intentar(subida)
            if paso is None or not paso.aguanta:
                return
            estado["mayor"] = subida
        return
    for bajada in escalones_red.hacia_abajo(bitrate):
        if estado["cancelada"]:
            return
        paso = intentar(bajada)
        if paso is None:
            return
        if paso.aguanta:
            estado["aguantaron"] = bajada
            return


def _restaurar(cliente, cliente_yt, servicio_yt, original, perfil, servicio,
               estado):
    """Deja OBS y YouTube como estaban sin mirar la parada."""
    errores = []

    def intentar(descripcion, accion):
        try:
            accion()
        except Exception as error:
            errores.append("{}: {}".format(descripcion, error))

    intentar(_("Detener la transmisión de la prueba"), lambda: _detener(cliente))
    intentar(_("Restablecer los ajustes del perfil"), lambda: (
        perfiles_obs.guardar_ajustes(cliente, original, perfil, None)))
    intentar(_("Restablecer el servidor y la clave"),
             lambda: _poner_servicio(cliente, servicio))

    def borrar_directo():
        try:
            cliente_yt.borrar_emision(estado["id_video"])
        except Exception as error:
            errores.append(_(
                "El directo privado «{titulo}» quedó en YouTube: {error}").format(
                    titulo=estado.get("titulo", ""), error=error))

    def borrar_flujo():
        try:
            flujo_prueba.borrar(servicio_yt, estado["id_flujo"])
        except Exception as error:
            errores.append(_(
                "El flujo de transmisión de la prueba quedó en YouTube: "
                "{error}").format(error=error))

    if estado.get("id_video"):
        intentar(_("Borrar el directo de la prueba"), borrar_directo)
    if estado.get("id_flujo"):
        intentar(_("Borrar el flujo de la prueba"), borrar_flujo)
    return errores


def ejecutar(cliente, cliente_yt, parada=None, al_bitrate=None,
             calentamiento=CALENTAMIENTO, medicion=MEDICION,
             dormir=time.sleep) -> ResultadoConexion:
    """Mide la red con cada bitrate y devuelve lo aguantado; siempre restaura."""
    original = perfiles_obs.leer_ajustes(cliente, parada=parada)
    if perfiles_obs.esta_en_avanzado(cliente, parada=parada):
        raise ErrorPruebaConexion(_(MENSAJE_AVANZADO))
    _perfiles, perfil = perfiles_obs.listar_perfiles(cliente, parada)
    servicio = _datos(cliente, "GetStreamServiceSettings", parada=parada)
    # El flujo de la prueba se crea y se borra con el servicio de escritura
    # del cliente: se obtiene una sola vez y se reutiliza en todo el recorrido.
    servicio_yt = cliente_yt._escritura()
    bitrate = int(original.bitrate_video)
    estado = {"pasos": [], "aguantaron": None, "mayor": None,
              "cancelada": False, "titulo": _(TITULO_DIRECTO)}
    error_original = None
    try:
        servidor, clave = _crear_directo(cliente_yt, servicio_yt, estado)
        _poner_servicio(cliente, {
            "streamServiceType": "rtmp_custom",
            "streamServiceSettings": {"server": servidor, "key": clave},
        }, parada)
        base = replace(original, servidor=servidor, clave=clave)
        _recorrido(cliente, perfil, base, bitrate, parada, calentamiento,
                   medicion, dormir, al_bitrate, estado)
    except Exception as error:
        error_original = error
    finally:
        errores = _restaurar(cliente, cliente_yt, servicio_yt, original, perfil,
                             servicio, estado)
    if error_original is not None:
        if errores:
            raise ErrorPruebaConexion(_(MENSAJE_ERROR_RESTABLECER).format(
                error=error_original,
                errores=", ".join(errores)), errores) from error_original
        raise error_original
    return ResultadoConexion(
        perfil, original, bitrate, estado["aguantaron"], estado["mayor"],
        tuple(estado["pasos"]), estado["cancelada"], tuple(errores))
