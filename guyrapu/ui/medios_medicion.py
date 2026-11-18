# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Mide en segundo plano la sonoridad de un medio de la biblioteca.

Corre ffmpeg en un hilo y entrega la ganancia al hilo de la interfaz. No
hace esperar a la ventana ni anuncia nada.
"""

from __future__ import annotations

import threading

import wx

from guyrapu.downloads import ffmpeg_bin
from guyrapu.music import sonoridad


def medir(ruta, al_terminar) -> None:
    """Mide `ruta` en un hilo y entrega la ganancia con `wx.CallAfter`.

    `al_terminar` recibe la ganancia en dB o None si no se pudo medir.
    """
    def trabajo():
        ganancia = sonoridad.medir(ffmpeg_bin.ruta_ffmpeg(), str(ruta))
        wx.CallAfter(al_terminar, ganancia)

    threading.Thread(target=trabajo, daemon=True).start()
