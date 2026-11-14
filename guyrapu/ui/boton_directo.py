# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Botón directo de transmisión en la ventana principal, con wx.

Crea el botón en el panel que le pasan y concentra la lógica de wx
(visibilidad, etiqueta, nombre accesible, foco y repintado). El trabajo
de fondo lo hace `ComandoDirecto`, que recibe el marco: este crea el
botón, lo mete en la fila, le pide `actualizar` y muestra el estado que
el comando le avisa.
"""

from __future__ import annotations

import wx

from guyrapu.obs import transmision_directa
from guyrapu.ui.tema import _T, _pintar


class BotonDirecto:
    """Botón «Transmitir en directo» / «Finalizar directo»."""

    def __init__(self, panel, btn_conectar, marco, comando):
        etiqueta, nombre = transmision_directa.etiqueta(False)
        self._marco = marco
        self._conectar = btn_conectar
        self._comando = comando
        marco._comando_directo = comando
        self.boton = wx.Button(panel, label=etiqueta, name=nombre)
        _pintar(self.boton, _T.btn, _T.btn_t)
        self.boton.SetFont(self.boton.GetFont().Bold())
        self.boton.Bind(wx.EVT_BUTTON, self._al_pulsar)
        self._comando.suscribir(self._al_cambiar_estado)

    def actualizar(self, conectado, conectando, propio, transmitiendo,
                   deteniendo=False):
        """Aplica visibilidad, etiqueta y nombre; repinta la fila.

        Oculto sale del orden de Tab; si tenía el foco, este vuelve a
        Conectar para no quedar en un control invisible. Mientras se
        detiene sigue visible y habilitado, solo cambia lo que dice.
        """
        self._comando.sincronizar(transmitiendo, deteniendo)
        etiqueta, nombre = transmision_directa.etiqueta(transmitiendo,
                                                         deteniendo)
        self.boton.SetLabel(etiqueta)
        self.boton.SetName(nombre)
        visible = transmision_directa.boton_visible(
            conectado, conectando, propio, transmitiendo)
        if visible:
            self.boton.Show()
        else:
            if self.boton.HasFocus():
                self._conectar.SetFocus()
            self.boton.Hide()
        comando = getattr(self._marco, "mi_directo", None)
        if comando is not None:
            comando.SetItemLabel(self._etiqueta_del_menu(
                etiqueta, transmitiendo, deteniendo))
            comando.Enable(visible)
        self.boton.GetParent().Layout()

    @staticmethod
    def _etiqueta_del_menu(etiqueta, transmitiendo, deteniendo):
        if transmitiendo or deteniendo:
            return etiqueta
        return etiqueta + "…"

    def _al_cambiar_estado(self):
        etiqueta, nombre = transmision_directa.etiqueta(
            self._comando.transmitiendo, self._comando.deteniendo)
        self.boton.SetLabel(etiqueta)
        self.boton.SetName(nombre)
        item = getattr(self._marco, "mi_directo", None)
        if item is not None:
            item.SetItemLabel(self._etiqueta_del_menu(
                etiqueta, self._comando.transmitiendo,
                self._comando.deteniendo))

    def _al_pulsar(self, event):
        self.pulsar()

    def pulsar(self):
        """Hace lo mismo que pulsar el botón, desde él o desde el menú."""
        self._comando.pulsar(self._marco)
