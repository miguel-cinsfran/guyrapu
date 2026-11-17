# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Abrir la ventana de estilos del vídeo.

Un solo camino por acción, como pide la skill de interfaz accesible: el menú
Interacción llama acá.
"""

from __future__ import annotations

from guyrapu.ui import estilos_ventana


def abrir(frame):
    """Abre la ventana de estilos del vídeo."""
    estilos_ventana.abrir(frame)
