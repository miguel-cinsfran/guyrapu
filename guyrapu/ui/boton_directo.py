# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Botón directo de transmisión en la ventana principal, con wx.

Crea el botón en el panel que le pasan y concentra la lógica de wx
(visibilidad, etiqueta, nombre accesible, foco y repintado). El trabajo
de fondo (pedir destino, preparar OBS, confirmar, supervisar, finalizar)
lo hace `ComandoDirecto`, que recibe el marco: este solo crea el botón,
lo mete en la fila y le pide `actualizar`.
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
        self._comando.usar_boton(self.boton)

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
            if self._transmitiendo or self._deteniendo:
                comando.SetItemLabel(etiqueta)
            else:
                comando.SetItemLabel(etiqueta + "…")
            comando.Enable(visible)
        self.boton.GetParent().Layout()

    def _al_pulsar(self, event):
        self.pulsar()

    def pulsar(self):
        """Hace lo mismo que pulsar el botón, desde él o desde el menú."""
        self._comando.pulsar(self._marco)
