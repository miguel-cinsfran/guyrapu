# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Traduce a un `wx.ListCtrl` de informe lo que la pieza de listas pide.

La pieza común y la búsqueda al teclear hablan de `GetSelection`,
`SetSelection`, `Append` y `PopupMenu`, que son de `wx.ListBox`.
`ListaCtrlEnvuelta` envuelve un `wx.ListCtrl` y da esas operaciones con la
misma conducta, y `ListaCtrlComoListBox` es un control de una columna que las
tiene de fábrica. No anuncian, no suenan y no saben de acciones.
"""

from __future__ import annotations

import wx


class ListaCtrlEnvuelta:
    """Las operaciones de `wx.ListBox` sobre un `wx.ListCtrl` de informe."""

    def __init__(self, control, crudo=False):
        self._control = control
        self._crudo = crudo

    def _propio(self, nombre):
        """El método del control cuando ya trae la conducta de lista."""
        if self._crudo or not isinstance(self._control, ListaCtrlComoListBox):
            return None
        return getattr(self._control, nombre)

    def GetSelection(self):
        propio = self._propio("GetSelection")
        if propio is not None:
            return propio()
        return self._control.GetFirstSelected()

    def GetSelections(self):
        propio = self._propio("GetSelections")
        if propio is not None:
            return propio()
        elegidos = [self._control.GetFirstSelected()]
        while elegidos[-1] != -1:
            elegidos.append(self._control.GetNextSelected(elegidos[-1]))
        return elegidos[:-1]

    def SetSelection(self, indice):
        propio = self._propio("SetSelection")
        if propio is not None:
            return propio(indice)
        # Con solo `Select` el foco del lector queda en otra fila.
        self._control.Select(indice)
        self._control.Focus(indice)
        self._control.EnsureVisible(indice)

    def GetCount(self):
        propio = self._propio("GetCount")
        if propio is not None:
            return propio()
        return self._control.GetItemCount()

    def Clear(self):
        propio = self._propio("Clear")
        if propio is not None:
            return propio()
        self._control.DeleteAllItems()

    def Append(self, fila):
        propio = self._propio("Append")
        if propio is not None:
            return propio(fila)
        celdas = (fila,) if isinstance(fila, str) else fila
        indice = self._control.InsertItem(
            self._control.GetItemCount(), celdas[0])
        for columna, texto in enumerate(celdas[1:], start=1):
            self._control.SetItem(indice, columna, texto)

    def Insert(self, fila, indice):
        propio = self._propio("Insert")
        if propio is not None:
            return propio(fila, indice)
        celdas = (fila,) if isinstance(fila, str) else fila
        self._control.InsertItem(indice, celdas[0])
        for columna, texto in enumerate(celdas[1:], start=1):
            self._control.SetItem(indice, columna, texto)

    def Delete(self, indice):
        propio = self._propio("Delete")
        if propio is not None:
            return propio(indice)
        self._control.DeleteItem(indice)

    def GetString(self, indice):
        propio = self._propio("GetString")
        if propio is not None:
            return propio(indice)
        return tuple(self._control.GetItemText(indice, columna)
                     for columna in range(self._control.GetColumnCount()))

    def SetString(self, indice, fila):
        propio = self._propio("SetString")
        if propio is not None:
            return propio(indice, fila)
        celdas = (fila,) if isinstance(fila, str) else fila
        for columna, texto in enumerate(celdas):
            if self._control.GetItemText(indice, columna) != texto:
                self._control.SetItem(indice, columna, texto)

    def Bind(self, evento, manejador):
        self._control.Bind(evento, manejador)

    def PopupMenu(self, menu):
        self._control.PopupMenu(menu)


class ListaCtrlComoListBox(wx.ListCtrl):
    """Un `wx.ListCtrl` de informe de una columna que se maneja como una lista.

    Recibe si deja elegir varias filas y de fábrica deja una sola. La columna
    ocupa siempre el ancho del control.
    """

    def __init__(self, parent, varias=False, **kwargs):
        estilo = wx.LC_REPORT | wx.LC_NO_HEADER
        if not varias:
            estilo |= wx.LC_SINGLE_SEL
        super().__init__(parent, style=estilo, **kwargs)
        self._envuelta = ListaCtrlEnvuelta(self, crudo=True)
        self.InsertColumn(0, "")
        self.Bind(wx.EVT_SIZE, self._al_cambiar_tamano)
        self._ajustar_columna()

    def _al_cambiar_tamano(self, evento):
        evento.Skip()
        self._ajustar_columna()

    def _ajustar_columna(self):
        self.SetColumnWidth(0, self.GetClientSize().width)

    def GetString(self, indice):
        return self._envuelta.GetString(indice)[0]

    def GetStrings(self):
        return [self.GetString(indice) for indice in range(self.GetCount())]

    def GetCount(self):
        return self._envuelta.GetCount()

    def Append(self, texto):
        self._envuelta.Append(texto)

    def Insert(self, texto, indice):
        self._envuelta.Insert(texto, indice)

    def Delete(self, indice):
        self._envuelta.Delete(indice)

    def Clear(self):
        self._envuelta.Clear()

    def Set(self, textos):
        self.Clear()
        for texto in textos:
            self.Append(texto)

    def SetString(self, indice, texto):
        self._envuelta.SetString(indice, texto)

    def GetSelection(self):
        return self._envuelta.GetSelection()

    def GetSelections(self):
        return self._envuelta.GetSelections()

    def SetSelection(self, indice):
        # Quien llama quiere ir a una fila, así que en varias también quita
        # la elección de las demás en vez de sumarla.
        for elegido in self.GetSelections():
            self.Select(elegido, False)
        if indice >= 0:
            self._envuelta.SetSelection(indice)
