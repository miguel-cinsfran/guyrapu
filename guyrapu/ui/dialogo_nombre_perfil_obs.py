# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Cuadro del nombre de un perfil de OBS, para crearlo o duplicarlo."""

from __future__ import annotations

import wx

from guyrapu.core.idioma import _
from guyrapu.obs import perfiles_obs
from guyrapu.ui.accesibilidad import nombre_accesible
from guyrapu.ui.preferencias_comun import nombre_de_etiqueta


class DialogoNombrePerfil(wx.Dialog):
    """Pide el nombre y, para uno nuevo, la orientación."""

    def __init__(self, padre, existentes=(), con_orientacion=False,
                 titulo="", accion=""):
        super().__init__(padre, title=titulo or _("Nombre del perfil"),
                         name="DialogoNombrePerfil")
        self._existentes = {str(nombre) for nombre in existentes}
        self._con_orientacion = con_orientacion
        caja = wx.BoxSizer(wx.VERTICAL)
        self.rot_nombre = wx.StaticText(self, label=_("&Nombre:"))
        self.txt_nombre = wx.TextCtrl(
            self, name=nombre_de_etiqueta(_("&Nombre:")))
        nombre_accesible(self.txt_nombre, self.txt_nombre.GetName())
        fila = wx.BoxSizer(wx.HORIZONTAL)
        fila.Add(self.rot_nombre, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 6)
        fila.Add(self.txt_nombre, 1, wx.EXPAND | wx.ALL, 6)
        caja.Add(fila, 0, wx.EXPAND)
        if con_orientacion:
            self.rad_orientacion = wx.RadioBox(
                self, label=_("Orientación"),
                choices=[_("Horizontal"), _("Vertical")], majorDimension=2,
                style=wx.RA_SPECIFY_ROWS, name=_("Orientación"))
            nombre_accesible(self.rad_orientacion, _("Orientación"))
            self.rad_orientacion.SetSelection(0)
            caja.Add(self.rad_orientacion, 0, wx.ALL, 6)
        self.txt_error = wx.StaticText(self, label="")
        caja.Add(self.txt_error, 0, wx.LEFT | wx.RIGHT, 8)
        fila_botones = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_aceptar = wx.Button(
            self, wx.ID_OK, accion or _("C&rear"),
            name=nombre_de_etiqueta(accion or _("C&rear")))
        self.btn_cancelar = wx.Button(
            self, wx.ID_CANCEL, _("&Cancelar"),
            name=nombre_de_etiqueta(_("&Cancelar")))
        self.btn_aceptar.SetDefault()
        fila_botones.Add(self.btn_aceptar, 0, wx.RIGHT, 6)
        fila_botones.Add(self.btn_cancelar, 0)
        caja.Add(fila_botones, 0, wx.ALIGN_RIGHT | wx.ALL, 10)
        self.SetSizerAndFit(caja)
        self.SetMinSize((420, -1))
        self.Centre()
        self.btn_aceptar.Bind(wx.EVT_BUTTON, self._al_aceptar)
        self.txt_nombre.SetFocus()

    def _al_aceptar(self, _evento):
        nombre = self.nombre()
        if not nombre:
            self.txt_error.SetLabel(_("Escribe un nombre para el perfil."))
            self.txt_nombre.SetFocus()
            self.Layout()
            self.Fit()
            return
        if nombre in self._existentes:
            self.txt_error.SetLabel(_(perfiles_obs.MENSAJE_EXISTE))
            self.txt_nombre.SetFocus()
            self.Layout()
            self.Fit()
            return
        self.EndModal(wx.ID_OK)

    def nombre(self) -> str:
        return self.txt_nombre.GetValue().strip()

    def vertical(self) -> bool:
        if not self._con_orientacion:
            return False
        return self.rad_orientacion.GetSelection() == 1
