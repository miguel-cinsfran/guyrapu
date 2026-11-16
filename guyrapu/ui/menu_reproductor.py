# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Menú Reproductor de la barra principal.

Qué ofrece el menú Reproductor y cómo se enlazan sus comandos.
"""

import wx

from guyrapu.core.idioma import _, N_

CALIDADES = (
    (N_("Automática"), None),
    (N_("1080p"), 1080),
    (N_("720p"), 720),
    (N_("480p"), 480),
    (N_("360p"), 360),
    (N_("240p"), 240),
    (N_("144p"), 144),
)


def construir(frame, mb):
    m = wx.Menu()
    mi_rep_play  = m.Append(wx.ID_ANY, _("&Reproducir o pausar") + frame._accel("rep_play"))
    mi_rep_retro = m.Append(wx.ID_ANY, _("R&etroceder 1 minuto") + frame._accel("rep_retro"))
    mi_rep_avanz = m.Append(wx.ID_ANY, _("&Avanzar 1 minuto") + frame._accel("rep_avanz"))
    mi_rep_directo = m.Append(wx.ID_ANY, _("&Ir al directo") + frame._accel("rep_directo"))
    mi_rep_stop  = m.Append(wx.ID_ANY, _("De&tener reproducción") + frame._accel("rep_detener"))
    mi_rep_mute  = m.Append(wx.ID_ANY, _("&Silenciar o activar audio") + frame._accel("rep_mute"))
    mi_rep_fs    = m.Append(wx.ID_ANY, _("Pantalla &completa") + frame._accel("pantalla_completa"))
    # Submenú de calidad (radio). Se elige la disponible más cercana.
    sub_cal = wx.Menu()
    for etiqueta, altura in CALIDADES:
        it = sub_cal.AppendRadioItem(wx.ID_ANY, _(etiqueta))
        frame._bind_menu(it, frame._rep_accion, "set_calidad", altura)
    m.AppendSubMenu(sub_cal, _("Ca&lidad del vídeo"))
    m.AppendSeparator()
    # Descargar este vídeo (solo YouTube, no live). Se habilita en
    # `_actualizar_menus_por_conexion` cuando hay URL reproducible.
    frame.mi_descargar_este = m.Append(
        wx.ID_ANY, _("Descargar este &vídeo…"))
    m.AppendSeparator()
    mi_rep_volm  = m.Append(wx.ID_ANY, _("&Bajar volumen del reproductor") + frame._accel("rep_vol_menos"))
    mi_rep_volM  = m.Append(wx.ID_ANY, _("S&ubir volumen del reproductor") + frame._accel("rep_vol_mas"))
    m.AppendSeparator()
    frame.mi_rep_botones = m.AppendCheckItem(wx.ID_ANY, _("Mostrar botones en &pantalla"))
    frame.mi_rep_botones.Check(bool(frame._config.get("mostrar_botones_reproductor", True)))
    frame._bind_menu(frame.mi_rep_botones, frame._toggle_botones_rep)
    mb.Append(m, _("&Reproductor"))
    frame._bind_menu(mi_rep_play, frame._rep_accion, "_toggle_play")
    frame._bind_menu(mi_rep_retro, frame._rep_accion, "_buscar_rel", -60_000)
    frame._bind_menu(mi_rep_avanz, frame._rep_accion, "_buscar_rel", +60_000)
    frame._bind_menu(mi_rep_directo, frame._rep_accion, "ir_al_directo")
    frame._bind_menu(mi_rep_stop, frame._rep_accion, "_detener")
    frame._bind_menu(mi_rep_mute, frame._rep_accion, "_toggle_mute")
    frame._bind_menu(mi_rep_fs, frame._rep_accion, "alternar_pantalla_completa")
    frame.Bind(wx.EVT_MENU, lambda e: wx.CallAfter(
        frame._abrir_descargas,
        url=frame._rep_panel.get_url_para_descarga() if frame._rep_panel else None),
        frame.mi_descargar_este)
    frame._bind_menu(mi_rep_volm, frame._rep_accion, "ajustar_volumen", -20)
    frame._bind_menu(mi_rep_volM, frame._rep_accion, "ajustar_volumen", +20)
