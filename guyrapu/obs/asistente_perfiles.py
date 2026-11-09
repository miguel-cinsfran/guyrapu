# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""El recorrido del asistente de perfiles de OBS, sin interfaz.

Crea un perfil por cada uso marcado, prueba el equipo con los de transmitir,
guarda lo que aguantó y devuelve lo hecho. Si se corta o falla, elimina lo
creado en esta corrida y vuelve al perfil que tenía OBS, en un `finally`.
No guarda la configuración: eso lo hace la pestaña con el resultado.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from guyrapu.core import diagnostico
from guyrapu.core.idioma import N_, _
from guyrapu.obs import (escalones_equipo, escena_gemela, nombres_asistente,
                         obs_cliente, perfiles_obs, prueba_equipo,
                         usos_perfil)

logger = diagnostico.obtener_logger(__name__)

USOS = (
    ("perfil_horizontal", nombres_asistente.NOMBRE_HORIZONTAL, False),
    ("perfil_vertical", nombres_asistente.NOMBRE_VERTICAL, True),
    ("perfil_grabar", nombres_asistente.NOMBRE_GRABACION, False),
)

MENSAJE_NINGUNO_AGUANTO = N_(
    "Ningún ajuste aguantó: se guardó el último escalón probado.")
MENSAJE_SIN_CAMBIOS = N_("Sin cambios.")
MENSAJE_ELIMINADOS = N_("Se eliminaron los perfiles creados: {nombres}.")
MENSAJE_NO_ELIMINADOS = N_("No se pudo eliminar: {nombres}.")


@dataclass(frozen=True)
class PerfilPreparado:
    """Un perfil creado por el asistente y lo que le pasó."""

    nombre: str
    uso: str
    ajustes: object
    anterior: str = ""
    probado: bool = False
    cambios: str = ""
    aguanto: bool = True


@dataclass(frozen=True)
class ResultadoAsistente:
    """Los perfiles que quedaron creados o la marca de que se canceló."""

    perfiles: tuple = ()
    cancelada: bool = False


class ErrorAsistente(obs_cliente.ObsError):
    """El recorrido falló y la limpieza dejó o no dejó perfiles."""

    def __init__(self, mensaje, eliminados=(), quedaron=()):
        super().__init__(mensaje)
        self.eliminados = tuple(eliminados)
        self.quedaron = tuple(quedaron)


def _puesta(parada) -> bool:
    return parada is not None and parada.is_set()


def _existentes(cliente, parada):
    return perfiles_obs.listar_perfiles(cliente, parada)[0]


def _ajustes_grabacion(ajustes):
    """Salida igual al lienzo, calidad para archivo mediano y formato mkv."""
    return replace(ajustes,
                   ancho_salida=ajustes.ancho_lienzo,
                   alto_salida=ajustes.alto_lienzo,
                   calidad_grabacion="Small",
                   formato_grabacion="mkv")


def _describir(perfil):
    texto = escalones_equipo.describir(perfil.ajustes)
    if perfil.uso == "perfil_grabar":
        texto += ", " + _("grabación en formato {formato}, calidad alta para "
                          "archivo mediano").format(
                              formato=perfil.ajustes.formato_grabacion)
    return texto


def lineas_resumen(resultado, tiktok_sin_restream=True):
    """El resumen del asistente, una línea por perfil y lo que falta a mano."""
    lineas = []
    vertical = ""
    for perfil in resultado.perfiles:
        texto = _("Perfil «{nombre}» {uso}: {ajustes}.").format(
            nombre=perfil.nombre,
            uso=usos_perfil.texto_para([perfil.uso]),
            ajustes=_describir(perfil))
        if perfil.probado and perfil.cambios:
            texto += " " + _("Prueba del equipo: {cambios}").format(
                cambios=perfil.cambios)
        if perfil.anterior and perfil.anterior != perfil.nombre:
            texto += " " + _("Antes ese uso lo tenía «{anterior}».").format(
                anterior=perfil.anterior)
        lineas.append(texto)
        if perfil.uso == "perfil_vertical":
            vertical = perfil.nombre
    if vertical:
        if tiktok_sin_restream:
            lineas.append(_(
                "Para TikTok sin Restream, escribe el servidor y la clave en "
                "«Editar ajustes» del perfil «{nombre}».").format(
                    nombre=vertical))
        lineas.append(_(
            "Crea la versión vertical de las escenas con «Crear la versión "
            "vertical»."))
    return tuple(lineas)


