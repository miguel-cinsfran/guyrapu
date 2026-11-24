# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Cómo se distribuyen el rótulo, la lista y los botones de una página de lista.

Cambiar el espaciado acá alcanza a las nueve páginas de Interacción a la vez.
"""

from __future__ import annotations

import wx

BORDE_ROTULO = 10
BORDE_LISTA = 10
BORDE_BOTONES = 10
PROPORCION_ROTULO = 0
PROPORCION_LISTA = 1
PROPORCION_BOTONES = 0
BANDERAS_ROTULO = wx.LEFT | wx.RIGHT | wx.TOP
BANDERAS_ROTULO_SIN_SUPERIOR = wx.LEFT | wx.RIGHT
BANDERAS_LISTA = wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM
BANDERAS_BOTONES = wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM


def agregar_lista(sizer, rotulo, lista, *, borde_superior=True):
    """Pone el rótulo y la lista, en ese orden, en el sizer vertical."""
    banderas = (BANDERAS_ROTULO if borde_superior
                else BANDERAS_ROTULO_SIN_SUPERIOR)
    sizer.Add(rotulo, PROPORCION_ROTULO, banderas, BORDE_ROTULO)
    sizer.Add(lista, PROPORCION_LISTA, BANDERAS_LISTA, BORDE_LISTA)


def agregar_botones(sizer, fila):
    """Pone la fila de botones al final del sizer vertical."""
    sizer.Add(fila, PROPORCION_BOTONES, BANDERAS_BOTONES, BORDE_BOTONES)
