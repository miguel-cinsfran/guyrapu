# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Acciones de la lista de escenas del Panel de OBS."""

from __future__ import annotations

from guyrapu.core.idioma import N_, _
from guyrapu.ui.lista_acciones import Accion

_ACCIONES = (
    ("cambiar", N_("&Cambiar escena"), "intro"),
    ("renombrar", N_("Cambiar &nombre…"), "f2"),
    ("duplicar", N_("&Duplicar"), "ctrl+d"),
    ("vertical", N_("Crear la versión &vertical"), None),
    ("eliminar", N_("E&liminar"), "suprimir"),
    ("guardar", N_("&Guardar imagen…"), None),
)


def acciones_de_escena(cambiar, renombrar, duplicar, eliminar, guardar,
                       version_vertical=None, motivo=None):
    """Las acciones de la escena elegida, en el orden del menú."""
    manejadores = (cambiar, renombrar, duplicar, version_vertical, eliminar,
                   guardar)
    return tuple(
        Accion(clave, _(etiqueta), manejador, tecla=tecla, motivo=motivo)
        for (clave, etiqueta, tecla), manejador in zip(_ACCIONES, manejadores)
        if clave != "vertical" or version_vertical is not None)
