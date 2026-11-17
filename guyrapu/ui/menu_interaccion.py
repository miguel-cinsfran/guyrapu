# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Menú Interacción de la barra principal: los mensajes automáticos."""

import wx

from guyrapu.core.idioma import _
from guyrapu.ui import comando_mensajes_automaticos


def construir(frame, mb):
    m = wx.Menu()
    frame.mi_mensajes_automaticos = m.Append(
        wx.ID_ANY,
        _("&Mensajes automáticos…") + frame._accel("mensajes_automaticos"))
    frame.mi_programados_activo = m.AppendCheckItem(
        wx.ID_ANY, _("Acti&var mensajes automáticos"))
    frame.mi_programados_activo.Check(
        bool(frame._config.get("programados_activo", False)))
    mb.Append(m, _("&Interacción"))
    frame._bind_menu(frame.mi_mensajes_automaticos,
                     comando_mensajes_automaticos.abrir, frame)
    frame._bind_menu(frame.mi_programados_activo,
                     comando_mensajes_automaticos.alternar, frame)
