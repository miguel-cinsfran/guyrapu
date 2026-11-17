# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Abrir la ventana Interacción en mensajes y activarlos o desactivarlos.

Un solo camino por acción, como pide la skill de interfaz accesible: el menú,
su casilla y la casilla de la ventana llaman acá.
"""

from __future__ import annotations

from guyrapu.core.idioma import _
from guyrapu.ui import comando_interaccion


def abrir(frame):
    """Abre la ventana Interacción en la página de mensajes automáticos."""
    comando_interaccion.abrir(frame, "mensajes")


def alternar(frame):
    """Invierte la activación, la guarda, marca el menú y la anuncia."""
    from guyrapu.ui import gui
    nuevo = not bool(frame._config.get("programados_activo", False))
    frame._config["programados_activo"] = nuevo
    gui.guardar_opcion(gui.RUTA_CONFIG, "programados", "activo",
                       "true" if nuevo else "false")
    item = getattr(frame, "mi_programados_activo", None)
    if item is not None:
        item.Check(nuevo)
    gui.anunciar(_("Mensajes automáticos activados") if nuevo
                 else _("Mensajes automáticos desactivados"))
