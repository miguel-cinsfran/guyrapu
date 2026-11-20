# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Cuadro que elige de qué tipos es predeterminado un estilo del vídeo.

Recoge las casillas y no guarda: la ventana de estilos maneja la colección y
el disco.
"""

from __future__ import annotations

import wx

from guyrapu.core.idioma import N_, _
from guyrapu.obs import estilos_aviso
from guyrapu.ui import formulario, paleta, tecla_escape

TITULO = N_("Establecer como predeterminado")


class DialogoTipos(wx.Dialog):
    """Las casillas de tipos, marcadas las que ya usan el estilo."""

    def __init__(self, padre, marcados):
        super().__init__(padre, title=_(TITULO),
                         name="DialogoEstiloPredeterminado")
        self._crear_controles(marcados)
        self.Fit()
        self.Centre()
        paleta.pintar_ventana(self)
        self._casillas[estilos_aviso.TIPOS[0][0]].SetFocus()

    def _crear_controles(self, marcados):
        panel = wx.Panel(self, name="PanelEstiloPredeterminado")
        vs = wx.BoxSizer(wx.VERTICAL)
        self._casillas = {}
        for tipo, nombre in estilos_aviso.TIPOS:
            casilla = wx.CheckBox(panel, label=_(nombre), name=_(nombre))
            casilla.SetValue(tipo in marcados)
            self._casillas[tipo] = casilla
        formulario.agregar_casillas(vs, self._casillas.values(), hueco=0)
        self.btn_aceptar = wx.Button(panel, wx.ID_OK, _("&Aceptar"),
                                     name=_("Aceptar"))
        self.btn_cancelar = wx.Button(panel, wx.ID_CANCEL, _("&Cancelar"),
                                      name=_("Cancelar"))
        self.btn_aceptar.SetDefault()
        self.btn_aceptar.Bind(wx.EVT_BUTTON, self._aceptar)
        self.btn_cancelar.Bind(
            wx.EVT_BUTTON, lambda _evento: self.EndModal(wx.ID_CANCEL))
        formulario.agregar_pie(vs, [self.btn_aceptar, self.btn_cancelar])
        formulario.ajustar_tamano(self, panel, vs)
        self.Bind(wx.EVT_CHAR_HOOK, self._al_tecla)

    def marcados(self) -> set[str]:
        """Los tipos que quedan marcados."""
        return {tipo for tipo, casilla in self._casillas.items()
                if casilla.GetValue()}

    def _aceptar(self, _evento):
        self.EndModal(wx.ID_OK)

    def _al_tecla(self, evento):
        tecla_escape.cancelar_si_escape(self, evento)


def abrir(padre, marcados):
    """Abre el cuadro y devuelve los tipos marcados, o None si se cancela."""
    dialogo = DialogoTipos(padre, marcados)
    try:
        if dialogo.ShowModal() != wx.ID_OK:
            return None
        return dialogo.marcados()
    finally:
        dialogo.Destroy()
