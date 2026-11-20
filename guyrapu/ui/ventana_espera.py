# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Ventana común para una operación larga, con su sonido de espera.

Su única razón para cambiar es cómo se ve y se oye una espera: el estado en
un campo de texto que se puede leer, Cancelar mientras trabaja y el sonido
«espera» cada dos segundos. Desde el hilo de trabajo se llama solo a través
de `wx.CallAfter`, como los cuadros que reemplaza.
"""

from __future__ import annotations

import wx

from guyrapu.core.idioma import _
from guyrapu.ui import formulario
from guyrapu.ui.accesibilidad import anunciar, nombre_accesible
from guyrapu.ui.espera_sonora import EsperaSonora
from guyrapu.ui.preferencias_comun import nombre_de_etiqueta

_PROPIEDADES_TEXTO = wx.TE_MULTILINE | wx.TE_READONLY


class VentanaEspera(wx.Dialog):
    """El avance de una operación larga, con Cancelar si se puede cortar."""

    def __init__(self, padre, titulo, texto_inicial, parada=None):
        super().__init__(padre, title=titulo, name="VentanaEspera")
        self._parada = parada
        self._terminada = False
        self._btn = None
        self._crear_controles(titulo, texto_inicial)
        self._espera = EsperaSonora(self)
        self.Bind(wx.EVT_CLOSE, self._al_cerrar)
        self.Bind(wx.EVT_WINDOW_DESTROY, self._al_destruir)
        self._espera.empezar()

    def _crear_controles(self, titulo, texto_inicial):
        self._panel = wx.Panel(self, name="PanelEspera")
        self.txt_estado = wx.TextCtrl(
            self._panel, style=_PROPIEDADES_TEXTO, name=titulo)
        nombre_accesible(self.txt_estado, titulo)
        self.txt_estado.SetMinSize((-1, 100))
        self.txt_estado.SetValue(texto_inicial)
        if self._parada is not None:
            self._btn = self._crear_boton(_("&Cancelar"))
        self._armar()
        self.Centre()
        self.txt_estado.SetFocus()

    def _armar(self):
        caja = wx.BoxSizer(wx.VERTICAL)
        formulario.agregar_fila(caja, None, self.txt_estado)
        if self._btn is not None:
            formulario.agregar_pie(caja, [self._btn])
        formulario.ajustar_tamano(self, self._panel, caja)

    def _crear_boton(self, etiqueta):
        control = wx.Button(self._panel, wx.ID_CANCEL, etiqueta,
                            name=nombre_de_etiqueta(etiqueta))
        nombre_accesible(control, control.GetName())
        control.Bind(wx.EVT_BUTTON, self._al_boton)
        return control

    def estado(self, texto):
        self.txt_estado.SetValue(texto)
        anunciar(texto)

    def _al_boton(self, _evento):
        if self._terminada:
            self.EndModal(wx.ID_CANCEL)
        else:
            self._cancelar()

    def _cancelar(self):
        if self._parada is None or self._parada.is_set():
            return
        self._parada.set()
        self._espera.detener()
        frase = _("Cancelando…")
        self.txt_estado.SetValue(frase)
        anunciar(frase)

    def terminar(self, texto, error=False):
        self._terminada = True
        self._espera.terminar("error" if error else "listo")
        self.txt_estado.SetValue(texto)
        anunciar(texto)
        self._poner_cerrar()

    def _poner_cerrar(self):
        if self._btn is None:
            self._btn = self._crear_boton(_("&Cerrar"))
            self._armar()
        else:
            self._btn.SetLabel(_("&Cerrar"))
            nombre_accesible(self._btn, nombre_de_etiqueta(_("&Cerrar")))
            self._btn.Enable()
        self._btn.SetFocus()

    def _al_cerrar(self, evento):
        self._espera.detener()
        evento.Skip()

    def _al_destruir(self, evento):
        self._espera.detener()
        evento.Skip()
