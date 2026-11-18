# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Cómo se arma el menú contextual de una lista con acciones.

Una acción con `opciones` sale como submenú, armado cada vez que se abre el
menú. `mostrar_opciones` arma el menú de un nivel que se abre al ejecutar
una de esas acciones.
"""

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


def _etiqueta(accion, motivo) -> str:
    if motivo:
        base = redaccion.etiqueta_con_motivo(accion.etiqueta, motivo)
    else:
        base = accion.etiqueta
    return base + _SUFIJOS.get(accion.tecla, "")


def etiqueta_de_menu(accion) -> str:
    """La etiqueta del botón, con su tecla a la vista si la tiene."""
    motivo = accion.motivo() if accion.motivo is not None else ""
    return _etiqueta(accion, motivo)


def _agregar_opciones(menu, opciones) -> None:
    """Agrega al menú las opciones que la acción arma en este momento."""
    for etiqueta, funcion in opciones():
        identificador = wx.NewIdRef()
        menu.Append(identificador, etiqueta)
        menu.Bind(
            wx.EVT_MENU,
            lambda _evento, funcion=funcion: funcion(),
            id=identificador)


def _agregar_item(menu, accion, activo, ejecutar, etiqueta) -> None:
    identificador = wx.NewIdRef()
    item = menu.Append(identificador, etiqueta)
    habilitar(item, activo)
    menu.Bind(
        wx.EVT_MENU,
        lambda _evento, clave=accion.clave: ejecutar(clave),
        id=identificador)


def _agregar_accion(menu, accion, activo, ejecutar, motivo_extra="") -> None:
    motivo = motivo_extra or (
        accion.motivo() if accion.motivo is not None else "")
    etiqueta = _etiqueta(accion, motivo)
    if accion.opciones is not None and activo and not motivo:
        submenu = wx.Menu()
        menu.AppendSubMenu(submenu, etiqueta)
        _agregar_opciones(submenu, accion.opciones)
        return
    _agregar_item(menu, accion, activo, ejecutar, etiqueta)


def construir_menu(acciones, estados, ejecutar, motivos=None):
    """El menú contextual de la lista, con sus submenús, estados y motivos."""
    motivos = motivos or {}
    menu = wx.Menu()
    for accion in acciones:
        _agregar_accion(
            menu, accion, estados[accion.clave], ejecutar,
            motivos.get(accion.clave, ""))
    return menu


def mostrar_opciones(lista, opciones) -> None:
    """Muestra sobre la lista el menú de un nivel con esas opciones."""
    menu = wx.Menu()
    try:
        _agregar_opciones(menu, opciones)
        lista.PopupMenu(menu)
    finally:
        menu.Destroy()
