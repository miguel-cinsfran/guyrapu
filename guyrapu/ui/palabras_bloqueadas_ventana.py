# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""La lista de palabras bloqueadas del público y sus acciones.

El panel vive en la ventana Interacción. Cada cambio se guarda al momento,
y las respuestas de los comandos releen el archivo cuando cambia.
"""

from __future__ import annotations

import wx

from guyrapu.core import paths
from guyrapu.core.idioma import N_, _
from guyrapu.interaction import filtro_publico
from guyrapu.interaction.texto import normalizar
from guyrapu.ui import botonera
from guyrapu.ui import confirmar
from guyrapu.ui.accesibilidad import anunciar, nombre_accesible
from guyrapu.ui.lista_acciones import Accion, ListaConAcciones
from guyrapu.ui.pagina_de_lista import agregar_botones, agregar_lista
from guyrapu.ui.preferencias_comun import fila_label

VACIO = N_(
    "No hay palabras bloqueadas. Aquí aparecen las palabras que se tapan en "
    "lo que el público escribe y se muestra en el vídeo. "
    "Usa Agregar para escribir una.")
REPETIDA = N_("Esa palabra ya está en la lista.")
VACIA = N_("Escribe una palabra o frase.")


def pedir_palabra(padre, inicial=""):
    """Pide una palabra o frase, o None si se cancela."""
    dialogo = wx.TextEntryDialog(
        padre, _("Palabra o frase:"), _("Palabras bloqueadas"), value=inicial)
    try:
        if dialogo.ShowModal() == wx.ID_OK:
            return dialogo.GetValue()
        return None
    finally:
        dialogo.Destroy()


def _acciones(panel):
    return (
        Accion("agregar", _("A&gregar"), panel._agregar,
               necesita_elemento=False),
        Accion("editar", _("&Editar"), panel._editar, tecla="intro"),
        Accion("eliminar", _("E&liminar"), panel._eliminar,
               tecla="suprimir"),
    )


class PanelPalabrasBloqueadas(wx.Panel):
    """La lista de palabras bloqueadas con sus acciones."""

    def __init__(self, padre):
        super().__init__(padre, name="PanelPalabrasBloqueadas")
        self._ruta = paths.palabras_bloqueadas()
        self._palabras = filtro_publico.cargar(self._ruta)
        self._crear_controles()

    def _crear_controles(self):
        vs = wx.BoxSizer(wx.VERTICAL)
        rotulo = fila_label(self, _("Palabras &bloqueadas:"))
        self.lista = wx.ListBox(
            self, style=wx.LB_SINGLE | wx.LB_HSCROLL,
            name="ListaPalabrasBloqueadas")
        nombre_accesible(self.lista, _("Palabras bloqueadas"))
        self._acciones = _acciones(self)
        self._lista = ListaConAcciones(self.lista, self._acciones, _(VACIO))
        self._lista.fijar(self._textos())
        agregar_lista(vs, rotulo, self.lista)
        agregar_botones(vs, self._fila_de_botones())
        self.SetSizer(vs)
        self.lista.SetFocus()

    def _fila_de_botones(self):
        return botonera.armar(self, self._acciones, self._lista)

    def _textos(self):
        return list(self._palabras)

    def _fijar(self, indice=-1):
        self._lista.fijar(self._textos(), indice)
        self.lista.SetFocus()

    def _guardar(self):
        filtro_publico.guardar(self._ruta, self._palabras)

    def _elegido(self):
        return self._lista.indice()

    def _repetida(self, palabra, salvo=None) -> bool:
        buscada = normalizar(palabra)
        return any(normalizar(otra) == buscada
                   for indice, otra in enumerate(self._palabras)
                   if indice != salvo)

    def _agregar(self):
        while True:
            palabra = pedir_palabra(self)
            if palabra is None:
                return
            palabra = palabra.strip()
            if not palabra:
                anunciar(_(VACIA))
                continue
            if self._repetida(palabra):
                anunciar(_(REPETIDA))
                continue
            break
        self._palabras.append(palabra)
        self._guardar()
        self._fijar(len(self._palabras) - 1)
        anunciar(_("Palabra agregada"))

    def _editar(self):
        indice = self._elegido()
        if indice is None:
            return
        while True:
            palabra = pedir_palabra(self, self._palabras[indice])
            if palabra is None:
                return
            palabra = palabra.strip()
            if not palabra:
                anunciar(_(VACIA))
                continue
            if self._repetida(palabra, salvo=indice):
                anunciar(_(REPETIDA))
                continue
            break
        self._palabras[indice] = palabra
        self._guardar()
        self._fijar(indice)
        anunciar(_("Palabra guardada"))

    def _eliminar(self):
        indice = self._elegido()
        if indice is None:
            return
        palabra = self._palabras[indice]
        if not confirmar.preguntar(
                self,
                _("¿Eliminar «{palabra}» de las palabras bloqueadas?").format(
                    palabra=palabra),
                _("Eliminar palabra bloqueada"), _("&Eliminar"),
                _("&Cancelar"), predeterminado_si=False):
            return
        self._palabras.pop(indice)
        self._guardar()
        self._fijar(min(indice, len(self._palabras) - 1))
        anunciar(_("Palabra eliminada"))
