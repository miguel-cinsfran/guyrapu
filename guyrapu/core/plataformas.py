# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Plataformas de chat que reconoce Guyrapu y cómo se presentan.

Puro y sin wx. Única razón para cambiar: qué plataformas de chat conoce
Guyrapu, cómo se llaman, con qué sonido suena su mensaje común y si se
pueden moderar desde la app.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Plataforma:
    """Una plataforma de chat y lo que la app necesita saber de ella."""

    id: str
    nombre: str
    sonido: str
    moderable: bool


YOUTUBE = "youtube"
TIKTOK = "tiktok"

PLATAFORMAS: dict[str, Plataforma] = {
    YOUTUBE: Plataforma(YOUTUBE, "YouTube", "mensaje_nuevo", True),
    TIKTOK: Plataforma(TIKTOK, "TikTok", "mensaje_tiktok", False),
}


def obtener(identificador: str) -> Plataforma | None:
    """La plataforma con ese id, o None si la app no la conoce."""
    return PLATAFORMAS.get((identificador or "").lower())


def nombre(identificador: str) -> str:
    """Nombre visible y hablado de la plataforma, o cadena vacía."""
    plataforma = obtener(identificador)
    return plataforma.nombre if plataforma else ""


def sonido(identificador: str) -> str:
    """Sonido de un mensaje común de la plataforma; el de siempre si no hay."""
    plataforma = obtener(identificador)
    return plataforma.sonido if plataforma else "mensaje_nuevo"


def moderable(identificador: str) -> bool:
    """Si la moderación de esa plataforma se hace desde Guyrapu."""
    plataforma = obtener(identificador)
    return bool(plataforma and plataforma.moderable)


def sufijo(identificador: str) -> str:
    """« - Nombre» para la fila y la voz, o cadena vacía si no se conoce."""
    nombre_plataforma = nombre(identificador)
    return f" - {nombre_plataforma}" if nombre_plataforma else ""


def texto_con_nombre(texto: str, identificador: str, config: dict,
                     varios_chats: bool) -> str:
    """Agrega el nombre de la plataforma al texto de la voz si corresponde."""
    if not varios_chats or not config.get("decir_plataforma", False):
        return texto
    return texto + sufijo(identificador)
