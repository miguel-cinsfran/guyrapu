# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Cómo se arma el menú contextual de una lista con acciones."""

from __future__ import annotations

import wx

from guyrapu.capture import redaccion
from guyrapu.ui.menu_habilitado import habilitar

_SUFIJOS = {
    "intro": "\tEnter",
    "mayus+intro": "\tShift+Enter",
    "ctrl+intro": "\tCtrl+Enter",
    "alt+flecha_arriba": "\tAlt+Up",
    "alt+flecha_abajo": "\tAlt+Down",
    "f2": "\tF2",
    "suprimir": "\tDel",
    "ctrl+c": "\tCtrl+C",
    "ctrl+d": "\tCtrl+D",
}


def etiqueta_de_menu(accion) -> str:
    """La etiqueta del botón, con su tecla a la vista si la tiene."""
    etiqueta = accion.etiqueta
    if accion.motivo is not None:
        etiqueta = redaccion.etiqueta_con_motivo(etiqueta, accion.motivo())
    return etiqueta + _SUFIJOS.get(accion.tecla, "")


def construir_menu(acciones, estados, ejecutar):
    """El menú contextual de la lista, con sus etiquetas y estados."""
    menu = wx.Menu()
    for accion in acciones:
        identificador = wx.NewIdRef()
        item = menu.Append(identificador, etiqueta_de_menu(accion))
        habilitar(item, estados[accion.clave])
        menu.Bind(
            wx.EVT_MENU,
            lambda _evento, clave=accion.clave: ejecutar(clave),
            id=identificador)
    return menu
