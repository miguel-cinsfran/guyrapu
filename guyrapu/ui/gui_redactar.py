# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Controles accesibles para redactar mensajes de varias líneas."""

from __future__ import annotations

import wx

from guyrapu.capture import redaccion
from guyrapu.core.idioma import _
from guyrapu.ui import formulario, paleta


def _anunciar(texto: str) -> None:
    from guyrapu.ui.accesibilidad import anunciar
    anunciar(texto)


class PanelRedactar(wx.Panel):
    def __init__(self, parent, etiqueta, maximo, al_enviar, en_dialogo=False):
        super().__init__(parent, name="PanelRedactar")
        self._maximo = maximo
        self._al_enviar = al_enviar
        self._motivo = ""

        vs = wx.BoxSizer(wx.VERTICAL)
        self.etiqueta = wx.StaticText(self, label=etiqueta, name="EtiquetaRedaccion")
        self.texto = wx.TextCtrl(self, style=wx.TE_MULTILINE, name=_("Mensaje para el chat"))
        self.texto.SetMinSize((-1, (4 if en_dialogo else 3)
                               * self.texto.GetCharHeight() + 12))
        # Traductores: botón para enviar el mensaje.
        self.boton = wx.Button(self, label=_("E&nviar"), name=_("Enviar mensaje al chat"))
        if en_dialogo:
            formulario.agregar_fila(vs, self.etiqueta, self.texto)
            self.btn_cancelar = wx.Button(
                self, wx.ID_CANCEL, _("&Cancelar"), name=_("Cancelar"))
            formulario.agregar_pie(vs, [self.boton, self.btn_cancelar])
        else:
            fila = wx.BoxSizer(wx.HORIZONTAL)
            fila.Add(self.etiqueta, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
            fila.Add(self.texto, 1, wx.EXPAND | wx.RIGHT, 6)
            fila.Add(self.boton, 0, wx.ALIGN_BOTTOM)
            vs.Add(fila, 1, wx.EXPAND)
        self.contenido = vs
        if not en_dialogo:
            self.SetSizer(vs)
        self.boton.Bind(wx.EVT_BUTTON, self._on_enviar)
        self.texto.Bind(wx.EVT_CHAR_HOOK, self._on_char_hook)

    def establecer_motivo(self, motivo: str) -> None:
        self._motivo = motivo or ""
        base = self.boton.GetLabel().split(" (")[0]
        self.boton.SetLabel(redaccion.etiqueta_con_motivo(base, self._motivo))
        self.boton.InvalidateBestSize()
        self.Layout()

    def motivo(self) -> str:
        """Por qué no se puede enviar ahora («» si se puede)."""
        return self._motivo

    def enfocar(self) -> None:
        self.texto.SetFocus()

    def _on_char_hook(self, event) -> None:
        if (event.GetKeyCode() in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER)
                and not event.ShiftDown()):
            self._on_enviar(event)
            return
        event.Skip()

    def _on_enviar(self, _event) -> None:
        if self._motivo:
            _anunciar(self._motivo)
            self.enfocar()
            return
        motivo = redaccion.validar(self.texto.GetValue(), self._maximo)
        if motivo:
            _anunciar(motivo)
            self.enfocar()
            return
        texto = redaccion.limpiar(self.texto.GetValue())
        self._al_enviar(texto)
        self.texto.Clear()
        self.enfocar()


class DialogoRedactar(wx.Dialog):
    texto_enviado = ""

    def __init__(self, parent, etiqueta, maximo, al_enviar,
                 titulo=None, motivo="", nombre_texto=None,
                 nombre_boton=None):
        # Traductores: título de la ventana para redactar.
        titulo = _("Redactar") if titulo is None else titulo
        nombre_texto = _("Texto del comentario") if nombre_texto is None else nombre_texto
        # Traductores: nombre del botón que publica.
        nombre_boton = _("Publicar") if nombre_boton is None else nombre_boton
        super().__init__(parent, title=titulo, name="DialogoRedactar")
        self.SetEscapeId(wx.ID_CANCEL)
        self._al_enviar = al_enviar
        self.panel = PanelRedactar(
            self, etiqueta, maximo, self._enviar, en_dialogo=True)
        self.panel.texto.SetName(nombre_texto)
        # Traductores: botón con el nombre que pone el llamador; {boton} es ese nombre.
        self.panel.boton.SetLabel(_("&{boton}").format(boton=nombre_boton))
        self.panel.boton.SetName(nombre_boton)
        self.panel.boton.SetDefault()
        self.panel.establecer_motivo(motivo)
        formulario.ajustar_tamano(self, self.panel, self.panel.contenido)
        self.panel.btn_cancelar.Bind(
            wx.EVT_BUTTON, lambda e: self.EndModal(wx.ID_CANCEL))
        paleta.pintar_ventana(self)

    def _enviar(self, texto) -> None:
        self.texto_enviado = texto
        if self._al_enviar:
            self._al_enviar(texto)
        self.EndModal(wx.ID_OK)
