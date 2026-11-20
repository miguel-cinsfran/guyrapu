# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Cuadro para elegir la ventana que captura la escena del Panel de OBS."""

from __future__ import annotations

import wx

from guyrapu.capture import redaccion
from guyrapu.core.idioma import _
from guyrapu.obs import consultas_transmision
from guyrapu.ui import formulario, paleta, tecla_escape
from guyrapu.ui.accesibilidad import anunciar
from guyrapu.ui.preferencias_comun import (
    boton, fila_label, lista_con_nombre, nombre_de_etiqueta)


class DialogoCapturarVentana(wx.Dialog):
    """Pide una ventana; el foco empieza en la lista."""

    def __init__(self, padre, opciones, actual):
        super().__init__(padre, title=_("Capturar ventana"),
                         name="DialogoCapturarVentana")
        self._valores = [valor for _texto, valor in opciones or ()]
        self._crear_controles(opciones, actual)
        paleta.pintar_ventana(self)
        self.Centre()
        self.cho_ventana.SetFocus()

    def _crear_controles(self, opciones, actual):
        self._panel = wx.Panel(self)
        vertical = wx.BoxSizer(wx.VERTICAL)
        self.rotulo_ventana = fila_label(self._panel, _("&Ventana:"))
        self.cho_ventana = lista_con_nombre(
            self._panel, _("&Ventana:"),
            [texto for texto, _valor in opciones or ()])
        self.cho_ventana.SetSelection(self._seleccion(actual))
        formulario.agregar_fila(
            vertical, self.rotulo_ventana, self.cho_ventana)
        self.aviso_vacio = None
        self._vacio = _("No hay ventanas para capturar.")
        if not opciones:
            self.aviso_vacio = wx.StaticText(self._panel, label=self._vacio)
            self.aviso_vacio.Wrap(
                formulario.ANCHO_MINIMO - 2 * formulario.MARGEN)
            formulario.agregar_fila(vertical, None, self.aviso_vacio, hueco=0)
        self._crear_botones(self._panel)
        formulario.agregar_pie(
            vertical, [self.btn_aceptar, self.btn_cancelar])
        formulario.ajustar_tamano(self, self._panel, vertical)
        self._enlazar_eventos()

    def _seleccion(self, actual):
        if actual in self._valores:
            return self._valores.index(actual)
        return wx.NOT_FOUND

    def _crear_botones(self, panel):
        self.btn_aceptar = boton(
            panel, _("&Aceptar"), nombre_de_etiqueta(_("&Aceptar")),
            wx.ID_OK)
        self.btn_aceptar.SetDefault()
        self.btn_cancelar = boton(
            panel, _("&Cancelar"), nombre_de_etiqueta(_("&Cancelar")),
            wx.ID_CANCEL)
        if not self._valores:
            self.btn_aceptar.SetLabel(redaccion.etiqueta_con_motivo(
                _("&Aceptar"), self._vacio.rstrip(".")))

    def _enlazar_eventos(self):
        self.btn_aceptar.Bind(wx.EVT_BUTTON, self._al_aceptar)
        self.btn_cancelar.Bind(wx.EVT_BUTTON, self._al_cancelar)
        self.Bind(wx.EVT_CHAR_HOOK, self._al_tecla)

    def valor(self):
        indice = self.cho_ventana.GetSelection()
        if indice == wx.NOT_FOUND or indice < 0 or indice >= len(self._valores):
            return ""
        return self._valores[indice]

    def _al_aceptar(self, _event):
        if not self._valores:
            anunciar(self._vacio)
            return
        if not self.valor():
            anunciar(_("Elige primero una ventana en Ventana."))
            return
        self.EndModal(wx.ID_OK)

    def _al_cancelar(self, _event):
        self.EndModal(wx.ID_CANCEL)

    def _al_tecla(self, event):
        tecla_escape.cancelar_si_escape(self, event)


def pedir_valor(padre, opciones, actual):
    """Abre el cuadro de ventanas y devuelve la elegida, sin aplicarla."""
    dialogo = DialogoCapturarVentana(padre, opciones, actual)
    try:
        if dialogo.ShowModal() != wx.ID_OK:
            return None
        return dialogo.valor() or None
    finally:
        dialogo.Destroy()


def pedir_ventana(padre, gestor, operaciones, escena, al_aplicar, al_cerrar):
    """Pide las ventanas a OBS en el hilo y abre el cuadro."""
    if operaciones.en_vuelo:
        return
    operaciones.en_hilo(
        lambda: gestor.ventanas(escena),
        lambda datos: _abrir(padre, gestor, operaciones, escena, datos,
                             al_aplicar, al_cerrar))


def _abrir(padre, gestor, operaciones, escena, datos, al_aplicar, al_cerrar):
    opciones, actual = datos
    dialogo = DialogoCapturarVentana(padre, opciones, actual)
    try:
        aceptado = dialogo.ShowModal() == wx.ID_OK
        valor = dialogo.valor()
    finally:
        dialogo.Destroy()
    al_cerrar()
    if not aceptado or not valor:
        return
    if operaciones.en_vuelo:
        return
    operaciones.en_hilo(
        lambda: consultas_transmision.aplicar_ventana(gestor, escena, valor),
        al_aplicar)
