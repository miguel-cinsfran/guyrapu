# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Ventana canario del carril: tres controles conocidos y un anuncio.

La abre `correr.py` en un proceso aparte. El orden de Tab es el de creación:
el campo con la etiqueta «Nombre:», la casilla «Opción de prueba» y el botón
«Aceptar». Al mostrarse anuncia «Canario listo» por el lector, que en esta
corrida es el sintetizador espía. Se cierra con Alt+F4 mandado desde NVDA.
"""

from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

TITULO = "Canario del carril"
ANUNCIO = "Canario listo"


def main() -> int:
    import wx

    from guyrapu.voice.lector import Lector

    app = wx.App(False)
    marco = wx.Frame(None, title=TITULO)
    panel = wx.Panel(marco)
    caja = wx.BoxSizer(wx.VERTICAL)
    caja.Add(wx.StaticText(panel, label="Nombre:"), 0,
             wx.ALL, 6)
    campo = wx.TextCtrl(panel)
    campo.SetName("Nombre:")
    caja.Add(campo, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 6)
    casilla = wx.CheckBox(panel, label="Opción de prueba")
    caja.Add(casilla, 0, wx.ALL, 6)
    boton = wx.Button(panel, label="Aceptar")
    caja.Add(boton, 0, wx.ALL, 6)
    panel.SetSizer(caja)
    marco.Fit()
    marco.Centre()
    lector = Lector()

    def al_mostrar(evento):
        if not evento.IsShown():
            return
        campo.SetFocus()
        lector.speak(ANUNCIO)

    marco.Bind(wx.EVT_SHOW, al_mostrar)
    marco.Show()
    app.MainLoop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
