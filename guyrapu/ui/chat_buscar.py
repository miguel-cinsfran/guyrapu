# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Cuadro para buscar un texto en los mensajes de la sesión del chat.

Replica el filtro de la ventana Música: filtra con cada cambio, anuncia la
cantidad a los 700 ms del último cambio y Escape borra antes de cerrar. La
lista lleva al mensaje elegido a la lista del chat.
"""

from __future__ import annotations

import wx

from guyrapu.core.idioma import N_, _
from guyrapu.ui import busqueda_chat, paleta, tecla_escape
from guyrapu.ui.accesibilidad import anunciar, entregar_intro, nombre_accesible
from guyrapu.ui.lista_acciones import ListaConVacio

# Traductores: título del cuadro que busca en los mensajes del chat.
TITULO = N_("Buscar en el chat")
TEXTO_ESCRIBE = N_("Escribe para buscar en los mensajes del chat.")
TEXTO_SIN_COINCIDENCIAS = N_("No hay mensajes con «{texto}».")
TEXTO_NINGUNO = N_("Ningún mensaje coincide")
TEXTO_UNO = N_("1 mensaje coincide")
TEXTO_VARIOS = N_("{n} mensajes coinciden")
TEXTO_BUSQUEDA_VACIADA = N_("Búsqueda vaciada")


def texto_coincidencias(cantidad: int) -> str:
    """Cuántos mensajes coinciden, para anunciar después de teclear."""
    cantidad = max(0, int(cantidad))
    if cantidad == 0:
        return _(TEXTO_NINGUNO)
    if cantidad == 1:
        return _(TEXTO_UNO)
    return _(TEXTO_VARIOS).format(n=cantidad)


class CuadroBuscarChat(wx.Dialog):
    """Campo de búsqueda, resultados y botón Cerrar."""

    def __init__(self, parent, acciones):
        super().__init__(parent, title=_(TITULO), size=(560, 460),
                         name="BuscarEnElChat")
        self._acciones = acciones
        self._resultados = []
        self._temporizador = None
        self._crear_controles()
        self._filtrar()
        self.txt_buscar.SetFocus()
        self.Centre()
        paleta.pintar_ventana(self)

    def _crear_controles(self):
        panel = wx.Panel(self, name="PanelBuscarChat")
        self._panel = panel
        vs = wx.BoxSizer(wx.VERTICAL)

        vs.Add(wx.StaticText(panel, label=_("&Buscar en el chat:")),
               0, wx.ALL, 8)
        self.txt_buscar = wx.TextCtrl(panel, name=_("Buscar en el chat"))
        nombre_accesible(self.txt_buscar, _("Buscar en el chat"))
        vs.Add(self.txt_buscar, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        vs.Add(wx.StaticText(panel, label=_("&Resultados:")), 0, wx.ALL, 8)
        self.lb_resultados = wx.ListBox(
            panel, style=wx.LB_SINGLE | wx.LB_HSCROLL, name=_("Resultados"))
        nombre_accesible(self.lb_resultados, _("Resultados"))
        self.lista_vacia = ListaConVacio(
            self.lb_resultados, _(TEXTO_ESCRIBE))
        vs.Add(self.lb_resultados, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        self.btn_cerrar = wx.Button(
            panel, wx.ID_CANCEL, _("&Cerrar"), name=_("Cerrar"))
        vs.Add(self.btn_cerrar, 0, wx.ALIGN_RIGHT | wx.ALL, 8)

        panel.SetSizer(vs)
        self._conectar()

    def _conectar(self):
        self.txt_buscar.Bind(wx.EVT_TEXT, self._al_escribir)
        self.Bind(wx.EVT_CHAR_HOOK, self._tecla_dialogo)
        self.btn_cerrar.Bind(wx.EVT_BUTTON, lambda e: self._cerrar())
        entregar_intro(self.lb_resultados, self._elegir)

    def _filtrar(self):
        texto = self.txt_buscar.GetValue()
        self._resultados = busqueda_chat.buscar(
            self._acciones.chat_vivo.modelo.todos, texto,
            self._acciones._autor_esta_oculto)
        if texto.strip():
            vacio = _(TEXTO_SIN_COINCIDENCIAS).format(texto=texto.strip())
        else:
            vacio = _(TEXTO_ESCRIBE)
        self.lista_vacia.fijar(
            [self._texto_resultado(mensaje) for mensaje in self._resultados],
            vacio=vacio)

    @staticmethod
    def _texto_resultado(mensaje) -> str:
        return f"{mensaje.autor}: {mensaje.texto}, {mensaje.hora}"

    def _al_escribir(self, evento):
        self._filtrar()
        self._cancelar_temporizador()
        self._temporizador = wx.CallLater(700, self._avisar_coincidencias)
        evento.Skip()

    def _avisar_coincidencias(self):
        if self.txt_buscar.GetValue().strip():
            anunciar(texto_coincidencias(len(self._resultados)))

    def _tecla_dialogo(self, evento):
        if tecla_escape.es_escape(evento.GetKeyCode()):
            self._escape()
            return
        evento.Skip()

    def _escape(self):
        if self.txt_buscar.GetValue():
            self.txt_buscar.ChangeValue("")
            self._filtrar()
            self._cancelar_temporizador()
            anunciar(_(TEXTO_BUSQUEDA_VACIADA))
        else:
            self._cerrar()

    def _elegir(self, evento=None):
        indice = self.lista_vacia.indice()
        if indice is None:
            return
        if self._acciones.enfocar_mensaje(self._resultados[indice]):
            self._cancelar_temporizador()
            self.EndModal(wx.ID_OK)

    def _cerrar(self):
        self._cancelar_temporizador()
        self.EndModal(wx.ID_CANCEL)

    def _cancelar_temporizador(self):
        if self._temporizador is not None:
            self._temporizador.Stop()
            self._temporizador = None

    def Destroy(self):
        self._cancelar_temporizador()
        return super().Destroy()


def abrir(parent, acciones) -> None:
    """Abre el cuadro de búsqueda sobre los mensajes de la sesión."""
    with CuadroBuscarChat(parent, acciones) as dialogo:
        dialogo.ShowModal()
