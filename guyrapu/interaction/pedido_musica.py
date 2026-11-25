# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Qué pedido de música del chat se agrega a la cola.

Puro y sin interfaz. Su única razón para cambiar es qué pedido se acepta:
recibe el texto, los ajustes de la sesión y los pendientes como datos, y
devuelve el tema o el motivo por el que no se sumó a la cola.
"""

from __future__ import annotations

from dataclasses import dataclass

from guyrapu.core.config_musica import DONDE_CONTINUACION
from guyrapu.core.idioma import N_, _
from guyrapu.downloads.busqueda_youtube import Filtros
from guyrapu.interaction import filtro_publico
from guyrapu.music import enlaces

MOTIVO_VACIO = N_("falta el nombre o el enlace del tema")
MOTIVO_SIN_RESULTADO = N_("la búsqueda no dio resultados")
MOTIVO_EN_DIRECTO = N_("el vídeo está en directo")
MOTIVO_PROGRAMADO = N_("el vídeo está programado")
MOTIVO_DURACION = N_("dura más de {minutos} minutos")
MOTIVO_SIN_DURACION = N_("no se pudo obtener la duración del vídeo")
MOTIVO_LISTA = N_("el enlace es de una lista de reproducción")
MOTIVO_ENLACE = N_("no se pudo abrir el enlace")
MOTIVO_PERSONA = N_("ya tiene {limite} pedidos pendientes")
MOTIVO_TOTAL = N_("ya hay {limite} pedidos pendientes")
MOTIVO_EN_COLA = N_("ya está en la cola")
MOTIVO_BLOQUEADO = N_("el título contiene una palabra bloqueada")


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


@dataclass(frozen=True, slots=True)
class Pendiente:
    """Un pedido aceptado que todavía no sonó, con quien lo pidió."""

    persona: tuple[str, str]
    url: str


@dataclass(frozen=True, slots=True)
class AjustesPedidos:
    """Los ajustes del grupo Pedidos del público, leídos en cada pedido."""

    donde: str = DONDE_CONTINUACION
    duracion: int = 10
    por_persona: int = 2
    total: int = 10
    responder: bool = True
    bloquear: bool = True


def ajustes_de(config) -> AjustesPedidos:
    """Traduce la config en memoria a los ajustes de la decisión."""
    config = config or {}
    return AjustesPedidos(
        donde=str(config.get("musica_pedidos_donde", DONDE_CONTINUACION)),
        duracion=_entero(config.get("musica_pedidos_duracion", 10), 10),
        por_persona=_entero(config.get("musica_pedidos_persona", 2), 2),
        total=_entero(config.get("musica_pedidos_total", 10), 10),
        responder=bool(config.get("musica_pedidos_responder", True)),
        bloquear=bool(config.get("musica_pedidos_bloquear", True)))


def _entero(valor, defecto):
    try:
        return int(valor)
    except (TypeError, ValueError):
        return defecto


def _texto(plantilla, **datos) -> str:
    return _(plantilla).format(**datos)


def clave_de(url) -> str:
    """La clave de un vídeo: su id de YouTube o la dirección normalizada."""
    identificador = enlaces.id_de_url(url)
    return identificador or (url or "").strip().lower()


def resolver(texto, buscar, expandir=enlaces.expandir,
             info=enlaces.info_estado_duracion, ajustes=None,
             pendientes=(), persona=(), palabras=()) -> Pedido:
    """Decide si el pedido entra con los límites y los ajustes de la sesión."""
    ajustes = ajustes or AjustesPedidos()
    motivo = _motivo_limites(pendientes, persona, ajustes)
    if motivo:
        return Pedido(motivo=motivo)
    limpio = (texto or "").strip() if isinstance(texto, str) else ""
    if not limpio:
        return Pedido(motivo=_texto(MOTIVO_VACIO))
    if enlaces.es_enlace_youtube(limpio):
        pedido = _desde_enlace(limpio, expandir, info, ajustes.duracion)
    else:
        pedido = _desde_busqueda(limpio, buscar, info, ajustes.duracion)
    if pedido.tema is None:
        return pedido
    if _repetido(pedido.tema.url, pendientes):
        return Pedido(motivo=_texto(MOTIVO_EN_COLA))
    if (ajustes.bloquear and filtro_publico.tapar(
            pedido.tema.titulo, palabras) != pedido.tema.titulo):
        return Pedido(motivo=_texto(MOTIVO_BLOQUEADO))
    return pedido


def _motivo_limites(pendientes, persona, ajustes) -> str:
    """El motivo del rechazo por llenar el cupo, antes de buscar el vídeo."""
    if not persona:
        return ""
    propios = sum(1 for pendiente in pendientes
                  if pendiente.persona == persona)
    if propios >= ajustes.por_persona:
        return _texto(MOTIVO_PERSONA, limite=ajustes.por_persona)
    if len(pendientes) >= ajustes.total:
        return _texto(MOTIVO_TOTAL, limite=ajustes.total)
    return ""


def _repetido(url, pendientes) -> bool:
    clave = clave_de(url)
    return bool(clave) and any(clave_de(p.url) == clave for p in pendientes)


def _desde_busqueda(limpio, buscar, info, minutos) -> Pedido:
    respuesta = buscar(limpio, Filtros(tipo="videos"), 1, 1)
    for resultado in getattr(respuesta, "resultados", ()) or ():
        if resultado.tipo != "video":
            continue
        if resultado.en_directo:
            return Pedido(motivo=_texto(MOTIVO_EN_DIRECTO))
        if resultado.programado:
            return Pedido(motivo=_texto(MOTIVO_PROGRAMADO))
        if not resultado.url or not resultado.titulo:
            return Pedido(motivo=_texto(MOTIVO_SIN_RESULTADO))
        duracion = resultado.duracion
        if not isinstance(duracion, int):
            try:
                informacion = info(resultado.url)
            except enlaces.ErrorEnlace:
                return Pedido(motivo=_texto(MOTIVO_SIN_DURACION))
            motivo = _motivo_de_estado(informacion)
            if motivo:
                return Pedido(motivo=motivo)
            duracion = informacion.duracion
        tema = TemaPedido(resultado.url, resultado.titulo, duracion)
        return _aceptar(tema, duracion, minutos)
    return Pedido(motivo=_texto(MOTIVO_SIN_RESULTADO))


def _motivo_de_estado(informacion) -> str:
    """El motivo por el que no se agrega un vídeo en directo o programado."""
    if informacion.programado:
        return _texto(MOTIVO_PROGRAMADO)
    if informacion.en_directo:
        return _texto(MOTIVO_EN_DIRECTO)
    return ""


def _aceptar(tema: TemaPedido, segundos: int, minutos: int) -> Pedido:
    """El tema si cabe en el límite de duración, o el motivo del rechazo."""
    if not isinstance(segundos, int) or segundos <= 0:
        return Pedido(motivo=_texto(MOTIVO_SIN_DURACION))
    if segundos > minutos * 60:
        return Pedido(motivo=_texto(MOTIVO_DURACION, minutos=minutos))
    return Pedido(tema)


def _desde_enlace(url, expandir, info, minutos) -> Pedido:
    """Los temas del enlace, que dice si es un vídeo suelto o una lista."""
    try:
        temas = expandir(url) or ()
    except enlaces.ErrorEnlace:
        return Pedido(motivo=_texto(MOTIVO_ENLACE))
    if len(temas) > 1:
        return Pedido(motivo=_texto(MOTIVO_LISTA))
    if not temas:
        return Pedido(motivo=_texto(MOTIVO_ENLACE))
    tema = temas[0]
    if not tema.origen or not tema.titulo:
        return Pedido(motivo=_texto(MOTIVO_ENLACE))
    try:
        informacion = info(tema.origen)
    except enlaces.ErrorEnlace:
        return Pedido(motivo=_texto(MOTIVO_ENLACE))
    motivo = _motivo_de_estado(informacion)
    if motivo:
        return Pedido(motivo=motivo)
    segundos = informacion.duracion
    if not isinstance(segundos, int) or segundos <= 0:
        milisegundos = tema.duracion_ms
        segundos = (milisegundos // 1000
                    if isinstance(milisegundos, int) and milisegundos > 0 else 0)
    return _aceptar(TemaPedido(tema.origen, tema.titulo, segundos), segundos,
                    minutos)
