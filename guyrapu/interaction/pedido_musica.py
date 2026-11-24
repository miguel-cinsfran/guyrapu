# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Qué pedido de música del chat se agrega a la cola.

Puro y sin interfaz. Su única razón para cambiar es qué pedido se acepta:
recibe el texto, una función de búsqueda y una de expansión de enlaces, y
devuelve el tema o el motivo por el que no se sumó a la cola.
"""

from __future__ import annotations

from dataclasses import dataclass

from guyrapu.core.idioma import N_
from guyrapu.downloads.busqueda_youtube import Filtros
from guyrapu.music import enlaces

MAXIMO_SEGUNDOS = 600

MOTIVO_VACIO = N_("falta el nombre o el enlace del tema")
MOTIVO_SIN_RESULTADO = N_("la búsqueda no dio resultados")
MOTIVO_EN_DIRECTO = N_("el vídeo está en directo")
MOTIVO_PROGRAMADO = N_("el vídeo está programado")
MOTIVO_DURACION = N_("dura más de 10 minutos")
MOTIVO_SIN_DURACION = N_("no se pudo obtener la duración del vídeo")
MOTIVO_LISTA = N_("el enlace es de una lista de reproducción")
MOTIVO_ENLACE = N_("no se pudo abrir el enlace")


@dataclass(frozen=True, slots=True)
class TemaPedido:
    """El vídeo que se suma a la cola, con su duración en segundos."""

    url: str
    titulo: str
    duracion: int


@dataclass(frozen=True, slots=True)
class Pedido:
    """El tema aceptado, o el motivo por el que no se agregó."""

    tema: TemaPedido | None = None
    motivo: str = ""


def resolver(texto, buscar, expandir=enlaces.expandir,
             info=enlaces.info_estado_duracion) -> Pedido:
    """Busca el tema del texto o abre el enlace, y dice si se puede agregar."""
    limpio = (texto or "").strip() if isinstance(texto, str) else ""
    if not limpio:
        return Pedido(motivo=MOTIVO_VACIO)
    if enlaces.es_enlace_youtube(limpio):
        return _desde_enlace(limpio, expandir, info)
    respuesta = buscar(limpio, Filtros(tipo="videos"), 1, 1)
    for resultado in getattr(respuesta, "resultados", ()) or ():
        if resultado.tipo != "video":
            continue
        if resultado.en_directo:
            return Pedido(motivo=MOTIVO_EN_DIRECTO)
        if resultado.programado:
            return Pedido(motivo=MOTIVO_PROGRAMADO)
        if not resultado.url or not resultado.titulo:
            return Pedido(motivo=MOTIVO_SIN_RESULTADO)
        duracion = resultado.duracion
        if not isinstance(duracion, int):
            try:
                informacion = info(resultado.url)
            except enlaces.ErrorEnlace:
                return Pedido(motivo=MOTIVO_SIN_DURACION)
            motivo = _motivo_de_estado(informacion)
            if motivo:
                return Pedido(motivo=motivo)
            duracion = informacion.duracion
        tema = TemaPedido(resultado.url, resultado.titulo, duracion)
        return _aceptar(tema, duracion)
    return Pedido(motivo=MOTIVO_SIN_RESULTADO)


def _motivo_de_estado(informacion) -> str:
    """El motivo por el que no se agrega un vídeo en directo o programado."""
    if informacion.programado:
        return MOTIVO_PROGRAMADO
    if informacion.en_directo:
        return MOTIVO_EN_DIRECTO
    return ""


def _aceptar(tema: TemaPedido, segundos: int) -> Pedido:
    """El tema si cabe en el límite de duración, o el motivo del rechazo."""
    if not isinstance(segundos, int) or segundos <= 0:
        return Pedido(motivo=MOTIVO_SIN_DURACION)
    if segundos > MAXIMO_SEGUNDOS:
        return Pedido(motivo=MOTIVO_DURACION)
    return Pedido(tema)


def _desde_enlace(url, expandir, info) -> Pedido:
    """Los temas del enlace, que dice si es un vídeo suelto o una lista."""
    try:
        temas = expandir(url) or ()
    except enlaces.ErrorEnlace:
        return Pedido(motivo=MOTIVO_ENLACE)
    if len(temas) > 1:
        return Pedido(motivo=MOTIVO_LISTA)
    if not temas:
        return Pedido(motivo=MOTIVO_ENLACE)
    tema = temas[0]
    if not tema.origen or not tema.titulo:
        return Pedido(motivo=MOTIVO_ENLACE)
    try:
        informacion = info(tema.origen)
    except enlaces.ErrorEnlace:
        return Pedido(motivo=MOTIVO_ENLACE)
    motivo = _motivo_de_estado(informacion)
    if motivo:
        return Pedido(motivo=motivo)
    segundos = informacion.duracion
    if not isinstance(segundos, int) or segundos <= 0:
        milisegundos = tema.duracion_ms
        segundos = (milisegundos // 1000
                    if isinstance(milisegundos, int) and milisegundos > 0 else 0)
    return _aceptar(TemaPedido(tema.origen, tema.titulo, segundos), segundos)
