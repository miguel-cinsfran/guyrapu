# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""La prueba del equipo contra OBS: cómo se graba y se mide.

Graba con el perfil en uso una página con movimiento encima de la escena
actual, mide los fotogramas perdidos al dibujar y al codificar, y prueba
escalones más livianos hasta encontrar uno que aguante. Siempre deja OBS
como estaba, también cuando falla o se cancela.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, replace
from pathlib import Path

from guyrapu.core import diagnostico
from guyrapu.core.idioma import N_, _
from guyrapu.obs import (codificadores_obs, escalones_equipo, escenas_obs,
                         movimiento_prueba, obs_cliente, perfiles_obs)

logger = diagnostico.obtener_logger(__name__)

NOMBRE_ESCENA = N_("Guyrapu prueba del equipo")
NOMBRE_FUENTE = N_("Guyrapu prueba del equipo (movimiento)")
TIPO_FUENTE = "browser_source"
CALENTAMIENTO = 2.0
MEDICION = 10.0
_ESPERA_DETENCION = 10.0
_PASO_DETENCION = 0.2
_ESPERA_BORRADO = 5.0
_PASO_BORRADO = 0.25

MENSAJE_AVANZADO = N_(
    "No se puede probar el equipo con un perfil de OBS en modo Avanzado. "
    "Pásalo a modo Sencillo y vuelve a intentarlo.")
MENSAJE_ERROR_RESTABLECER = N_(
    "La prueba dio un error: {error} No se pudo restablecer: {errores}.")
MENSAJE_RESTABLECER = N_(
    "La prueba terminó, pero no se pudo restablecer: {errores}.")


@dataclass(frozen=True)
class Preparacion:
    """Lo que hace falta para mostrar el cuadro previo y arrancar la prueba."""

    perfil: str
    ajustes: object
    disponibles: tuple
    segundos_maximos: int


@dataclass(frozen=True)
class PasoEquipo:
    """Lo medido en un escalón, con las diferencias de los contadores."""

    ajustes: object
    perdidos_dibujar: int
    totales_dibujar: int
    perdidos_codificar: int
    totales_codificar: int

    @property
    def porcentaje_dibujar(self) -> int:
        return _porcentaje(self.perdidos_dibujar, self.totales_dibujar)

    @property
    def porcentaje_codificar(self) -> int:
        return _porcentaje(self.perdidos_codificar, self.totales_codificar)

    @property
    def aguanta(self) -> bool:
        return escalones_equipo.aguanta(
            self.perdidos_dibujar, self.totales_dibujar,
            self.perdidos_codificar, self.totales_codificar)


@dataclass(frozen=True)
class ResultadoEquipo:
    """Los escalones medidos y los ajustes que aguantaron, si hubo alguno."""

    perfil: str
    original: object
    aguantaron: object
    pasos: tuple
    cancelada: bool = False
    grabaciones: tuple = ()

    @property
    def aguanta_tal_cual(self) -> bool:
        return self.aguantaron is not None and self.aguantaron == self.original

    @property
    def ultimo(self):
        return self.pasos[-1] if self.pasos else None


class ErrorPruebaEquipo(obs_cliente.ObsError):
    """La prueba dio un error y el restablecimiento no quedó completo."""

    def __init__(self, mensaje, errores=()):
        super().__init__(mensaje)
        self.errores = tuple(errores)


def _datos(cliente, tipo, datos=None, parada=None):
    respuesta = cliente.pedir(tipo, datos, parada) or {}
    return respuesta.get("responseData", respuesta or {})


def _porcentaje(perdidos, totales) -> int:
    if totales <= 0:
        return 0
    return int(round(100 * max(0, perdidos) / totales))


def _disponibles(disponibles):
    if disponibles is not None:
        return tuple(disponibles)
    return codificadores_obs.codificadores_disponibles()


def segundos_maximos(ajustes, disponibles, calentamiento=CALENTAMIENTO,
                     medicion=MEDICION) -> int:
    """Cuánto puede durar la prueba si prueba todos los escalones."""
    pasos = escalones_equipo.escalones(ajustes, _disponibles(disponibles))
    return int(round(len(pasos) * (calentamiento + medicion)))


def preparar(cliente, disponibles=None, calentamiento=CALENTAMIENTO,
             medicion=MEDICION, parada=None) -> Preparacion:
    """Comprueba que se pueda probar y arma los datos del cuadro previo."""
    ajustes = perfiles_obs.leer_ajustes(cliente, parada=parada)
    if perfiles_obs.esta_en_avanzado(cliente, parada=parada):
        raise obs_cliente.ObsError(_(MENSAJE_AVANZADO))
    _perfiles, perfil = perfiles_obs.listar_perfiles(cliente, parada)
    lista = _disponibles(disponibles)
    return Preparacion(perfil, ajustes, lista,
                       segundos_maximos(ajustes, lista, calentamiento,
                                        medicion))


