# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Traduce a un `wx.ListCtrl` de informe lo que la pieza de listas pide.

La pieza común y la búsqueda al teclear hablan de `GetSelection`,
`SetSelection`, `Append` y `PopupMenu`, que son de `wx.ListBox`. Esta clase
envuelve un `wx.ListCtrl` y da esas operaciones con la misma conducta. No
anuncia, no suena y no sabe de acciones.
"""

from __future__ import annotations


class ListaCtrlEnvuelta:
    """Las operaciones de `wx.ListBox` sobre un `wx.ListCtrl` de informe."""

    def __init__(self, control):
        self._control = control

    def GetSelection(self):
        return self._control.GetFirstSelected()

    def SetSelection(self, indice):
        # Con solo `Select` el foco del lector queda en otra fila.
        self._control.Select(indice)
        self._control.Focus(indice)
        self._control.EnsureVisible(indice)

    def GetCount(self):
        return self._control.GetItemCount()

    def Clear(self):
        self._control.DeleteAllItems()

    def Append(self, fila):
        celdas = (fila,) if isinstance(fila, str) else fila
        indice = self._control.InsertItem(
            self._control.GetItemCount(), celdas[0])
        for columna, texto in enumerate(celdas[1:], start=1):
            self._control.SetItem(indice, columna, texto)

    def Insert(self, fila, indice):
        celdas = (fila,) if isinstance(fila, str) else fila
        self._control.InsertItem(indice, celdas[0])
        for columna, texto in enumerate(celdas[1:], start=1):
            self._control.SetItem(indice, columna, texto)

    def Delete(self, indice):
        self._control.DeleteItem(indice)

    def GetString(self, indice):
        return tuple(self._control.GetItemText(indice, columna)
                     for columna in range(self._control.GetColumnCount()))

    def SetString(self, indice, fila):
        celdas = (fila,) if isinstance(fila, str) else fila
        for columna, texto in enumerate(celdas):
            if self._control.GetItemText(indice, columna) != texto:
                self._control.SetItem(indice, columna, texto)

    def Bind(self, evento, manejador):
        self._control.Bind(evento, manejador)

    def PopupMenu(self, menu):
        self._control.PopupMenu(menu)
