# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Teclas, menú contextual y caso vacío para una lista con acciones.

La parte pura no abre ventanas: `clave_de_tecla`, `acciones_encendidas` y
`etiqueta_de_menu` se prueban con códigos y acciones. `ListaConVacio` deja
el caso vacío elegido en una lista y `ListaConAcciones` ata esas reglas a
una lista.
"""

from __future__ import annotations

import dataclasses
import time
from typing import Callable

import wx

from guyrapu.capture import redaccion
from guyrapu.core import pasos_lista
from guyrapu.core import sonidos_eventos
from guyrapu.core.idioma import _
from guyrapu.ui.accesibilidad import anunciar, entregar_intro
from guyrapu.ui.busqueda_teclado import instalar_busqueda_tipo
from guyrapu.ui.lista_ctrl import ListaCtrlEnvuelta
from guyrapu.ui.menu_habilitado import habilitar
from guyrapu.voice import sound_player as _snd

_TECLAS = {
    (wx.WXK_RETURN, wx.MOD_NONE): "intro",
    (wx.WXK_NUMPAD_ENTER, wx.MOD_NONE): "intro",
    (wx.WXK_RETURN, wx.MOD_SHIFT): "mayus+intro",
    (wx.WXK_NUMPAD_ENTER, wx.MOD_SHIFT): "mayus+intro",
    (wx.WXK_RETURN, wx.MOD_CONTROL): "ctrl+intro",
    (wx.WXK_NUMPAD_ENTER, wx.MOD_CONTROL): "ctrl+intro",
    (wx.WXK_UP, wx.MOD_ALT): "alt+flecha_arriba",
    (wx.WXK_DOWN, wx.MOD_ALT): "alt+flecha_abajo",
}

# F2 y Suprimir responden con cualquier modificador, como antes.
_TECLAS_CON_CUALQUIER_MODIFICADOR = {
    wx.WXK_F2: "f2",
    wx.WXK_DELETE: "suprimir",
    wx.WXK_NUMPAD_DELETE: "suprimir",
}

_TECLAS_CON_CONTROL = {
    ord("C"): "ctrl+c",
    ord("c"): "ctrl+c",
    ord("D"): "ctrl+d",
    ord("d"): "ctrl+d",
}

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
    motivo: Callable[[], str] | None = None


def _tecla_nombrada(codigo, modificadores) -> str | None:
    """El nombre de la tecla, o None si esa pulsación no es una acción."""
    if codigo in _TECLAS_CON_CONTROL:
        if (modificadores & wx.MOD_CONTROL
                and not modificadores & (wx.MOD_ALT | wx.MOD_SHIFT)):
            return _TECLAS_CON_CONTROL[codigo]
        return None
    nombre = _TECLAS.get((codigo, modificadores))
    if nombre is not None:
        return nombre
    return _TECLAS_CON_CUALQUIER_MODIFICADOR.get(codigo)


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
    etiqueta = accion.etiqueta
    if accion.motivo is not None:
        etiqueta = redaccion.etiqueta_con_motivo(etiqueta, accion.motivo())
    return etiqueta + _SUFIJOS.get(accion.tecla, "")


def _envuelta(lista):
    """El control con la conducta de `wx.ListBox` si es un `wx.ListCtrl`."""
    if isinstance(lista, wx.ListCtrl):
        return ListaCtrlEnvuelta(lista)
    return lista


def _texto_de(fila):
    """El texto que se busca y se anuncia: el de la primera columna."""
    return fila[0] if isinstance(fila, tuple) else fila


class ListaConVacio:
    """Deja el caso vacío elegido en una lista y da el índice real."""

    def __init__(self, lista, texto_vacio):
        self._lista = _envuelta(lista)
        self._texto_vacio = texto_vacio
        self._texto_vacio_inicial = texto_vacio
        self._textos = []
        self._claves = []
        self._lista.Bind(wx.EVT_KEY_DOWN, self._al_tecla)
        instalar_busqueda_tipo(
            self._lista, lambda: [_texto_de(fila) for fila in self._textos])

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
        self._claves = []
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

    def poner_al_dia(self, claves, filas, elegida=None):
        """Deja la lista igual a `filas`, una por clave, sin recargar todo."""
        claves = list(claves)
        filas = list(filas)
        seleccion = self._lista.GetSelection()
        clave_elegida = self._clave_en(seleccion)
        self._sincronizar(claves, filas)
        self._claves = claves
        self._textos = filas
        if not filas:
            self._dejar_vacia()
        self._restaurar(seleccion, clave_elegida, claves, elegida)

    def _clave_en(self, indice):
        if 0 <= indice < len(self._claves):
            return self._claves[indice]
        return None

    def _sincronizar(self, claves, filas):
        actuales = list(self._claves)
        if len(actuales) != len(self._textos) or (self.vacia() and filas):
            actuales = []
            self._borrar_todo()
        por_clave = dict(zip(claves, filas))
        for paso in pasos_lista.pasos_para_sincronizar(actuales, claves):
            self._aplicar(paso, por_clave, actuales)
        for indice, fila in enumerate(filas):
            self._reescribir(indice, fila)

    def _aplicar(self, paso, por_clave, actuales):
        if paso[0] == "borrar":
            self._lista.Delete(paso[1])
            del actuales[paso[1]]
        else:
            self._lista.Insert(por_clave[paso[2]], paso[1])
            actuales.insert(paso[1], paso[2])

    def _borrar_todo(self):
        for indice in range(self._lista.GetCount() - 1, -1, -1):
            self._lista.Delete(indice)

    def _reescribir(self, indice, fila):
        """Reescribe la fila solo si su texto no es ya el deseado."""
        actual = self._lista.GetString(indice)
        actuales = actual if isinstance(actual, tuple) else (actual,)
        deseadas = fila if isinstance(fila, tuple) else (fila,)
        if actuales != deseadas:
            self._lista.SetString(indice, fila)

    def _dejar_vacia(self):
        """Deja la línea vacía como la deja `fijar`."""
        if self._lista.GetCount() == 1:
            return
        self._borrar_todo()
        self._lista.Append(self._texto_vacio)

    def _restaurar(self, seleccion, clave, claves, elegida):
        """Vuelve a elegir la fila de antes, sin tocarla si no se movió."""
        if elegida is not None and elegida in claves:
            self._elegir(claves.index(elegida), forzar=False)
        elif not claves:
            self._elegir(0, forzar=False)
        elif clave is not None and clave in claves:
            indice = claves.index(clave)
            self._elegir(indice, forzar=indice != seleccion)
        else:
            self._elegir(min(max(seleccion, 0), len(claves) - 1), forzar=True)

    def _elegir(self, indice, forzar):
        if not forzar and self._lista.GetSelection() == indice:
            return
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
    """Da teclas, menú contextual y caso vacío a una lista."""

    def __init__(self, lista, acciones, texto_vacio):
        self._lista = _envuelta(lista)
        self._acciones = tuple(acciones)
        self._vacio = ListaConVacio(self._lista, texto_vacio)
        self._ultimo_menu = None
        self._lista.Bind(wx.EVT_KEY_DOWN, self._al_tecla)
        self._lista.Bind(wx.EVT_CONTEXT_MENU, self._al_contexto)
        evento = (wx.EVT_LIST_ITEM_ACTIVATED
                  if isinstance(lista, wx.ListCtrl) else wx.EVT_LISTBOX_DCLICK)
        self._lista.Bind(evento, self._al_doble_clic)
        entregar_intro(self._lista, self._al_intro)

    def fijar(self, textos, elegido=None, vacio=None):
        """Reemplaza a Clear y Append y deja el caso vacío elegido."""
        self._vacio.fijar(textos, elegido, vacio)

    def poner_al_dia(self, claves, filas, elegida=None):
        """Deja la lista igual a `filas`, una por clave, sin recargar todo."""
        self._vacio.poner_al_dia(claves, filas, elegida)

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
        if self._avisar_motivo(accion):
            return True
        accion.manejador()
        return True

    def _avisar_motivo(self, accion) -> bool:
        """Anuncia el motivo de una acción que no se puede usar ahora."""
        motivo = accion.motivo() if accion.motivo is not None else ""
        if not motivo:
            return False
        anunciar(f"{motivo}.")
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
            habilitar(item, estados[accion.clave])
            menu.Bind(
                wx.EVT_MENU,
                lambda _evento, clave=accion.clave: self.ejecutar(clave),
                id=identificador)
        return menu
