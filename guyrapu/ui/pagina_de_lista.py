# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Cómo se distribuyen el rótulo, la lista y los botones de una página de lista.

Cambiar el espaciado acá alcanza a las nueve páginas de Interacción a la vez.
"""

from __future__ import annotations

import wx

from guyrapu.ui import botonera, formulario

BORDE_ROTULO = formulario.MARGEN
BORDE_LISTA = formulario.MARGEN
BORDE_BOTONES = formulario.MARGEN - botonera.HUECO
ESPACIO_ROTULO_LISTA = formulario.ETIQUETA_A_CONTROL
ESPACIO_LISTA_BOTONES = formulario.CONTROL_A_ETIQUETA
PROPORCION_LISTA = 1
BANDERAS_ROTULO = wx.LEFT | wx.RIGHT | wx.TOP
BANDERAS_ROTULO_SIN_SUPERIOR = wx.LEFT | wx.RIGHT
BANDERAS_LISTA = wx.EXPAND | wx.LEFT | wx.RIGHT
BANDERAS_BOTONES = wx.EXPAND | wx.LEFT | wx.RIGHT


def agregar_lista(sizer, rotulo, lista, *, borde_superior=True):
    """Pone el rótulo y la lista, en ese orden, en el sizer vertical."""
    banderas = (BANDERAS_ROTULO if borde_superior
                else BANDERAS_ROTULO_SIN_SUPERIOR)
    sizer.Add(rotulo, 0, banderas, BORDE_ROTULO)
    sizer.AddSpacer(ESPACIO_ROTULO_LISTA)
    sizer.Add(lista, PROPORCION_LISTA, BANDERAS_LISTA, BORDE_LISTA)


def agregar_botones(sizer, fila):
    """Pone la fila de botones al final del sizer vertical."""
    sizer.AddSpacer(ESPACIO_LISTA_BOTONES)
    sizer.Add(fila, 0, BANDERAS_BOTONES, BORDE_LISTA)
    sizer.AddSpacer(BORDE_BOTONES)
