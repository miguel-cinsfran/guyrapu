# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Cuadro Filtros del micrófono: ruido, puerta y ganancia de la fuente de OBS.

No habla con OBS: recibe el estado ya leído y devuelve el que se eligió para
que la pestaña Audio lo aplique.
"""

from __future__ import annotations

import wx

from guyrapu.core.idioma import _
from guyrapu.obs.filtros_microfono import GANANCIAS, Estado
from guyrapu.ui import formulario, paleta, tecla_escape
from guyrapu.ui.preferencias_comun import (
    fila_label, lista_con_nombre, nombre_de_etiqueta)


class FiltrosMicrofonoDialog(wx.Dialog):
    """Pide eliminación de ruido, puerta y ganancia del micrófono."""

    def __init__(self, padre, fuente, estado):
        super().__init__(
            padre,
            title=_("Filtros del micrófono: {fuente}").format(fuente=fuente),
            name="DialogoFiltrosMicrofono")
        self._elegido = None
        self._crear_controles(estado)
        paleta.pintar_ventana(self)
        self.Centre()
        self.chk_ruido.SetFocus()

    def _crear_controles(self, estado):
        self._panel = wx.Panel(self)
        caja = wx.BoxSizer(wx.VERTICAL)
        self.chk_ruido = self._casilla(
            _("&Eliminación de ruido"), estado.eliminacion)
        self.chk_puerta = self._casilla(
            _("&Puerta anti-ruidos"), estado.puerta)
        formulario.agregar_casillas(caja, (self.chk_ruido, self.chk_puerta))
        self._crear_ganancia(caja, estado)
        self._crear_botones(caja)
        formulario.ajustar_tamano(self, self._panel, caja)
        self.btn_aceptar.Bind(wx.EVT_BUTTON, self._al_aceptar)
        self.btn_cancelar.Bind(wx.EVT_BUTTON, self._al_cancelar)
        self.Bind(wx.EVT_CHAR_HOOK, self._al_tecla)

    def _casilla(self, etiqueta, valor):
        casilla = wx.CheckBox(
            self._panel, label=etiqueta, name=nombre_de_etiqueta(etiqueta))
        casilla.SetValue(bool(valor))
        return casilla

    def _crear_ganancia(self, caja, estado):
        etiqueta = _("&Ganancia:")
        self.rotulo_ganancia = fila_label(self._panel, etiqueta)
        self.cho_ganancia = lista_con_nombre(
            self._panel, etiqueta, [_(nombre) for _db, nombre in GANANCIAS])
        self.cho_ganancia.SetSelection(self._indice_de(estado.ganancia_db))
        formulario.agregar_fila(
            caja, self.rotulo_ganancia, self.cho_ganancia)

    @staticmethod
    def _indice_de(db):
        for indice, (valor, _nombre) in enumerate(GANANCIAS):
            if valor == db:
                return indice
        return 0

    def _crear_botones(self, caja):
        self.btn_aceptar = wx.Button(
            self._panel, wx.ID_OK, _("&Aceptar"), name=_("Aceptar"))
        self.btn_aceptar.SetDefault()
        self.btn_cancelar = wx.Button(
            self._panel, wx.ID_CANCEL, _("&Cancelar"), name=_("Cancelar"))
        formulario.agregar_pie(caja, [self.btn_aceptar, self.btn_cancelar])

    def estado_elegido(self):
        return self._elegido

    def _al_aceptar(self, _event):
        indice = self.cho_ganancia.GetSelection()
        ganancia = GANANCIAS[indice][0] if indice >= 0 else 0
        self._elegido = Estado(
            self.chk_ruido.GetValue(), self.chk_puerta.GetValue(), ganancia)
        self.EndModal(wx.ID_OK)

    def _al_cancelar(self, _event):
        self.EndModal(wx.ID_CANCEL)

    def _al_tecla(self, event):
        tecla_escape.cancelar_si_escape(self, event)


def pedir_filtros(padre, fuente, estado):
    """Abre el cuadro y devuelve el estado elegido, o None si se cancela."""
    dialogo = FiltrosMicrofonoDialog(padre, fuente, estado)
    try:
        if dialogo.ShowModal() == wx.ID_OK:
            return dialogo.estado_elegido()
        return None
    finally:
        dialogo.Destroy()
