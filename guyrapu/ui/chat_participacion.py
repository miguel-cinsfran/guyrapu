# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Ventana con la participación del chat del directo conectado.

Muestra una foto del conteo al abrirla, permite ordenarlo por mensajes o
por regalos, guardarlo como texto y abrir la carpeta de resúmenes.
"""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path

import wx

from guyrapu.core import paths
from guyrapu.core.idioma import N_, _
from guyrapu.ui import ayuda_manual, confirmar, paleta, tecla_escape
from guyrapu.ui.accesibilidad import anunciar, nombre_accesible
from guyrapu.ui.lista_acciones import ListaConVacio
from guyrapu.ui.participacion_chat import ORDEN_MENSAJES, ORDENES
from guyrapu.voice import sound_player as _snd

# Traductores: título de la ventana con la participación del chat.
TITULO = N_("Participación en el chat")
# Traductores: fila de un directo sin mensajes en la lista de participación.
TEXTO_VACIO = N_(
    "No hay mensajes en este directo. Aquí aparece cuántos mensajes y regalos "
    "escribió cada persona. Conecta un directo y espera a que lleguen mensajes.")
TITULO_GUARDAR = N_("Guardar participación")
# Traductores: traduce solo «Archivos de texto»; no cambies «(*.txt)|*.txt».
FILTRO = N_("Archivos de texto (*.txt)|*.txt")
NOMBRE_PROPUESTO = N_("Participación {fecha}.txt")
TEXTO_GUARDADA = N_("Participación guardada.")
TEXTO_ERROR = N_("No se pudo guardar la participación:\n\n{exc}")
TITULO_CARPETA = N_("Carpeta de resúmenes")
TEXTO_ERROR_CARPETA = N_("No se pudo abrir la carpeta de resúmenes:\n\n{exc}")


class VentanaParticipacion(wx.Dialog):
    """Lista de participación, con Guardar y Cerrar."""

    def __init__(self, parent, acciones):
        super().__init__(parent, title=_(TITULO), size=(520, 420),
                         name="ParticipacionEnElChat")
        self._acciones = acciones
        self._participacion = acciones.chat_vivo.participacion
        self._orden = ORDEN_MENSAJES
        self._lineas = self._participacion.lineas(self._orden)
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
        vs.Add(self.lb_participacion, 1,
               wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        self._crear_orden(panel, vs)
        self._crear_botones(panel, vs)

        panel.SetSizer(vs)
        self._conectar()

    def _crear_orden(self, panel, vs):
        fila = wx.BoxSizer(wx.HORIZONTAL)
        self.lb_orden = wx.StaticText(panel, label=_("Or&denar por:"))
        self.cb_orden = wx.Choice(panel, name=_("Ordenar por"))
        nombre_accesible(self.cb_orden, _("Ordenar por"))
        self.cb_orden.Set([_(etiqueta) for _clave, etiqueta in ORDENES])
        self.cb_orden.SetSelection(0)
        fila.Add(self.lb_orden, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        fila.Add(self.cb_orden, 0, wx.ALIGN_CENTER_VERTICAL)
        vs.Add(fila, 0, wx.LEFT | wx.RIGHT, 8)

    def _crear_botones(self, panel, vs):
        fila = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_guardar = wx.Button(
            panel, wx.ID_SAVE, _("&Guardar…"), name=_("Guardar"))
        self.btn_resumenes = wx.Button(
            panel, label=_("&Abrir carpeta de resúmenes"),
            name=_("Abrir carpeta de resúmenes"))
        self.btn_cerrar = wx.Button(
            panel, wx.ID_CANCEL, _("&Cerrar"), name=_("Cerrar"))
        fila.AddStretchSpacer()
        fila.Add(self.btn_guardar, 0, wx.RIGHT, 8)
        fila.Add(self.btn_resumenes, 0, wx.RIGHT, 8)
        fila.Add(self.btn_cerrar)
        vs.Add(fila, 0, wx.EXPAND | wx.ALL, 8)

    def _conectar(self):
        self.Bind(wx.EVT_CHAR_HOOK, self._tecla_dialogo)
        self.btn_guardar.Bind(wx.EVT_BUTTON, self._guardar)
        self.btn_resumenes.Bind(wx.EVT_BUTTON, lambda e: self._abrir_resumenes())
        self.btn_cerrar.Bind(wx.EVT_BUTTON, lambda e: self._cerrar())
        self.cb_orden.Bind(wx.EVT_CHOICE, self._cambiar_orden)

    def _cargar(self):
        self.lista_vacia.fijar(self._lineas)

    def _cambiar_orden(self, evento=None):
        indice = self.cb_orden.GetSelection()
        self._orden = (ORDENES[indice][0]
                       if 0 <= indice < len(ORDENES) else ORDEN_MENSAJES)
        self._lineas = self._participacion.lineas(self._orden)
        self._cargar()
        self.lb_participacion.SetFocus()

    def _abrir_resumenes(self):
        carpeta = paths.resumenes_sesion()
        try:
            carpeta.mkdir(parents=True, exist_ok=True)
            os.startfile(str(carpeta))  # noqa: S606
        except Exception as exc:
            _snd.reproducir("error")
            confirmar.avisar(
                self, _(TEXTO_ERROR_CARPETA).format(exc=exc),
                _(TITULO_CARPETA), _("Aceptar"), icono=confirmar.ICON_ERROR)

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
