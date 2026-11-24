# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Mide en segundo plano la sonoridad y la duración de un medio.

Corre ffmpeg y libVLC en un hilo y entrega el resultado al hilo de la
interfaz. No hace esperar a la ventana ni anuncia nada.
"""

from __future__ import annotations

import threading

import wx

from guyrapu.downloads import ffmpeg_bin
from guyrapu.music import consultas_vlc, sonoridad

PLAZO_DURACION = 1.4


def duracion_de(ruta) -> int:
    """Los segundos del archivo, o 0 si no se pudo leer a tiempo.

    libVLC se mide en un hilo y la interfaz espera menos de un segundo y
    medio: si el motor todavía no está listo, el medio queda con duración
    desconocida en vez de congelar la ventana.
    """
    resultado = {}
    listo = threading.Event()

    def medir():
        try:
            datos = consultas_vlc.leer_etiquetas_vlc(str(ruta), plazo_ms=1200)
            resultado["ms"] = datos.get("duracion_ms") or 0
        finally:
            listo.set()

    threading.Thread(target=medir, daemon=True).start()
    if not listo.wait(PLAZO_DURACION):
        return 0
    return max(0, round(resultado.get("ms", 0) / 1000))


def medir(ruta, al_terminar) -> None:
    """Mide `ruta` en un hilo y entrega la ganancia con `wx.CallAfter`.

    `al_terminar` recibe la ganancia en dB o None si no se pudo medir.
    """
    def trabajo():
        ganancia = sonoridad.medir(ffmpeg_bin.ruta_ffmpeg(), str(ruta))
        wx.CallAfter(al_terminar, ganancia)

    threading.Thread(target=trabajo, daemon=True).start()
