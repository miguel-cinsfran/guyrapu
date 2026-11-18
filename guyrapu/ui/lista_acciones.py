# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Teclas, menú contextual y caso vacío para una lista con acciones.

Lo puro, como las teclas y qué acciones van encendidas, vive en
`lista_pura`. `ListaConVacio` deja el caso vacío elegido en una lista y
`ListaConAcciones` ata esas reglas a una lista.
"""

from __future__ import annotations

import time

import wx

from guyrapu.core import pasos_lista
from guyrapu.core import sonidos_eventos
from guyrapu.core.idioma import _
from guyrapu.ui.accesibilidad import anunciar, entregar_intro
from guyrapu.ui.busqueda_teclado import instalar_busqueda_tipo
from guyrapu.ui.lista_ctrl import ListaCtrlEnvuelta
from guyrapu.ui.lista_pura import (
    Accion, _con_apariciones, _indice_restaurado, acciones_encendidas,
    clave_de_tecla, motivo_de)
from guyrapu.ui.menu_lista import (
    construir_menu, etiqueta_de_menu, mostrar_opciones)
from guyrapu.voice import sound_player as _snd

# La tecla y el menú contextual pueden llegar los dos en la misma pulsación.
_SEGUNDOS_MENU = 0.5


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
        internas = _con_apariciones(claves)
        seleccion = self._lista.GetSelection()
        clave_elegida = self._clave_en(seleccion)
        self._sincronizar(internas, filas)
        self._claves = internas
        self._textos = filas
        self._restaurar(seleccion, clave_elegida, claves, internas, elegida)

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

    def _restaurar(self, seleccion, clave, claves, internas, elegida):
        """Vuelve a elegir la fila de antes, sin tocarla si no se movió."""
        if not claves:
            self._dejar_vacia()
        indice, forzar = _indice_restaurado(
            seleccion, clave, claves, internas, elegida)
        self._elegir(indice, forzar)

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

    def indices(self):
        """Los índices elegidos en orden, o una lista vacía."""
        if not self._textos:
            return []
        if isinstance(self._lista, ListaCtrlEnvuelta):
            elegidos = self._lista.GetSelections()
        else:
            elegidos = [self._lista.GetSelection()]
        return [indice for indice in elegidos
                if 0 <= indice < len(self._textos)]

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

    def indices(self):
        """Los índices elegidos en orden, o una lista vacía."""
        return self._vacio.indices()

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
        if self._rechazar(accion):
            return True
        if accion.opciones is not None:
            self._abrir_opciones(accion)
        else:
            accion.manejador()
        return True

    def _rechazar(self, accion) -> bool:
        """Anuncia por qué no se puede usar la acción, si es el caso."""
        elegidas = self.indices()
        if accion.necesita_elemento and not elegidas:
            self._vacio.sin_elemento()
            return True
        motivo = motivo_de(accion, elegidas)
        if motivo:
            anunciar(f"{motivo}.")
            return True
        return False

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

    def _abrir_opciones(self, accion):
        """Muestra las opciones de la acción sobre la lista."""
        mostrar_opciones(self._lista, accion.opciones)

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
        elegidas = self.indices()
        estados = acciones_encendidas(self._acciones, len(elegidas))
        motivos = {}
        for accion in self._acciones:
            motivo = motivo_de(accion, elegidas)
            if not motivo:
                continue
            motivos[accion.clave] = motivo
            if accion.motivo_indices is not None:
                estados[accion.clave] = False
        return construir_menu(self._acciones, estados, self.ejecutar, motivos)
