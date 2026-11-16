# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Sonido de una espera que pidió el usuario.

Su única razón para cambiar es cómo suena una espera pedida: «espera» cada
dos segundos mientras dura, «listo» al terminar bien si llegó a sonar y
«error» al fallar. El primer «espera» sale a los dos segundos, no al
empezar: una espera corta no hace ruido. Se detiene sola al destruirse la
ventana.
"""

from __future__ import annotations

import wx

from guyrapu.voice import sound_player

_INTERVALO_ESPERA_MS = 2000


class EsperaSonora:
    """La espera de una ventana, con un temporizador que vive en ella."""

    def __init__(self, ventana):
        self._sono = False
        self._mudo = False
        self._timer = wx.Timer(ventana)
        ventana.Bind(wx.EVT_TIMER, self._al_tiempo, self._timer)
        ventana.Bind(wx.EVT_WINDOW_DESTROY, self._al_destruir)

    def empezar(self) -> None:
        self._sono = False
        self._mudo = False
        self._timer.Start(_INTERVALO_ESPERA_MS)

    def terminar(self, sonido) -> None:
        if self._mudo:
            return
        self._timer.Stop()
        if sonido == "error":
            sound_player.reproducir("error")
        elif sonido == "listo" and self._sono:
            sound_player.reproducir("listo")

    def detener(self) -> None:
        self._timer.Stop()
        self._sono = False
        self._mudo = True

    def _al_tiempo(self, _evento) -> None:
        self._sono = True
        sound_player.reproducir("espera")

    def _al_destruir(self, evento) -> None:
        self.detener()
        evento.Skip()
