# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Cómo se conectan los chats de un directo por Restream.

El chat principal es el de YouTube y se conecta en el hilo de la interfaz.
"""

from __future__ import annotations

from guyrapu.core import diagnostico
from guyrapu.core.idioma import _

logger = diagnostico.obtener_logger(__name__)


def conectar_chat(frame, youtube=False, guardados=None):
    def al_conectar_chat(url):
        from guyrapu.ui import gui as _gui

        def _conectar():
            if not getattr(frame, "_alive", True):
                return
            if youtube:
                from guyrapu.ui import inicio_youtube
                if inicio_youtube.sin_chat(frame, guardados or {}, url):
                    return
            if frame._conectado or frame._conectando:
                _gui.anunciar(
                    _("El chat ya estaba conectado y no se cambió."))
                return
            try:
                frame.txt_url.SetValue(url)
            except Exception as error:
                logger.debug("no se pudo mostrar la dirección: %s", error)
            frame.sesion.conexion_propia = True
            frame._on_conectar(None)
        _gui.wx.CallAfter(_conectar)
    return al_conectar_chat