def _con_calidad(ajustes, calidad):
    if ajustes.calidad_grabacion == calidad:
        return ajustes
    return replace(ajustes, calidad_grabacion=calidad)


def _pedir(cliente, parada):
    def pedir(tipo, datos=None, parada=parada):
        return _datos(cliente, tipo, datos, parada)
    return pedir


def _escena_al_aire(cliente, parada):
    return str(_datos(cliente, "GetCurrentProgramScene",
                      parada=parada).get("currentProgramSceneName") or "")


def _acomodar_fuente(pedir, escena, parada):
    """La deja en la esquina superior izquierda y por encima de todo."""
    elementos = pedir("GetSceneItemList", {"sceneName": escena}, parada) or {}
    items = list(elementos.get("sceneItems", ()))
    propio = next((item for item in items
                   if item.get("sourceName") == NOMBRE_FUENTE), None)
    if propio is None:
        return
    # La imagen cubre el lienzo: la fuente se ancla arriba a la izquierda,
    # porque al crearla OBS la centra y dejaría franjas sin movimiento.
    pedir("SetSceneItemTransform", {
        "sceneName": escena, "sceneItemId": propio["sceneItemId"],
        "sceneItemTransform": {"positionX": 0, "positionY": 0,
                               "alignment": 5}}, parada)
    mayor = max((item.get("sceneItemIndex", 0) for item in items), default=0)
    if propio.get("sceneItemIndex", 0) == mayor:
        return
    pedir("SetSceneItemIndex", {
        "sceneName": escena, "sceneItemId": propio["sceneItemId"],
        "sceneItemIndex": mayor}, parada)


def _preparar_escena(cliente, estado, parada, fps):
    estado["escena_original"] = _escena_al_aire(cliente, parada)
    pedir = _pedir(cliente, parada)
    escenas_obs.duplicar(pedir, estado["escena_original"], NOMBRE_ESCENA,
                         parada)
    estado["escena"] = True
    lienzo = _datos(cliente, "GetVideoSettings", parada=parada)
    ancho = int(lienzo.get("baseWidth", 1920))
    alto = int(lienzo.get("baseHeight", 1080))
    estado["entrada"] = {"url": movimiento_prueba.url(), "width": ancho,
                         "height": alto, "fps": fps, "fps_custom": True}
    _datos(cliente, "CreateInput", {
        "sceneName": NOMBRE_ESCENA,
        "inputName": NOMBRE_FUENTE,
        "inputKind": TIPO_FUENTE,
        "inputSettings": estado["entrada"],
    }, parada)
    estado["fuente"] = True
    _acomodar_fuente(pedir, NOMBRE_ESCENA, parada)
    _datos(cliente, "SetCurrentProgramScene",
           {"sceneName": NOMBRE_ESCENA}, parada)


def _esperar(parada, segundos, dormir):
    if parada is None:
        dormir(segundos)
        return False
    return parada.wait(segundos)


def _stats(cliente, parada):
    datos = _datos(cliente, "GetStats", parada=parada)
    return {clave: _entero(datos.get(clave)) for clave in (
        "renderSkippedFrames", "renderTotalFrames",
        "outputSkippedFrames", "outputTotalFrames")}


def _entero(valor):
    try:
        return max(0, int(valor or 0))
    except (TypeError, ValueError):
        return 0


def _esperar_detencion(cliente):
    """Espera a que OBS suelte el archivo después de StopRecord."""
    limite = time.monotonic() + _ESPERA_DETENCION
    while time.monotonic() < limite:
        try:
            if not _datos(cliente, "GetRecordStatus").get("outputActive"):
                return True
        except obs_cliente.ObsError as error:
            logger.debug("OBS no informó el fin de la grabación: %s", error)
            return False
        time.sleep(_PASO_DETENCION)
    return False


def _en_uso(error):
    return (isinstance(error, PermissionError)
            or getattr(error, "winerror", None) in (32, 33))


def _borrar(ruta):
    """Borra la grabación de la prueba; False si quedó tomada por OBS."""
    if not ruta:
        return True
    limite = time.monotonic() + _ESPERA_BORRADO
    while True:
        try:
            Path(ruta).unlink(missing_ok=True)
            return True
        except OSError as error:
            if not _en_uso(error) or time.monotonic() >= limite:
                logger.warning("la grabación de la prueba quedó en %s: %s",
                               ruta, error)
                return False
            time.sleep(_PASO_BORRADO)


