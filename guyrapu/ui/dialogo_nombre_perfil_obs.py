# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Cuadro del nombre de un perfil de OBS, para crearlo o duplicarlo."""

from __future__ import annotations

import wx

from guyrapu.core.idioma import _
from guyrapu.obs import perfiles_obs
from guyrapu.ui import formulario, paleta, tema
from guyrapu.ui.accesibilidad import nombre_accesible
from guyrapu.ui.preferencias_comun import fila_label, nombre_de_etiqueta


class DialogoNombrePerfil(wx.Dialog):
    """Pide el nombre y, para uno nuevo, la orientación."""

    def __init__(self, padre, existentes=(), con_orientacion=False,
                 titulo="", accion=""):
        super().__init__(padre, title=titulo or _("Nombre del perfil"),
                         name="DialogoNombrePerfil")
        self._existentes = {str(nombre) for nombre in existentes}
        self._con_orientacion = con_orientacion
        panel = wx.Panel(self, name="PanelNombrePerfil")
        caja = wx.BoxSizer(wx.VERTICAL)
        rotulo = fila_label(panel, _("&Nombre:"))
        self.txt_nombre = wx.TextCtrl(
            panel, name=nombre_de_etiqueta(_("&Nombre:")))
        nombre_accesible(self.txt_nombre, self.txt_nombre.GetName())
        formulario.agregar_fila(caja, rotulo, self.txt_nombre, hueco=0)
        if con_orientacion:
            self.rad_orientacion = wx.RadioBox(
                panel, label=_("Orientación"),
                choices=[_("Horizontal"), _("Vertical")], majorDimension=2,
                style=wx.RA_SPECIFY_ROWS, name=_("Orientación"))
            nombre_accesible(self.rad_orientacion, _("Orientación"))
            self.rad_orientacion.SetSelection(0)
            formulario.agregar_fila(caja, None, self.rad_orientacion,
                                    hueco=0)
        self.txt_error = wx.StaticText(panel, label="")
        formulario.agregar_fila(caja, None, self.txt_error, hueco=0)
        self.btn_aceptar = wx.Button(
            panel, wx.ID_OK, accion or _("C&rear"),
            name=nombre_de_etiqueta(accion or _("C&rear")))
        self.btn_cancelar = wx.Button(
            panel, wx.ID_CANCEL, _("&Cancelar"),
            name=nombre_de_etiqueta(_("&Cancelar")))
        self.btn_aceptar.SetDefault()
        tema.boton_principal(self.btn_aceptar)
        formulario.agregar_pie(caja, [self.btn_aceptar, self.btn_cancelar])
        formulario.ajustar_tamano(self, panel, caja)
        paleta.pintar_ventana(self)
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
