# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pieza de armado de los deslizadores accesibles de la app."""

from __future__ import annotations

import wx

from guyrapu.ui.accesibilidad import nombre_accesible


def deslizador_accesible(padre, minimo, maximo, inicial, paso, nombre):
    """Un deslizador horizontal con su nombre y las flechas de un paso."""
    control = wx.Slider(padre, value=inicial, minValue=minimo,
                        maxValue=maximo, style=wx.SL_HORIZONTAL, name=nombre)
    control.SetLineSize(paso)
    nombre_accesible(control, nombre)
    return control