def _medir(cliente, parada, ajustes, estado, calentamiento, medicion, dormir):
    if parada is not None and parada.is_set():
        return None, ""
    entrada = dict(estado["entrada"])
    entrada["fps"] = ajustes.fps
    _datos(cliente, "SetInputSettings", {
        "inputName": NOMBRE_FUENTE, "inputSettings": entrada}, parada)
    _datos(cliente, "StartRecord", parada=parada)
    archivo = ""
    sobrante = ""
    paso = None
    try:
        if not _esperar(parada, calentamiento, dormir):
            antes = _stats(cliente, parada)
            if not _esperar(parada, medicion, dormir):
                despues = _stats(cliente, parada)
                paso = PasoEquipo(
                    ajustes,
                    _diferencia(despues, antes, "renderSkippedFrames"),
                    _diferencia(despues, antes, "renderTotalFrames"),
                    _diferencia(despues, antes, "outputSkippedFrames"),
                    _diferencia(despues, antes, "outputTotalFrames"))
    finally:
        try:
            # La parada corta la prueba, no la limpieza: detener la
            # grabación con la parada puesta dejaría el archivo abierto.
            respuesta = _datos(cliente, "StopRecord")
            archivo = str(respuesta.get("outputPath") or "")
        finally:
            _esperar_detencion(cliente)
            if not _borrar(archivo):
                sobrante = archivo
    return paso, sobrante


def _diferencia(despues, antes, clave):
    return max(0, despues.get(clave, 0) - antes.get(clave, 0))


def _guardar(cliente, ajustes, perfil, parada):
    perfiles_obs.guardar_ajustes(cliente, ajustes, perfil, parada)


def _detener(cliente, sobrantes):
    if not _datos(cliente, "GetRecordStatus").get("outputActive"):
        return
    ruta = str(_datos(cliente, "StopRecord").get("outputPath") or "")
    _esperar_detencion(cliente)
    if not _borrar(ruta):
        sobrantes.append(ruta)


def _quitar_escena(cliente, estado, parada):
    if estado.get("escena"):
        _datos(cliente, "RemoveScene", {"sceneName": NOMBRE_ESCENA}, parada)
        estado["escena"] = False


def _quitar_fuente(cliente, estado, parada):
    if estado.get("fuente"):
        _datos(cliente, "RemoveInput", {"inputName": NOMBRE_FUENTE}, parada)
        estado["fuente"] = False


def _restaurar(cliente, original, perfil, estado, sobrantes):
    """Restablece OBS sin mirar la parada: cancelar no deja nada a medias."""
    errores = []

    def intentar(descripcion, accion):
        try:
            accion()
        except Exception as error:
            errores.append(f"{descripcion}: {error}")

    intentar(_("Detener la grabación de la prueba"),
             lambda: _detener(cliente, sobrantes))
    escena = estado.get("escena_original")
    if escena:
        intentar(_("Volver a la escena anterior"), lambda: _datos(
            cliente, "SetCurrentProgramScene", {"sceneName": escena}, None))
    intentar(_("Eliminar la escena de la prueba"),
             lambda: _quitar_escena(cliente, estado, None))
    intentar(_("Eliminar la fuente de la prueba"),
             lambda: _quitar_fuente(cliente, estado, None))
    intentar(_("Restablecer los ajustes del perfil"), lambda: _guardar(
        cliente, original, perfil, None))
    return errores


def ejecutar(cliente, parada=None, disponibles=None, al_escalon=None,
             calentamiento=CALENTAMIENTO, medicion=MEDICION,
             dormir=time.sleep) -> ResultadoEquipo:
    """Corre los escalones y devuelve lo medido; siempre restaura OBS."""
    original = perfiles_obs.leer_ajustes(cliente, parada=parada)
    if perfiles_obs.esta_en_avanzado(cliente, parada=parada):
        raise obs_cliente.ObsError(_(MENSAJE_AVANZADO))
    _perfiles, perfil = perfiles_obs.listar_perfiles(cliente, parada)
    trabajo = (replace(original, calidad_grabacion="Stream")
               if original.calidad_grabacion != "Stream" else original)
    estado = {}
    pasos = []
    sobrantes = []
    aguantaron = None
    cancelada = False
    error_original = None
    try:
        _preparar_escena(cliente, estado, parada, trabajo.fps)
        for ajustes in escalones_equipo.escalones(trabajo, _disponibles(disponibles)):
            if parada is not None and parada.is_set():
                cancelada = True
                break
            _guardar(cliente, ajustes, perfil, parada)
            if al_escalon is not None:
                al_escalon(ajustes)
            paso, sobrante = _medir(cliente, parada, ajustes, estado,
                                    calentamiento, medicion, dormir)
            if sobrante:
                sobrantes.append(sobrante)
            if paso is None:
                cancelada = True
                break
            pasos.append(paso)
            if paso.aguanta:
                aguantaron = _con_calidad(ajustes, original.calidad_grabacion)
                break
    except Exception as error:
        error_original = error
    finally:
        errores = _restaurar(cliente, original, perfil, estado, sobrantes)
    if error_original is not None:
        if errores:
            raise ErrorPruebaEquipo(_(MENSAJE_ERROR_RESTABLECER).format(
                error=error_original,
                errores=", ".join(errores)), errores) from error_original
        raise error_original
    if errores:
        raise ErrorPruebaEquipo(_(MENSAJE_RESTABLECER).format(
            errores=", ".join(errores)), errores)
    return ResultadoEquipo(perfil, original, aguantaron, tuple(pasos), cancelada, tuple(sobrantes))
