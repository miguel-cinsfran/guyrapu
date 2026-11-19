# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Cómo la sonda lee y maneja las listas y los desplegables.

Junta las ramas por clase que la sonda necesita para describir una lista y
para elegir o activar una fila, así `sonda.py` no las repite.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def _es_lista_ctrl_como_listbox(ventana) -> bool:
    """Si el control es la clase que se maneja como una lista."""
    from guyrapu.ui.lista_ctrl import ListaCtrlComoListBox
    return isinstance(ventana, ListaCtrlComoListBox)


def clase_visible(ventana) -> str:
    """La clase que la sonda le muestra al banco.

    La clase nueva se describe como un wx.ListBox: el banco la lee y la
    maneja igual que antes.
    """
    if _es_lista_ctrl_como_listbox(ventana):
        return "ListBox"
    return ventana.__class__.__name__


def describir_filas(ventana, datos) -> None:
    """Agrega a `datos` el contenido de una lista o un desplegable."""
    import wx
    # El contenido de las listas es lo que de verdad lee el usuario, así que
    # sin esto no se puede comprobar que un mensaje llegó al chat. Los
    # desplegables también: «Colecciones» elige la fuente de la Biblioteca.
    if (_es_lista_ctrl_como_listbox(ventana)
            or isinstance(ventana, (wx.ListBox, wx.Choice))):
        try:
            datos["items"] = list(ventana.GetStrings())
            datos["seleccion"] = int(ventana.GetSelection())
        except Exception as exc:
            logger.debug("No se pudo leer el contenido de la lista: %s", exc)
    elif isinstance(ventana, wx.ListCtrl):
        try:
            filas = []
            for f in range(ventana.GetItemCount()):
                cols = []
                for c in range(max(1, ventana.GetColumnCount())):
                    try:    cols.append(ventana.GetItemText(f, c))
                    except Exception: break
                filas.append(cols)
            datos["items"] = filas
        except Exception as exc:
            logger.debug("No se pudieron leer las filas del control: %s", exc)


def es_lista_o_desplegable(ctrl) -> bool:
    """Si «elegir» puede usarlo: una lista, un desplegable o la clase nueva."""
    import wx
    return (_es_lista_ctrl_como_listbox(ctrl)
            or isinstance(ctrl, (wx.ListBox, wx.Choice)))


def es_lista_activable(ctrl) -> bool:
    """Si «activar» puede usarlo: una lista o la clase nueva."""
    import wx
    return _es_lista_ctrl_como_listbox(ctrl) or isinstance(ctrl, wx.ListBox)


def evento_de_elegir(ctrl, indice):
    """El evento que dispara la sonda al elegir una fila."""
    import wx
    if _es_lista_ctrl_como_listbox(ctrl):
        evento = wx.ListEvent(wx.wxEVT_LIST_ITEM_SELECTED, ctrl.GetId())
        evento.SetIndex(indice)
    else:
        tipo = (wx.EVT_LISTBOX.typeId if isinstance(ctrl, wx.ListBox)
                else wx.EVT_CHOICE.typeId)
        evento = wx.CommandEvent(tipo, ctrl.GetId())
        evento.SetInt(indice)
    evento.SetEventObject(ctrl)
    return evento


def evento_de_activar(ctrl):
    """El evento que dispara la sonda al activar la fila elegida."""
    import wx
    como_lista = _es_lista_ctrl_como_listbox(ctrl)
    if como_lista:
        evento = wx.ListEvent(wx.wxEVT_LIST_ITEM_ACTIVATED, ctrl.GetId())
    else:
        evento = wx.CommandEvent(wx.EVT_LISTBOX_DCLICK.typeId, ctrl.GetId())
    evento.SetEventObject(ctrl)
    try:
        indice = int(ctrl.GetSelection())
        if como_lista:
            evento.SetIndex(indice)
        else:
            evento.SetInt(indice)
    except Exception as exc:
        logger.debug("No se pudo poner el índice del evento: %s", exc)
    return evento
