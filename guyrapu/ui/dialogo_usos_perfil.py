# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Cuadro para asignar un perfil de OBS a transmitir o grabar.

Solo presenta la asignación: no guarda ni habla con OBS. La pestaña
Perfiles lee las casillas al aceptar y aplica los cambios.
"""

from __future__ import annotations

import wx

from guyrapu.core.idioma import N_, _
from guyrapu.ui import paleta, tecla_escape
from guyrapu.ui.accesibilidad import nombre_accesible
from guyrapu.ui.preferencias_comun import nombre_de_etiqueta

ROTULOS = (
    ("perfil_horizontal", N_("&Transmitir en horizontal")),
    ("perfil_vertical", N_("Transmitir en &vertical")),
    ("perfil_grabar", N_("&Grabar")),
)


class DialogoUsosPerfil(wx.Dialog):

    def __init__(self, padre, nombre, config):
        super().__init__(
            padre, title=_("Usar {nombre} para").format(nombre=nombre),
            name="DialogoUsosPerfil")
        self._crear_controles(nombre, config)
        paleta.pintar_ventana(self)
        self.Centre()

    def _crear_controles(self, nombre, config):
        caja = wx.BoxSizer(wx.VERTICAL)
        self.casillas = {}
        for clave, rotulo in ROTULOS:
            etiqueta = self._etiqueta(clave, rotulo, nombre, config)
            casilla = wx.CheckBox(
                self, label=etiqueta, name=nombre_de_etiqueta(etiqueta))
            nombre_accesible(casilla, casilla.GetName())
            casilla.SetValue((config.get(clave) or "") == nombre)
            self.casillas[clave] = casilla
            caja.Add(casilla, 0, wx.ALL, 6)
        caja.Add(self._fila_botones(), 0, wx.ALIGN_RIGHT | wx.ALL, 10)
        self.SetSizerAndFit(caja)
        self.SetMinSize((420, -1))
        self.Bind(wx.EVT_CHAR_HOOK, self._al_tecla)
        next(iter(self.casillas.values())).SetFocus()

    def _etiqueta(self, clave, rotulo, nombre, config):
        otro = config.get(clave) or ""
        if otro and otro != nombre:
            return "{rotulo} {ahora}".format(
                rotulo=_(rotulo),
                ahora=_("(ahora: {nombre})").format(nombre=otro))
        return _(rotulo)

    def _fila_botones(self):
        fila = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_aceptar = wx.Button(
            self, wx.ID_OK, _("&Aceptar"),
            name=nombre_de_etiqueta(_("&Aceptar")))
        self.btn_cancelar = wx.Button(
            self, wx.ID_CANCEL, _("&Cancelar"),
            name=nombre_de_etiqueta(_("&Cancelar")))
        for boton in (self.btn_aceptar, self.btn_cancelar):
            nombre_accesible(boton, boton.GetName())
        self.btn_aceptar.SetDefault()
        fila.Add(self.btn_aceptar, 0, wx.RIGHT, 6)
        fila.Add(self.btn_cancelar, 0)
        return fila

    def marcados(self):
        """Clave de uso a si su casilla quedó marcada."""
        return {clave: casilla.GetValue()
                for clave, casilla in self.casillas.items()}

    def _al_tecla(self, evento):
        tecla_escape.cancelar_si_escape(self, evento)
