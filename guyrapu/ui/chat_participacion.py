# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Ventana con la participación del chat del directo conectado.

Muestra una foto del conteo al abrirla y permite guardarlo como texto.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import wx

from guyrapu.core.idioma import N_, _
from guyrapu.ui import ayuda_manual, confirmar, paleta, tecla_escape
from guyrapu.ui.accesibilidad import anunciar, nombre_accesible
from guyrapu.ui.lista_acciones import ListaConVacio
from guyrapu.voice import sound_player as _snd

# Traductores: título de la ventana con la participación del chat.
TITULO = N_("Participación en el chat")
TEXTO_VACIO = N_("Todavía no hay mensajes en este directo.")
TITULO_GUARDAR = N_("Guardar participación")
# Traductores: traduce solo «Archivos de texto»; no cambies «(*.txt)|*.txt».
FILTRO = N_("Archivos de texto (*.txt)|*.txt")
NOMBRE_PROPUESTO = N_("Participación {fecha}.txt")
TEXTO_GUARDADA = N_("Participación guardada.")
TEXTO_ERROR = N_("No se pudo guardar la participación:\n\n{exc}")


class VentanaParticipacion(wx.Dialog):
    """Lista de participación, con Guardar y Cerrar."""

    def __init__(self, parent, acciones):
        super().__init__(parent, title=_(TITULO), size=(520, 420),
                         name="ParticipacionEnElChat")
        self._acciones = acciones
        self._lineas = acciones.chat_vivo.participacion.lineas()
        self._crear_controles()
        self._cargar()
        self.lb_participacion.SetFocus()
        self.Centre()
        paleta.pintar_ventana(self)
        ayuda_manual.enlazar(self, "chat")

    def _crear_controles(self):
        panel = wx.Panel(self, name="PanelParticipacion")
        self._panel = panel
        vs = wx.BoxSizer(wx.VERTICAL)

        vs.Add(wx.StaticText(panel, label=_("&Participación:")),
               0, wx.ALL, 8)
        self.lb_participacion = wx.ListBox(
            panel, style=wx.LB_SINGLE | wx.LB_HSCROLL, name=_("Participación"))
        nombre_accesible(self.lb_participacion, _("Participación"))
        self.lista_vacia = ListaConVacio(
            self.lb_participacion, _(TEXTO_VACIO))
        vs.Add(self.lb_participacion, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        fila = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_guardar = wx.Button(
            panel, wx.ID_SAVE, _("&Guardar…"), name=_("Guardar"))
        self.btn_cerrar = wx.Button(
            panel, wx.ID_CANCEL, _("&Cerrar"), name=_("Cerrar"))
        fila.AddStretchSpacer()
        fila.Add(self.btn_guardar, 0, wx.RIGHT, 8)
        fila.Add(self.btn_cerrar)
        vs.Add(fila, 0, wx.EXPAND | wx.ALL, 8)

        panel.SetSizer(vs)
        self._conectar()

    def _conectar(self):
        self.Bind(wx.EVT_CHAR_HOOK, self._tecla_dialogo)
        self.btn_guardar.Bind(wx.EVT_BUTTON, self._guardar)
        self.btn_cerrar.Bind(wx.EVT_BUTTON, lambda e: self._cerrar())

    def _cargar(self):
        self.lista_vacia.fijar(self._lineas)

    def _tecla_dialogo(self, evento):
        if tecla_escape.es_escape(evento.GetKeyCode()):
            self._cerrar()
            return
        evento.Skip()

    def _guardar(self, evento=None):
        if not self._lineas:
            anunciar(_(TEXTO_VACIO))
            return
        with wx.FileDialog(
                self, _(TITULO_GUARDAR), wildcard=_(FILTRO),
                defaultFile=_(NOMBRE_PROPUESTO).format(
                    fecha=date.today().isoformat()),
                style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as cuadro:
            if cuadro.ShowModal() != wx.ID_OK:
                return
            ruta = cuadro.GetPath()
        try:
            self._escribir(ruta)
        except Exception as exc:
            _snd.reproducir("error")
            confirmar.avisar(
                self, _(TEXTO_ERROR).format(exc=exc), _(TITULO_GUARDAR),
                _("Aceptar"), icono=confirmar.ICON_ERROR)
            return
        _snd.reproducir("listo")
        anunciar(_(TEXTO_GUARDADA))

    def _escribir(self, ruta: str) -> None:
        Path(ruta).write_text("\n".join(self._lineas) + "\n",
                              encoding="utf-8")

    def _cerrar(self):
        self.EndModal(wx.ID_CANCEL)


def abrir(parent, acciones) -> None:
    """Abre la ventana con la participación del directo conectado."""
    with VentanaParticipacion(parent, acciones) as dialogo:
        dialogo.ShowModal()
