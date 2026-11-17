# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Qué mensaje del chat vale la pena traducir.

Puro, sin red ni ventanas. Su única razón para cambiar es qué mensaje se
manda a traducir y cuál se lee tal cual.
"""

from __future__ import annotations

import re

_ENLACE = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
_EXPRESIONES = (
    re.compile(r"g+"),
    re.compile(r"x+d+"),
    re.compile(r"l+o+l+"),
    re.compile(r"(?:ja)+j?"),
)


def traducible(texto, propio=False):
    """Dice si el mensaje se manda a traducir o se lee tal cual."""
    if propio:
        return False
    letras = "".join(caracter for caracter in _ENLACE.sub(" ", texto)
                     if caracter.isalpha())
    if len(letras) < 3:
        return False
    return not _es_expresion(letras.lower())


def _es_expresion(letras):
    return any(patron.fullmatch(letras) for patron in _EXPRESIONES)
