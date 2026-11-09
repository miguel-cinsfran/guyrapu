# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Cómo se llaman los perfiles que crea el asistente de perfiles de OBS.

Puro, sin OBS ni interfaz. Los tres nombres base se traducen al mostrarse y
`libre` resuelve el primero que no esté ocupado.
"""

from __future__ import annotations

from guyrapu.core.idioma import N_

NOMBRE_HORIZONTAL = N_("Guyrapu horizontal")
NOMBRE_VERTICAL = N_("Guyrapu vertical")
NOMBRE_GRABACION = N_("Guyrapu grabación")


def libre(base, existentes) -> str:
    """El nombre base o, si ya existe, el primero libre con « 2», « 3»..."""
    ocupados = set(existentes or ())
    if base not in ocupados:
        return base
    numero = 2
    while f"{base} {numero}" in ocupados:
        numero += 1
    return f"{base} {numero}"
