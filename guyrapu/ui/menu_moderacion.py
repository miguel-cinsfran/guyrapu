# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Ítems de moderación del menú contextual de una fila del chat.

Única razón para cambiar: qué ofrece el menú de moderación de una fila.
"""

import wx

from guyrapu.core import plataformas
from guyrapu.core.idioma import _
from guyrapu.youtube import credenciales
from guyrapu.youtube import youtube_api


def agregar(menu, frame, registro, autor_mostrado, varios: bool = False) -> None:
    """Agrega al menú lo que se puede moderar de la fila seleccionada."""
    id_ban = wx.NewIdRef()
    id_timeout = wx.NewIdRef()
    autor = registro.autor if registro else ""
    plataforma = plataformas.obtener(registro.plataforma if registro else "")
    identificador = registro.identificador if registro else ""
    moderable = bool(autor and plataforma and plataforma.moderable
                     and identificador and frame.sesion.live_chat_id
                     and youtube_api.google_disponible() and credenciales.hay_sesion())
    if moderable:
        menu.AppendSeparator()
        if varios:
            texto = _("Suspender temporalmente a {autor} en {plataforma} (5 minutos)")
        else:
            texto = _("Suspender temporalmente a {autor} (5 minutos)")
        menu.Append(id_timeout, texto.format(
            autor=autor_mostrado, plataforma=plataforma.nombre))
        menu.Append(id_ban, _("Ocultar a {autor} en el canal de {plataforma}").format(
            autor=autor_mostrado, plataforma=plataforma.nombre))
        menu.Bind(wx.EVT_MENU, lambda e: frame._moderar(autor, identificador, 300), id=id_timeout)
        menu.Bind(wx.EVT_MENU, lambda e: frame._moderar(autor, identificador, None), id=id_ban)
    elif autor and plataforma and not plataforma.moderable:
        menu.AppendSeparator()
        menu.Append(id_ban, _("{plataforma} no permite moderar desde Guyrapu").format(
            plataforma=plataforma.nombre))
        menu.Enable(id_ban, False)
