# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pieza común de los cuadros de formulario.

No es una ventana: arma las filas, las secciones, las casillas y el pie con
una sola medida por hueco. Los cuadros no repiten números de espaciado.
"""

from __future__ import annotations

import wx

MARGEN = 16
ETIQUETA_A_CONTROL = 4
CONTROL_A_ETIQUETA = 12
ANTES_DE_TITULO = 20
ENTRE_COLUMNAS = 16
ENTRE_CASILLAS = 8
ENTRE_BOTONES = 8
ANTES_DEL_PIE = 16

ANCHO_MINIMO = 440
ANCHO_COLUMNA = 300
ANCHO_NUMERICO = 96
ANCHO_MINIMO_BOTON = 96

ALTO_MAXIMO = 728


def agregar_fila(sizer, rotulo, control, *, expandir=True,
                 numerico=False, hueco=CONTROL_A_ETIQUETA):
    """Agrega el rótulo y su control, ya creados en ese orden, con el ritmo común."""
    if rotulo is not None:
        sizer.Add(rotulo, 0, wx.BOTTOM, ETIQUETA_A_CONTROL)
    if numerico:
        control.SetMinSize((ANCHO_NUMERICO, -1))
        banderas = wx.BOTTOM
    elif expandir:
        banderas = wx.EXPAND | wx.BOTTOM
    else:
        banderas = wx.BOTTOM
    sizer.Add(control, 0, banderas, hueco)


def agregar_seccion(columna, panel, titulo):
    """Agrega una caja de grupo con el título de la app y devuelve su sizer."""
    caja = wx.StaticBox(panel, label=titulo)
    sizer = wx.StaticBoxSizer(caja, wx.VERTICAL)
    alto = ANTES_DE_TITULO if columna.GetChildren() else 0
    columna.Add(sizer, 0, wx.EXPAND | wx.TOP, alto)
    return sizer


def agregar_casillas(sizer, casillas, *, hueco=CONTROL_A_ETIQUETA):
    """Casillas seguidas, en dos columnas y con el hueco común."""
    columnas = 1 if len(casillas) == 1 else 2
    grilla = wx.GridSizer(0, columnas, ENTRE_CASILLAS, ENTRE_CASILLAS)
    for casilla in casillas:
        grilla.Add(casilla, 0, wx.EXPAND)
    sizer.Add(grilla, 0, wx.EXPAND | wx.BOTTOM, hueco)


def agregar_pie(contenido, botones):
    """Botones abajo a la derecha, del mismo ancho y con el hueco común."""
    ancho = max([ANCHO_MINIMO_BOTON]
                + [boton.GetBestSize().GetWidth() for boton in botones])
    fila = wx.BoxSizer(wx.HORIZONTAL)
    for indice, boton in enumerate(botones):
        boton.SetMinSize((ancho, -1))
        derecha = ENTRE_BOTONES if indice < len(botones) - 1 else 0
        fila.Add(boton, 0, wx.RIGHT, derecha)
    contenido.Add(fila, 0, wx.ALIGN_RIGHT | wx.TOP, ANTES_DEL_PIE)


def columnas(contenido, izquierda, derecha):
    """Dos columnas del mismo ancho para las secciones lado a lado."""
    lado_a_lado = wx.BoxSizer(wx.HORIZONTAL)
    izquierda.SetMinSize((ANCHO_COLUMNA, -1))
    derecha.SetMinSize((ANCHO_COLUMNA, -1))
    lado_a_lado.Add(izquierda, 1, wx.EXPAND | wx.RIGHT, ENTRE_COLUMNAS)
    lado_a_lado.Add(derecha, 1, wx.EXPAND)
    contenido.Add(lado_a_lado, 1, wx.EXPAND)


def ajustar_tamano(cuadro, panel, contenido):
    """Pone el margen, el ancho mínimo y el tope de alto del cuadro."""
    exterior = wx.BoxSizer(wx.VERTICAL)
    exterior.Add(contenido, 1, wx.EXPAND | wx.ALL, MARGEN)
    panel.SetSizer(exterior)
    marco = wx.BoxSizer(wx.VERTICAL)
    marco.Add(panel, 1, wx.EXPAND)
    cuadro.SetSizer(marco)
    cuadro.Layout()
    ancho, alto = marco.GetMinSize()
    ancho = max(ANCHO_MINIMO, ancho)
    cuadro.SetMinSize((ancho, -1))
    cuadro.SetMaxSize((-1, ALTO_MAXIMO))
    cuadro.SetClientSize((ancho, min(alto, ALTO_MAXIMO)))
    cuadro.Layout()