def _probar(cliente, preparado, prueba, disponibles, parada, anunciar):
    anunciar(_("Probando el equipo con {nombre}: {ajustes}…").format(
        nombre=preparado.nombre,
        ajustes=escalones_equipo.describir(preparado.ajustes)))
    resultado = escena_gemela.en_perfil(
        cliente, preparado.nombre,
        lambda: prueba(cliente, parada=parada, disponibles=disponibles),
        parada)
    if resultado.cancelada:
        return preparado, True
    if resultado.aguantaron is not None:
        if resultado.aguanta_tal_cual:
            return replace(preparado, ajustes=resultado.aguantaron,
                           probado=True, cambios=_(MENSAJE_SIN_CAMBIOS),
                           aguanto=True), False
        perfiles_obs.guardar_ajustes(cliente, resultado.aguantaron,
                                     preparado.nombre, parada)
        return replace(preparado, ajustes=resultado.aguantaron, probado=True,
                       cambios=escalones_equipo.diferencias(
                           resultado.original, resultado.aguantaron),
                       aguanto=True), False
    ultimo = resultado.ultimo
    ajustes = ultimo.ajustes if ultimo is not None else preparado.ajustes
    perfiles_obs.guardar_ajustes(cliente, ajustes, preparado.nombre, parada)
    return replace(preparado, ajustes=ajustes, probado=True,
                   cambios=_(MENSAJE_NINGUNO_AGUANTO), aguanto=False), False


def _deshacer(cliente, inicial, creados):
    """Vuelve al perfil de antes y elimina lo creado; devuelve lo que quedó."""
    if inicial:
        try:
            perfiles_obs.cambiar(cliente, inicial, None)
        except obs_cliente.ObsError as error:
            logger.debug("no se pudo volver al perfil %s: %s", inicial, error)
    quedaron = []
    for nombre in reversed(creados):
        try:
            perfiles_obs.eliminar_perfil(cliente, nombre, None)
        except obs_cliente.ObsError as error:
            logger.warning("el perfil %s quedó en OBS: %s", nombre, error)
            quedaron.append(nombre)
    return quedaron


def _error_con_limpieza(error, creados, quedaron):
    eliminados = [nombre for nombre in creados if nombre not in quedaron]
    partes = [str(error)]
    if eliminados:
        partes.append(_(MENSAJE_ELIMINADOS).format(
            nombres=", ".join(eliminados)))
    if quedaron:
        partes.append(_(MENSAJE_NO_ELIMINADOS).format(
            nombres=", ".join(quedaron)))
    return ErrorAsistente(" ".join(partes), eliminados, quedaron)


def _crear_uno(cliente, uso, base, vertical, probar, disponibles, parada,
               anteriores, anunciar, prueba, creados):
    """Crea el perfil de un uso y, si toca, lo prueba. (perfil, cortada)."""
    nombre = nombres_asistente.libre(_(base), _existentes(cliente, parada))
    anunciar(_("Creando el perfil {nombre}…").format(nombre=nombre))
    ajustes = perfiles_obs.crear_perfil(
        cliente, nombre, vertical=vertical, codificadores=disponibles,
        parada=parada)
    creados.append(nombre)
    if uso == "perfil_grabar":
        ajustes = _ajustes_grabacion(ajustes)
        perfiles_obs.guardar_ajustes(cliente, ajustes, nombre, parada)
    preparado = PerfilPreparado(
        nombre=nombre, uso=uso, ajustes=ajustes,
        anterior=str(anteriores.get(uso) or ""))
    if probar and uso in ("perfil_horizontal", "perfil_vertical"):
        return _probar(cliente, preparado, prueba, disponibles, parada,
                       anunciar)
    return preparado, False


def preparar(cliente, usos, probar=True, parada=None, anunciar=None,
             disponibles=None, anteriores=None, prueba=None):
    """Crea, prueba y deja listos los perfiles de los usos marcados.

    `usos` son las claves de `usos_perfil`. Devuelve un `ResultadoAsistente`
    con lo creado; si se cancela, lo creado se elimina y se avisa con
    `cancelada`. Los errores salen como `ErrorAsistente`.
    """
    anunciar = anunciar or (lambda texto: None)
    anteriores = dict(anteriores or {})
    prueba = prueba or prueba_equipo.ejecutar
    creados = []
    preparados = []
    cancelada = False
    error = None
    quedaron = []
    inicial = ""
    try:
        perfiles_obs.comprobar_salidas(cliente, parada)
        _perfiles, inicial = perfiles_obs.listar_perfiles(cliente, parada)
        for uso, base, vertical in USOS:
            if uso not in usos:
                continue
            if _puesta(parada):
                cancelada = True
                break
            preparado, cortada = _crear_uno(
                cliente, uso, base, vertical, probar, disponibles, parada,
                anteriores, anunciar, prueba, creados)
            if cortada:
                cancelada = True
                break
            preparados.append(preparado)
    except Exception as exc:
        if _puesta(parada):
            cancelada = True
        else:
            error = exc
    finally:
        if cancelada or error is not None:
            quedaron = _deshacer(cliente, inicial, creados)
    if cancelada:
        return ResultadoAsistente((), cancelada=True)
    if error is not None:
        raise _error_con_limpieza(error, creados, quedaron) from error
    return ResultadoAsistente(tuple(preparados))
