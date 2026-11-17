# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Cómo se comparan textos del chat.

Puro y sin wx. Única razón para cambiar: cómo se normalizan los textos que
se escriben en el chat.
"""

from __future__ import annotations

import unicodedata


def _sin_tildes(caracter: str) -> str:
    if caracter == "ñ":
        return caracter
    descompuesto = unicodedata.normalize("NFD", caracter)
    return "".join(parte for parte in descompuesto
                   if not unicodedata.combining(parte))


def normalizar(texto: str) -> str:
    """Minúsculas, sin tildes y sin espacios en los extremos.

    La eñe se conserva: `año` y `ano` son nombres distintos.
    """
    return "".join(_sin_tildes(caracter)
                   for caracter in (texto or "").strip().lower())
