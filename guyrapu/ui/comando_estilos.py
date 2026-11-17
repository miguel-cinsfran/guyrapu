# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Abrir la ventana Interacción en estilos del vídeo.

Un solo camino por acción, como pide la skill de interfaz accesible: el menú
Interacción llama acá.
"""

from __future__ import annotations

from guyrapu.ui import comando_interaccion


def abrir(frame):
    """Abre la ventana Interacción en la página de estilos del vídeo."""
    comando_interaccion.abrir(frame, "estilos")
