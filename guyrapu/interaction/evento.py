# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Cómo se ve un mensaje del directo, venga de donde venga.

Puro y sin wx. Única razón para cambiar: qué datos de un mensaje del chat
necesita la interacción con el público.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EventoDirecto:
    """Un mensaje del chat con los datos que la interacción necesita."""

    plataforma: str
    autor_id: str
    autor: str
    roles: frozenset[str]
    tipo: str
    texto: str
    monto: str
    id_mensaje: str = ""


def persona(evento: EventoDirecto) -> tuple[str, str]:
    """Identidad de quien escribe: su id dentro de su plataforma.

    Sin id, el nombre normalizado, para que un autor sin id cuente una sola
    vez.
    """
    if evento.autor_id:
        return (evento.plataforma, evento.autor_id)
    # Se importa acá para no cerrar el ciclo comandos -> evento.
    from guyrapu.interaction.comandos import normalizar
    return (evento.plataforma, normalizar(evento.autor))


def desde_entrante(autor, mensaje, tipo, monto, canal_id, rol,
                   plataforma) -> EventoDirecto:
    """Arma el evento de un mensaje tal como lo entrega una plataforma.

    `canal_id` es el id del autor; `rol` es un solo texto o "".
    """
    return EventoDirecto(
        plataforma=plataforma,
        autor_id=canal_id,
        autor=autor,
        roles=frozenset((rol,)) if rol else frozenset(),
        tipo=tipo,
        texto=mensaje,
        monto=monto,
    )
