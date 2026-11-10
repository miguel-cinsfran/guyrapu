# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Cómo se reconoce y se atiende Escape en la interfaz."""

from __future__ import annotations

import wx


def es_escape(codigo) -> bool:
    """Dice si un código de tecla es Escape."""
    return codigo == wx.WXK_ESCAPE


def cancelar_si_escape(dialogo, evento) -> None:
    """Cierra el diálogo con Cancelar ante Escape y deja pasar lo demás."""
    if es_escape(evento.GetKeyCode()):
        dialogo.EndModal(wx.ID_CANCEL)
        return
    evento.Skip()
