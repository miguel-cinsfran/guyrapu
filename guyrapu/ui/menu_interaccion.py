# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Menú Interacción de la barra principal: la ventana y la casilla de mensajes."""

import wx

from guyrapu.core.idioma import _
from guyrapu.ui import (
    comando_comandos_chat, comando_estilos, comando_interaccion,
    comando_mensajes_automaticos)


def _programados(frame, m):
    frame.mi_programados_activo = m.AppendCheckItem(
        wx.ID_ANY, _("Acti&var mensajes automáticos"))
    frame.mi_programados_activo.Check(
        bool(frame._config.get("programados_activo", False)))
    frame._bind_menu(frame.mi_programados_activo,
                     comando_mensajes_automaticos.alternar, frame)


def _abrir(frame, m):
    frame.mi_interaccion = m.Append(
        wx.ID_ANY,
        _("&Abrir Interacción…") + frame._accel("mensajes_automaticos"))
    frame._bind_menu(frame.mi_interaccion, comando_interaccion.abrir, frame)


def _mensajes(frame, m):
    frame.mi_mensajes_automaticos = m.Append(
        wx.ID_ANY, _("&Mensajes automáticos…"))
    frame._bind_menu(frame.mi_mensajes_automaticos,
                     comando_mensajes_automaticos.abrir, frame)


def _estilos(frame, m):
    frame.mi_estilos_video = m.Append(wx.ID_ANY, _("Es&tilos del vídeo…"))
    frame._bind_menu(frame.mi_estilos_video, comando_estilos.abrir, frame)


def construir(frame, mb):
    m = wx.Menu()
    _abrir(frame, m)
    _mensajes(frame, m)
    comando_comandos_chat.agregar_al_menu(frame, m)
    _estilos(frame, m)
    m.AppendSeparator()
    _programados(frame, m)
    mb.Append(m, _("&Interacción"))
