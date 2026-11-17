# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Abrir la ventana de mensajes automáticos y activarlos o desactivarlos.

Un solo camino por acción, como pide la skill de interfaz accesible: el menú,
su casilla y la casilla de la ventana llaman acá.
"""

from __future__ import annotations

from guyrapu.core import paths
from guyrapu.core.idioma import _
from guyrapu.capture import programados
from guyrapu.ui import mensajes_automaticos_ventana


def abrir(frame):
    """Abre la ventana y, al cerrarla, recarga la lista del disco."""
    mensajes_automaticos_ventana.abrir(frame, lambda: _recargar(frame))


def _recargar(frame):
    frame.programador.recargar(
        programados.cargar(paths.mensajes_programados()))


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
