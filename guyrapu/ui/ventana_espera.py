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

from guyrapu.core import diagnostico
from guyrapu.core.idioma import _
from guyrapu.ui.accesibilidad import anunciar, nombre_accesible
from guyrapu.ui.preferencias_comun import nombre_de_etiqueta
from guyrapu.voice import sound_player

logger = diagnostico.obtener_logger(__name__)

_PROPIEDADES_TEXTO = wx.TE_MULTILINE | wx.TE_READONLY
_INTERVALO_ESPERA_MS = 2000


class VentanaEspera(wx.Dialog):
    """El avance de una operación larga, con Cancelar si se puede cortar."""

    def __init__(self, padre, titulo, texto_inicial, parada=None):
        super().__init__(padre, title=titulo, name="VentanaEspera")
        self._parada = parada
        self._terminada = False
        self._btn = None
        self._crear_controles(titulo, texto_inicial)
        self._timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self._al_tiempo, self._timer)
        self.Bind(wx.EVT_CLOSE, self._al_cerrar)
        self.Bind(wx.EVT_WINDOW_DESTROY, self._al_destruir)
        self._timer.Start(_INTERVALO_ESPERA_MS)

    def _crear_controles(self, titulo, texto_inicial):
        caja = wx.BoxSizer(wx.VERTICAL)
        self.txt_estado = wx.TextCtrl(
            self, style=_PROPIEDADES_TEXTO, name=titulo)
        nombre_accesible(self.txt_estado, titulo)
        self.txt_estado.SetMinSize((-1, 100))
        self.txt_estado.SetValue(texto_inicial)
        caja.Add(self.txt_estado, 1, wx.EXPAND | wx.ALL, 10)
        if self._parada is not None:
            self._btn = self._crear_boton(_("&Cancelar"))
            caja.Add(self._btn, 0, wx.ALIGN_RIGHT | wx.ALL, 10)
        self.SetSizerAndFit(caja)
        self.SetMinSize((480, -1))
        self.Centre()
        self.txt_estado.SetFocus()

    def _crear_boton(self, etiqueta):
        control = wx.Button(self, wx.ID_CANCEL, etiqueta,
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
        frase = _("Cancelando…")
        self.txt_estado.SetValue(frase)
        anunciar(frase)

    def _al_tiempo(self, _evento):
        sound_player.reproducir("espera")

    def terminar(self, texto, error=False):
        self._terminada = True
        self._detener()
        self.txt_estado.SetValue(texto)
        anunciar(texto)
        if error:
            sound_player.reproducir("error")
        self._poner_cerrar()

    def _poner_cerrar(self):
        if self._btn is None:
            self._btn = self._crear_boton(_("&Cerrar"))
            self.GetSizer().Add(self._btn, 0, wx.ALIGN_RIGHT | wx.ALL, 10)
            self.Layout()
            self.Fit()
        else:
            self._btn.SetLabel(_("&Cerrar"))
            nombre_accesible(self._btn, nombre_de_etiqueta(_("&Cerrar")))
            self._btn.Enable()
        self._btn.SetFocus()

    def _detener(self):
        try:
            self._timer.Stop()
        except RuntimeError as error:
            logger.debug("El temporizador de espera ya no existe: %s", error)

    def _al_cerrar(self, evento):
        self._detener()
        evento.Skip()

    def _al_destruir(self, evento):
        self._detener()
        evento.Skip()
