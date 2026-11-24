# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pieza común de los cuadros de formulario.

No es una ventana: arma las filas, las secciones, las casillas y el pie con
una sola medida por hueco. Los cuadros no repiten números de espaciado.
"""

from __future__ import annotations

import wx

from guyrapu.core.idioma import N_

SECCION_CUANDO = N_("Activación")
SECCION_ALCANCE = N_("Permiso y espera")

MARGEN = 16
ETIQUETA_A_CONTROL = 4
CONTROL_A_ETIQUETA = 12
ANTES_DE_TITULO = 20
ENTRE_COLUMNAS = 16
ENTRE_CASILLAS = 8
ENTRE_BOTONES = 8
MARGEN_DE_SECCION = 8
ANTES_DEL_PIE = 16

ANCHO_MINIMO = 440
ANCHO_COLUMNA = 300
ANCHO_NUMERICO = 96
ANCHO_MINIMO_BOTON = 96

ALTO_MAXIMO = 728


def armar_pagina(panel, contenido):
    """Pone el contenido con el margen común y se lo da a la página."""
    exterior = wx.BoxSizer(wx.VERTICAL)
    exterior.Add(contenido, 1, wx.EXPAND | wx.ALL, MARGEN)
    panel.SetSizer(exterior)


def agregar_fila(sizer, rotulo, control, *, expandir=True, numerico=False):
    """Agrega el rótulo y su control, ya creados en ese orden, con el ritmo común."""
    alto = CONTROL_A_ETIQUETA if sizer.GetChildren() else 0
    if rotulo is not None:
        sizer.Add(rotulo, 0, wx.TOP, alto)
    if numerico:
        control.SetMinSize((ANCHO_NUMERICO, -1))
        banderas = wx.TOP
    elif expandir:
        banderas = wx.EXPAND | wx.TOP
    else:
        banderas = wx.TOP
    borde = alto if rotulo is None else ETIQUETA_A_CONTROL
    sizer.Add(control, 0, banderas, borde)


def agregar_bloque(sizer, bloque, *, junto=False):
    """Agrega un sizer o una ventana a lo ancho, con el hueco común arriba."""
    hueco = ETIQUETA_A_CONTROL if junto else CONTROL_A_ETIQUETA
    alto = hueco if sizer.GetChildren() else 0
    sizer.Add(bloque, 0, wx.EXPAND | wx.TOP, alto)


def agregar_nota(sizer, nota):
    """Agrega el texto que acompaña al control de arriba, a lo ancho."""
    sizer.Add(nota, 0, wx.EXPAND | wx.TOP, ETIQUETA_A_CONTROL)


def agregar_seccion_con_caja(columna, panel, titulo):
    """Agrega una caja con el título de la app y devuelve su contenido y su caja."""
    caja = wx.StaticBox(panel, label=titulo)
    sizer = wx.StaticBoxSizer(caja, wx.VERTICAL)
    alto = ANTES_DE_TITULO if columna.GetChildren() else 0
    columna.Add(sizer, 0, wx.EXPAND | wx.TOP, alto)
    interior = wx.BoxSizer(wx.VERTICAL)
    sizer.Add(interior, 0,
              wx.EXPAND | wx.TOP | wx.LEFT | wx.RIGHT | wx.BOTTOM,
              MARGEN_DE_SECCION)
    return interior, sizer


def agregar_seccion(columna, panel, titulo):
    """Agrega una caja con el título de la app y devuelve su contenido."""
    interior, _sizer = agregar_seccion_con_caja(columna, panel, titulo)
    return interior


def agregar_casillas(sizer, casillas):
    """Casillas seguidas, en dos columnas y con el hueco común."""
    columnas = 1 if len(casillas) == 1 else 2
    grilla = wx.GridSizer(0, columnas, ENTRE_CASILLAS, ENTRE_CASILLAS)
    for casilla in casillas:
        grilla.Add(casilla, 0, wx.EXPAND)
    alto = CONTROL_A_ETIQUETA if sizer.GetChildren() else 0
    sizer.Add(grilla, 0, wx.EXPAND | wx.TOP, alto)


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
    borde = cuadro.GetSize().height - cuadro.GetClientSize().height
    cuadro.SetClientSize((ancho, min(alto, ALTO_MAXIMO - borde)))
    cuadro.Layout()
