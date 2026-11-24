# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Página Reproductor del diálogo de Preferencias.

Dueña de sus controles. El diálogo la construye por composición y copia solo
los controles que lee su tabla de opciones simples.
"""

from __future__ import annotations

import wx

from guyrapu.core.idioma import _
from guyrapu.ui.preferencias_comun import crear_panel


# Filas del reproductor de `_OPCIONES_SIMPLES` en `gui_preferencias`: misma
# tabla, mismo orden.
OPCIONES_REPRODUCTOR = (
    ("chk_autoplay", "ui", "autoplay_reproductor", "autoplay_reproductor", bool, True),
    ("chk_solo_audio", "ui", "reproductor_solo_audio", "reproductor_solo_audio", bool, True),
    ("chk_botones_rep", "ui", "mostrar_botones_reproductor",
     "mostrar_botones_reproductor", bool, True),
    ("sp_cache_video", "ui", "cache_video_mb", "cache_video_mb", int, 1024),
)


class PaginaReproductor:
    """Página Reproductor: audio, botones y caché de vídeo."""

    def construir(self, parent):
        p = crear_panel(parent, "PagReproductor")
        vs = wx.BoxSizer(wx.VERTICAL)

        self.chk_autoplay = wx.CheckBox(p, label=_("&Reproducir audio automáticamente al conectar"),
                                         name="AutoplayReproductor")
        vs.Add(self.chk_autoplay, 0, wx.ALL, 10)

        self.chk_solo_audio = wx.CheckBox(
            p, label=_("Reproducir &solo el audio, sin imagen"),
            name="SoloAudioReproductor")
        vs.Add(self.chk_solo_audio, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        self.chk_botones_rep = wx.CheckBox(p, label=_("Mostrar &botones del reproductor"),
                                            name="MostrarBotonesReproductor")
        vs.Add(self.chk_botones_rep, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        etiqueta_cache = wx.StaticText(
            p, label=_("&Tamaño máximo de la caché de vídeo, en megabytes:"))
        self.sp_cache_video = wx.SpinCtrl(
            p, min=0, max=20000,
            name=_("Tamaño máximo de la caché de vídeo en megabytes"))
        vs.Add(etiqueta_cache, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)
        vs.Add(self.sp_cache_video, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        p.SetSizer(vs)
        return p
