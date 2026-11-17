# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Abrir la ventana de comandos del chat desde el menú Interacción.

Un solo camino por acción, como pide la skill de interfaz accesible: el menú
llama acá y acá se abre la ventana.
"""

from __future__ import annotations

import wx

from guyrapu.core.idioma import _
from guyrapu.ui import comandos_ventana


def abrir(frame):
    """Abre la ventana de comandos del chat."""
    comandos_ventana.abrir(frame)


def agregar_al_menu(frame, menu):
    """Suma el comando al menú Interacción y lo enlaza."""
    frame.mi_comandos_chat = menu.Append(wx.ID_ANY, _("&Comandos del chat…"))
    frame._bind_menu(frame.mi_comandos_chat, abrir, frame)
