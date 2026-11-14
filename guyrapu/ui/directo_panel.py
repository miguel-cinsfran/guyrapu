# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Botón del directo del panel de transmisión.

Vive aparte de la ventana por composición: recibe el botón y el comando del
directo. Su única razón para cambiar es cómo muestra el estado del directo
en este panel: delega el trabajo en el comando y copia el rótulo que el
comando avisa.
"""

from __future__ import annotations

import wx

from guyrapu.obs import transmision_directa


class DirectoPanel:
    """El botón del directo del panel y el estado que muestra."""

    def __init__(self, ventana, boton, comando, al_cambiar=None):
        self._ventana = ventana
        self._boton = boton
        self._comando = comando
        self._al_cambiar = al_cambiar
        boton.Bind(wx.EVT_BUTTON, self._al_pulsar)
        self._comando.suscribir(self._al_cambiar_estado)
        self._actualizar_boton()

    @property
    def transmitiendo(self) -> bool:
        return self._comando.transmitiendo

    @property
    def deteniendo(self) -> bool:
        return self._comando.deteniendo

    def sincronizar(self, transmitiendo, deteniendo=False) -> None:
        """Ajusta el estado y la etiqueta sin pedir nada a OBS."""
        self._comando.sincronizar(transmitiendo, deteniendo)

    def cerrar(self) -> None:
        self._comando.desuscribir(self._al_cambiar_estado)

    def _actualizar_boton(self) -> None:
        etiqueta, nombre = transmision_directa.etiqueta(
            self.transmitiendo, self.deteniendo)
        self._boton.SetLabel(etiqueta)
        self._boton.SetName(nombre)

    def _al_cambiar_estado(self) -> None:
        self._actualizar_boton()
        if self._al_cambiar is not None:
            self._al_cambiar()

    def _al_pulsar(self, event) -> None:
        self._comando.pulsar(self._ventana)
