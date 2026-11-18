# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Menú Interacción de la barra principal: la ventana y lo que sale en el vídeo."""

import wx

from guyrapu.core.idioma import _
from guyrapu.ui import (
    comando_comandos_chat, comando_en_directo, comando_estilos,
    comando_interaccion, comando_mensajes_automaticos, interaccion_atajos)


def _programados(frame, m):
    frame.mi_programados_activo = m.AppendCheckItem(
        wx.ID_ANY, _("Acti&var mensajes automáticos")
        + frame._accel("mensajes_automaticos_alternar"))
    frame.mi_programados_activo.Check(
        bool(frame._config.get("programados_activo", False)))
    frame._bind_menu(frame.mi_programados_activo,
                     comando_en_directo.alternar_mensajes, frame)


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


def _en_directo_cola(frame, m):
    frame.mi_video_pausar = m.AppendCheckItem(
        wx.ID_ANY,
        _("&Pausar cola del vídeo") + frame._accel("video_pausar"))
    frame._bind_menu(frame.mi_video_pausar,
                     comando_en_directo.alternar_pausa, frame)
    frame.mi_video_omitir = m.Append(
        wx.ID_ANY,
        _("Omitir m&ensaje del vídeo") + frame._accel("video_saltar"))
    frame._bind_menu(frame.mi_video_omitir, comando_en_directo.saltar, frame)
    frame.mi_video_vaciar = m.Append(
        wx.ID_ANY,
        _("Vaciar co&la del vídeo") + frame._accel("video_vaciar"))
    frame._bind_menu(frame.mi_video_vaciar, comando_en_directo.vaciar, frame)


def _en_directo_medios(frame, m):
    frame.mi_video_silenciar = m.AppendCheckItem(
        wx.ID_ANY,
        _("Silencia&r medios") + frame._accel("video_silenciar"))
    frame._bind_menu(frame.mi_video_silenciar,
                     comando_en_directo.alternar_silencio, frame)
    frame.mi_video_panico = m.AppendCheckItem(
        wx.ID_ANY,
        _("Modo pánic&o") + frame._accel("video_panico"))
    frame._bind_menu(frame.mi_video_panico,
                     comando_en_directo.alternar_panico, frame)


def _encuesta(frame, m):
    frame.mi_encuesta_cerrar = m.Append(
        wx.ID_ANY,
        _("Cerrar e&ncuesta") + frame._accel("encuesta_cerrar"))
    frame._bind_menu(frame.mi_encuesta_cerrar,
                     comando_en_directo.cerrar_encuesta, frame)


def _en_directo(frame, m):
    _en_directo_cola(frame, m)
    _en_directo_medios(frame, m)
    _encuesta(frame, m)
    _programados(frame, m)


def construir(frame, mb):
    m = wx.Menu()
    _abrir(frame, m)
    _mensajes(frame, m)
    comando_comandos_chat.agregar_al_menu(frame, m)
    _estilos(frame, m)
    m.AppendSeparator()
    _en_directo(frame, m)
    mb.Append(m, _("&Interacción"))
    if getattr(frame, "_interaccion_atajos", None) is None:
        frame._interaccion_atajos = interaccion_atajos.InteraccionAtajos(frame)
