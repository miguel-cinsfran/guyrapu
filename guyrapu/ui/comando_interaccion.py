# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Abrir la ventana Interacción en una página y releer los mensajes al cerrar.

Un solo camino por acción, como pide la skill de interfaz accesible: el menú,
su atajo y los tres comandos llaman acá.
"""

from __future__ import annotations

from guyrapu.capture import programados
from guyrapu.core import paths
from guyrapu.ui import interaccion_ventana


def abrir(frame, pagina=None):
    """Muestra la ventana, guarda la página a la vista y recarga la lista."""
    ventana = interaccion_ventana.VentanaInteraccion(frame, pagina)
    try:
        ventana.ShowModal()
    finally:
        guardada = ventana.pagina_actual()
        ventana.Destroy()
    from guyrapu.ui import gui
    frame._config["interaccion_pagina"] = guardada
    gui.guardar_opcion(
        gui.RUTA_CONFIG, "ui", "interaccion_pagina", guardada)
    frame.programador.recargar(
        programados.cargar(paths.mensajes_programados()))
