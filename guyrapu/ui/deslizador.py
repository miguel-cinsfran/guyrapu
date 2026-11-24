# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pieza de armado de los deslizadores accesibles de la app."""

from __future__ import annotations

import wx

from guyrapu.ui.accesibilidad import nombre_accesible

ANCHO = 280  # El ancho del cuadro combinado de salida de audio de la página Voces.


def deslizador_accesible(padre, minimo, maximo, inicial, paso, nombre):
    """Un deslizador horizontal con su nombre, su valor y las flechas de un paso."""
    # Sin SL_VALUE_LABEL: su rótulo de valor tapa la tecla de acceso que anuncia NVDA.
    control = wx.Slider(
        padre, value=inicial, minValue=minimo, maxValue=maximo,
        style=wx.SL_HORIZONTAL, name=nombre)
    control.SetMinSize((ANCHO, -1))
    control.SetLineSize(paso)
    nombre_accesible(control, nombre)
    return control
