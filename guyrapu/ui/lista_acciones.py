# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Teclas, menú contextual y caso vacío para una lista con acciones.

La parte pura no abre ventanas: `clave_de_tecla`, `acciones_encendidas` y
`etiqueta_de_menu` se prueban con códigos y acciones. `ListaConVacio` deja
el caso vacío elegido en una `wx.ListBox` y `ListaConAcciones` ata esas
reglas a una lista.
"""

from __future__ import annotations

import dataclasses
import time
from typing import Callable

import wx

from guyrapu.core import sonidos_eventos
from guyrapu.core.idioma import _
from guyrapu.ui.accesibilidad import anunciar, entregar_intro
from guyrapu.ui.busqueda_teclado import instalar_busqueda_tipo
from guyrapu.voice import sound_player as _snd

_TECLAS = {
    wx.WXK_RETURN: "intro",
    wx.WXK_NUMPAD_ENTER: "intro",
    wx.WXK_F2: "f2",
    wx.WXK_DELETE: "suprimir",
    wx.WXK_NUMPAD_DELETE: "suprimir",
}

_TECLAS_CON_CONTROL = {
    ord("D"): "ctrl+d",
    ord("d"): "ctrl+d",
}

_SUFIJOS = {
    "intro": "\tEnter",
    "f2": "\tF2",
    "suprimir": "\tDel",
    "ctrl+d": "\tCtrl+D",
}

# La tecla y el menú contextual pueden llegar los dos en la misma pulsación.
_SEGUNDOS_MENU = 0.5


@dataclasses.dataclass(frozen=True)
class Accion:
    """Una acción de la lista, con la etiqueta del botón y su tecla."""

    clave: str
    etiqueta: str
    manejador: Callable[[], None]
    tecla: str | None = None
    necesita_elemento: bool = True


def _tecla_nombrada(codigo, modificadores) -> str | None:
    """El nombre de la tecla, o None si esa pulsación no es una acción."""
    if codigo in _TECLAS_CON_CONTROL:
        if (modificadores & wx.MOD_CONTROL
                and not modificadores & (wx.MOD_ALT | wx.MOD_SHIFT)):
            return _TECLAS_CON_CONTROL[codigo]
        return None
    return _TECLAS.get(codigo)


def clave_de_tecla(codigo: int, modificadores: int, acciones) -> str | None:
    """La clave de la acción para esa tecla, "menu", o None si no le toca."""
    if (codigo == wx.WXK_WINDOWS_MENU
            or (codigo == wx.WXK_F10 and modificadores & wx.MOD_SHIFT)):
        return "menu"
    tecla = _tecla_nombrada(codigo, modificadores)
    if tecla is None:
        return None
    for accion in acciones:
        if accion.tecla == tecla:
            return accion.clave
    return None


def acciones_encendidas(acciones, hay_elemento: bool) -> dict[str, bool]:
    """Qué acciones van encendidas: las que piden elemento solo con uno."""
    return {accion.clave: hay_elemento or not accion.necesita_elemento
            for accion in acciones}


def etiqueta_de_menu(accion: Accion) -> str:
    """La etiqueta del botón, con su tecla a la vista si la tiene."""
    return accion.etiqueta + _SUFIJOS.get(accion.tecla, "")


class ListaConVacio:
    """Deja el caso vacío elegido en una `wx.ListBox` y da el índice real."""

    def __init__(self, lista, texto_vacio):
        self._lista = lista
        self._texto_vacio = texto_vacio
        self._texto_vacio_inicial = texto_vacio
        self._textos = []
        self._lista.Bind(wx.EVT_KEY_DOWN, self._al_tecla)
        instalar_busqueda_tipo(self._lista, lambda: list(self._textos))

    def _al_tecla(self, evento):
        try:
            seleccion = self._lista.GetSelection()
            total = self._lista.GetCount()
        except Exception:
            seleccion, total = -1, 0
        if sonidos_eventos.es_orilla(evento.GetKeyCode(), seleccion, total):
            _snd.reproducir("orilla")
        evento.Skip()

    def fijar(self, textos, elegido=None, vacio=None):
        """Reemplaza a Clear y Append y deja el caso vacío elegido."""
        self._texto_vacio = (
            self._texto_vacio_inicial if vacio is None else vacio)
        self._textos = list(textos)
        self._lista.Clear()
        if not self._textos:
            self._lista.Append(self._texto_vacio)
            self._lista.SetSelection(0)
        else:
            self._cargar(elegido)

    def _cargar(self, elegido):
        for texto in self._textos:
            self._lista.Append(texto)
        indice = 0 if elegido is None else elegido
        if not 0 <= indice < len(self._textos):
            indice = 0
        self._lista.SetSelection(indice)

    def indice(self):
        """El índice elegido de verdad, o None también con la línea vacía."""
        if not self._textos:
            return None
        seleccion = self._lista.GetSelection()
        if 0 <= seleccion < len(self._textos):
            return seleccion
        return None

    def vacia(self):
        """Si la lista no tiene elementos, solo la línea vacía."""
        return not self._textos

    def sin_elemento(self):
        """Dice por qué no hay nada que usar o que falta elegir."""
        anunciar(self._texto_vacio if self.vacia() else _("Sin selección"))


class ListaConAcciones:
    """Da teclas, menú contextual y caso vacío a una `wx.ListBox`."""

    def __init__(self, lista, acciones, texto_vacio):
        self._lista = lista
        self._acciones = tuple(acciones)
        self._vacio = ListaConVacio(lista, texto_vacio)
        self._ultimo_menu = None
        self._lista.Bind(wx.EVT_KEY_DOWN, self._al_tecla)
        self._lista.Bind(wx.EVT_CONTEXT_MENU, self._al_contexto)
        self._lista.Bind(wx.EVT_LISTBOX_DCLICK, self._al_doble_clic)
        entregar_intro(self._lista, self._al_intro)

    def fijar(self, textos, elegido=None, vacio=None):
        """Reemplaza a Clear y Append y deja el caso vacío elegido."""
        self._vacio.fijar(textos, elegido, vacio)

    def indice(self):
        """El índice elegido de verdad, o None también con la línea vacía."""
        return self._vacio.indice()

    def _accion(self, clave):
        for accion in self._acciones:
            if accion.clave == clave:
                return accion
        return None

    def ejecutar(self, clave) -> bool:
        """Corre la acción si se puede; si no, dice por qué y no la corre."""
        accion = self._accion(clave)
        if accion is None:
            return False
        if accion.necesita_elemento and self.indice() is None:
            self._vacio.sin_elemento()
            return True
        accion.manejador()
        return True

    def _al_tecla(self, evento):
        clave = clave_de_tecla(
            evento.GetKeyCode(), evento.GetModifiers(), self._acciones)
        if clave is None:
            evento.Skip()
            return
        if clave == "menu":
            self._abrir_menu()
            return
        self.ejecutar(clave)

    def _al_intro(self, evento):
        clave = clave_de_tecla(wx.WXK_RETURN, wx.MOD_NONE, self._acciones)
        if clave is None or not self.ejecutar(clave):
            evento.Skip()

    def _al_doble_clic(self, _evento):
        clave = clave_de_tecla(wx.WXK_RETURN, wx.MOD_NONE, self._acciones)
        if clave is not None:
            self.ejecutar(clave)

    def _al_contexto(self, _evento):
        self._abrir_menu()

    def _abrir_menu(self):
        ahora = time.monotonic()
        if (self._ultimo_menu is not None
                and ahora - self._ultimo_menu < _SEGUNDOS_MENU):
            return
        self._ultimo_menu = ahora
        menu = self._construir_menu()
        try:
            self._lista.PopupMenu(menu)
        finally:
            menu.Destroy()

    def _construir_menu(self):
        menu = wx.Menu()
        estados = acciones_encendidas(self._acciones, self.indice() is not None)
        for accion in self._acciones:
            identificador = wx.NewIdRef()
            item = menu.Append(identificador, etiqueta_de_menu(accion))
            item.Enable(estados[accion.clave])
            menu.Bind(
                wx.EVT_MENU,
                lambda _evento, clave=accion.clave: self.ejecutar(clave),
                id=identificador)
        return menu
