# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""La fila de botones de una lista con acciones.

No es una superficie: la recorren las ventanas que arman con ella.
"""

from __future__ import annotations

import wx

from guyrapu.ui.preferencias_comun import nombre_de_etiqueta

ANCHO_MINIMO = 96
HUECO = 8


def armar(panel, acciones=(), lista=None, *, botones=None):
    """Arma la fila de botones de una lista con acciones.

    Con `botones` se colocan los que ya creó una página, como Perfiles de OBS.
    """
    fila = wx.WrapSizer(wx.HORIZONTAL, flags=0)
    if botones is None:
        botones = []
        for accion in acciones:
            boton = wx.Button(panel, label=accion.etiqueta,
                              name=nombre_de_etiqueta(accion.etiqueta))
            boton.Bind(wx.EVT_BUTTON,
                       lambda _evento, clave=accion.clave:
                       lista.ejecutar(clave))
            botones.append(boton)
    ancho = max([ANCHO_MINIMO]
                + [boton.GetBestSize().GetWidth() for boton in botones])
    for boton in botones:
        boton.SetMinSize((ancho, -1))
        fila.Add(boton, 0, wx.RIGHT | wx.BOTTOM, HUECO)
    return fila
