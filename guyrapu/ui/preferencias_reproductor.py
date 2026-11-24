# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Página Reproductor del diálogo de Preferencias.

Dueña de sus controles. El diálogo la construye por composición y copia solo
los controles que lee su tabla de opciones simples.
"""

from __future__ import annotations

import wx

from guyrapu.core.idioma import _
from guyrapu.ui import formulario
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
        formulario.agregar_fila(vs, None, self.chk_autoplay, expandir=False)

        self.chk_solo_audio = wx.CheckBox(
            p, label=_("Reproducir &solo el audio, sin imagen"),
            name="SoloAudioReproductor")
        formulario.agregar_fila(vs, None, self.chk_solo_audio, expandir=False)

        self.chk_botones_rep = wx.CheckBox(p, label=_("Mostrar &botones del reproductor"),
                                            name="MostrarBotonesReproductor")
        formulario.agregar_fila(vs, None, self.chk_botones_rep, expandir=False)

        etiqueta_cache = wx.StaticText(
            p, label=_("&Tamaño máximo de la caché de vídeo, en megabytes:"))
        self.sp_cache_video = wx.SpinCtrl(
            p, min=0, max=20000,
            name=_("Tamaño máximo de la caché de vídeo en megabytes"))
        formulario.agregar_fila(vs, etiqueta_cache, self.sp_cache_video,
                                numerico=True)

        formulario.armar_pagina(p, vs)
        return p
