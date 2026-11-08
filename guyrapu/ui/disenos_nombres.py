# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Nombres de los diseños de escena guardados."""

from __future__ import annotations

import wx

from guyrapu.core.idioma import _


def pedir_nombre(padre, inicial):
    """Pide un nombre para guardar el diseño, o None si se cancela."""
    dialogo = wx.TextEntryDialog(
        padre, _("Nombre del diseño:"), _("Guardar diseño"), value=inicial)
    try:
        if dialogo.ShowModal() == wx.ID_OK:
            return dialogo.GetValue()
        return None
    finally:
        dialogo.Destroy()


def buscar_guardado(guardados, nombre):
    """El índice del diseño guardado con ese nombre, o None."""
    buscado = nombre.casefold()
    for indice, (guardado, _diseno) in enumerate(guardados):
        if guardado.casefold() == buscado:
            return indice
    return None
