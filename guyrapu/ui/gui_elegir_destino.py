# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Ventana pequeña para elegir a dónde transmitir.

Modal y chica como `DialogoDirectoYoutube`: lista «Transmitir a» con
los destinos de OBS, campo de usuario visible solo para TikTok y
botones Continuar y Cancelar. Pura salvo wx.
"""

from __future__ import annotations

import wx

from guyrapu.obs.obs_destinos import DESTINOS
from guyrapu.core.idioma import _
from guyrapu.restream import ganchos, transmitir
from guyrapu.ui import ayuda_manual, formulario, paleta, tecla_escape
from guyrapu.ui.accesibilidad import anunciar, nombre_accesible


def destino_inicial(destino_guardado, opciones=None) -> str:
    """Destino con el que arranca la lista: el guardado o el primero."""
    opciones = tuple(opciones or DESTINOS)
    if destino_guardado in opciones:
        return destino_guardado
    return opciones[0]


def _opcion_elegida(seleccion, opciones) -> str:
    if seleccion is None or seleccion < 0 or seleccion >= len(opciones):
        return ""
    return opciones[seleccion]


def validar_eleccion(destino, usuario, opciones=None) -> tuple:
    """Valida lo elegido y devuelve (destino, usuario).

    Pura y sin ventanas: la usan el diálogo y las pruebas. Con TikTok
    y usuario vacío lanza ValueError con «Falta el usuario de TikTok.».
    Para YouTube y los perfiles de Restream el usuario no hace falta y se
    devuelve vacío.
    """
    from guyrapu.capture import tiktok_vivo
    opciones = tuple(opciones or DESTINOS)
    if destino not in opciones:
        destino = opciones[0]
    if destino == "TikTok":
        usuario = tiktok_vivo.usuario_tiktok(usuario or "")
        if not usuario:
            raise ValueError(_("Falta el usuario de TikTok."))
        return (destino, usuario)
    return (destino, "")


class DialogoElegirDestino(wx.Dialog):
    def __init__(self, padre, destino="", usuario="", perfiles=None):
        super().__init__(padre, title=_("Transmitir a"),
                         name="DialogoElegirDestino")
        perfiles = (ganchos.cargar_perfiles() if perfiles is None
                    else list(perfiles))
        self._opciones = transmitir.opciones(perfiles)
        destino = destino_inicial(destino, self._opciones)
        self._datos = None

        panel = wx.Panel(self, name="PanelElegirDestino")
        self._panel = panel
        vs = wx.BoxSizer(wx.VERTICAL)
        self._crear_destino(panel, vs, destino)
        self._crear_usuario(panel, vs, usuario)
        self._crear_botones(panel, vs)

        self._mostrar_usuario()
        formulario.ajustar_tamano(self, panel, vs)
        self.cho_destino.Bind(wx.EVT_CHOICE, self._al_destino)
        self.btn_continuar.Bind(wx.EVT_BUTTON, self._al_continuar)
        self.Bind(wx.EVT_CHAR_HOOK, self._al_tecla)
        self.cho_destino.SetFocus()

    def _crear_destino(self, panel, vs, destino):
        self.rotulo_destino = wx.StaticText(panel, label=_("Transmitir a:"))
        self.cho_destino = wx.Choice(
            panel, choices=[transmitir.texto(opcion)
                            for opcion in self._opciones],
            name=_("Transmitir a"))
        self.cho_destino.SetSelection(self._opciones.index(destino))
        nombre_accesible(self.cho_destino, _("Transmitir a"))
        formulario.agregar_fila(vs, self.rotulo_destino, self.cho_destino)

    def _crear_usuario(self, panel, vs, usuario):
        self.rotulo_usuario = wx.StaticText(
            panel, label=_("Usuario de TikTok:"))
        self.txt_usuario = wx.TextCtrl(
            panel, value=usuario or "", name=_("Usuario de TikTok"))
        nombre_accesible(self.txt_usuario, _("Usuario de TikTok"))
        formulario.agregar_fila(vs, self.rotulo_usuario, self.txt_usuario)

    def _crear_botones(self, panel, vs):
        # Traductores: botón para seguir con la transmisión.
        self.btn_continuar = wx.Button(panel, wx.ID_OK, _("&Continuar"), name=_("Continuar"))
        self.btn_continuar.SetDefault()
        # Traductores: botón para volver sin transmitir.
        self.btn_cancelar = wx.Button(panel, wx.ID_CANCEL, _("C&ancelar"), name=_("Cancelar"))
        formulario.agregar_pie(vs, [self.btn_continuar, self.btn_cancelar])

    @property
    def datos(self):
        return self._datos

    def _opcion_elegida(self):
        return _opcion_elegida(self.cho_destino.GetSelection(),
                               self._opciones)

    def _mostrar_usuario(self):
        visible = self._opcion_elegida() == "TikTok"
        self.rotulo_usuario.Show(visible)
        self.txt_usuario.Show(visible)
        self._panel.Layout()
        paleta.pintar_ventana(self)

    def _al_destino(self, _event):
        self._mostrar_usuario()

    def _al_continuar(self, _event) -> None:
        try:
            self._datos = validar_eleccion(
                self._opcion_elegida(),
                self.txt_usuario.GetValue(),
                self._opciones)
        except ValueError as exc:
            anunciar(str(exc))
            self.txt_usuario.Show()
            self.rotulo_usuario.Show()
            self._panel.Layout()
            self.txt_usuario.SetFocus()
            return
        self.EndModal(wx.ID_OK)

    def _al_tecla(self, event) -> None:
        if ayuda_manual.atender_f1(self, event, "transmitir"):
            return
        tecla_escape.cancelar_si_escape(self, event)


def pedir_destino(padre, destino_guardado, usuario_guardado):
    """Pide el destino y el usuario. Tupla (destino, usuario) o None."""
    dialogo = DialogoElegirDestino(padre, destino_guardado, usuario_guardado)
    try:
        if dialogo.ShowModal() == wx.ID_OK:
            return dialogo.datos
        return None
    finally:
        dialogo.Destroy()
