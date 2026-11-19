# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Qué registro arma un mensaje de ensayo y qué destinos tiene.

No importa `MensajeChat`: `guyrapu.interaction` no puede importar de
`guyrapu.ui` (R16). El registro tiene la misma forma, así que el controlador
del chat lo recibe sin convertirlo.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from guyrapu.core.config import TIPO_SUPERCHAT, TIPO_TEXTO
from guyrapu.core.idioma import N_

MENSAJE = "mensaje"
SUPER_CHAT = "superchat"
REGALO = "regalo"

# Traductores: autor de fábrica de los mensajes de la ventana de ensayo.
AUTOR_PREDETERMINADO = N_("Público de prueba")


@dataclass(frozen=True, slots=True)
class MensajeEnsayo:
    """Una fila del chat de ensayo, con los campos que espera `chat_vivo`."""

    plataforma: str
    autor: str
    identificador: str
    texto: str
    hora: str
    tipo: str
    monto: str
    rol: str = ""
    nivel: int = 0


def registro(autor, mensaje, plataforma, tipo, cantidad="", ahora=None):
    """Arma el registro desde los campos de la ventana de ensayo."""
    momento = ahora or datetime.now()
    if tipo == MENSAJE:
        tipo_interno, monto = TIPO_TEXTO, ""
    elif tipo == REGALO:
        tipo_interno, monto = TIPO_SUPERCHAT, f"{cantidad} diamantes"
    else:
        tipo_interno, monto = TIPO_SUPERCHAT, cantidad
    return MensajeEnsayo(
        plataforma=plataforma, autor=autor, identificador="", texto=mensaje,
        hora=momento.strftime("%H:%M:%S"), tipo=tipo_interno, monto=monto)


def destinos():
    """El ensayo no tiene chat: solo va al vídeo."""
    return {"video"}


def en_ensayo(frame) -> bool:
    """Si la ventana de ensayo está abierta en ese marco."""
    return getattr(frame, "_ensayo", False) is True


def en_vivo_o_ensayo(frame) -> bool:
    """Si el marco está conectado al directo o en ensayo."""
    return bool(getattr(frame, "_conectado", False)) or en_ensayo(frame)
