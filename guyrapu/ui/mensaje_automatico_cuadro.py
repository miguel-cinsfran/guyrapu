# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Cuadro que edita un mensaje automático y el que cambia solo su nombre.

Recoge los datos y valida: no guarda. La colección y el disco los maneja la
ventana de mensajes automáticos.
"""

from __future__ import annotations

import wx

from guyrapu.core import paths
from guyrapu.core.idioma import N_, _
from guyrapu.capture import programados
from guyrapu.obs import estilos_aviso
from guyrapu.ui import paleta, tecla_escape
from guyrapu.ui.accesibilidad import ContadorAccesible, anunciar, nombre_accesible
from guyrapu.ui.preferencias_comun import fila_label, nombre_de_etiqueta

TITULO_AGREGAR = N_("Agregar mensaje automático")
TITULO_EDITAR = N_("Editar mensaje automático")

_DESTINOS = ("chat", "video", "ambos")


def _destinos():
    return [_("Chat"), _("Vídeo"), _("Chat y vídeo")]


def _estilos():
    return estilos_aviso.todos(
        estilos_aviso.cargar_estilos(paths.estilos_avisos()))


class DialogoMensaje(wx.Dialog):
    """Nombre, texto, destino, estilo, tiempos y actividad de un mensaje."""

    def __init__(self, padre, mensaje, otros):
        super().__init__(
            padre,
            title=_(TITULO_EDITAR if mensaje else TITULO_AGREGAR),
            name="DialogoMensajeAutomatico")
        self._otros = list(otros)
        self._estilos = _estilos()
        self._crear_controles(mensaje)
        self.Bind(wx.EVT_CHAR_HOOK, self._al_tecla)
        self.Fit()
        self.Centre()
        paleta.pintar_ventana(self)
        self.txt_nombre.SetFocus()

    def _crear_controles(self, mensaje):
        panel = wx.Panel(self, name="PanelMensajeAutomatico")
        vs = wx.BoxSizer(wx.VERTICAL)
        vs.Add(fila_label(panel, _("&Nombre:")), 0, wx.ALL, 8)
        self.txt_nombre = self._campo(panel, _("Nombre del mensaje"))
        vs.Add(self.txt_nombre, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        vs.Add(fila_label(panel, _("&Texto del mensaje:")), 0, wx.LEFT | wx.RIGHT, 8)
        self.txt_texto = self._campo(panel, _("Texto del mensaje"))
        self.txt_texto.SetMaxLength(programados.MAX_CARACTERES)
        vs.Add(self.txt_texto, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        vs.Add(fila_label(panel, _("Dónde se &muestra:")), 0, wx.LEFT | wx.RIGHT, 8)
        self.cho_destino = wx.Choice(
            panel, choices=_destinos(), name=nombre_de_etiqueta(_("Dónde se muestra:")))
        nombre_accesible(self.cho_destino, self.cho_destino.GetName())
        vs.Add(self.cho_destino, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        vs.Add(fila_label(panel, _("&Estilo:")), 0, wx.LEFT | wx.RIGHT, 8)
        self.cho_estilo = wx.Choice(
            panel, choices=[_(estilo["nombre"]) for estilo in self._estilos],
            name=nombre_de_etiqueta(_("Estilo:")))
        nombre_accesible(self.cho_estilo, self.cho_estilo.GetName())
        vs.Add(self.cho_estilo, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        self.sp_segundos = self._contador(
            panel, _("Segundos en pantalla"), 3, 60, 10)
        self.sp_min = self._contador(
            panel, _("Intervalo mínimo, en minutos"), 5, 240, 10)
        self.sp_max = self._contador(
            panel, _("Intervalo máximo, en minutos"), 5, 240, 10)
        self.sp_entre = self._contador(
            panel, _("Mensajes del chat entre uno y otro"), 0, 100, 0)
        for etiqueta, control in (
                (_("&Segundos en pantalla:"), self.sp_segundos),
                (_("Intervalo m&ínimo, en minutos:"), self.sp_min),
                (_("Intervalo má&ximo, en minutos:"), self.sp_max),
                (_("Mensajes del c&hat entre uno y otro:"), self.sp_entre)):
            vs.Add(fila_label(panel, etiqueta), 0, wx.LEFT | wx.RIGHT, 8)
            vs.Add(control, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        self.chk_activo = wx.CheckBox(
            panel, label=_("Acti&vo"), name=nombre_de_etiqueta(_("Activo")))
        vs.Add(self.chk_activo, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)
        vs.Add(self._botones(panel), 0, wx.ALIGN_RIGHT | wx.ALL, 8)
        panel.SetSizer(vs)
        self._cargar(mensaje)

    def _campo(self, panel, nombre):
        campo = wx.TextCtrl(panel, name=nombre)
        nombre_accesible(campo, nombre)
        return campo

    def _contador(self, panel, rotulo, minimo, maximo, inicial):
        control = ContadorAccesible(
            panel, min=minimo, max=maximo, initial=inicial, name=rotulo)
        nombre_accesible(control, rotulo)
        return control

    def _botones(self, panel):
        fila = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_aceptar = wx.Button(panel, wx.ID_OK, _("&Aceptar"), name=_("Aceptar"))
        self.btn_cancelar = wx.Button(
            panel, wx.ID_CANCEL, _("&Cancelar"), name=_("Cancelar"))
        self.btn_aceptar.SetDefault()
        self.btn_aceptar.Bind(wx.EVT_BUTTON, self._aceptar)
        self.btn_cancelar.Bind(
            wx.EVT_BUTTON, lambda _evento: self.EndModal(wx.ID_CANCEL))
        fila.Add(self.btn_aceptar, 0, wx.RIGHT, 6)
        fila.Add(self.btn_cancelar, 0)
        return fila

    def _cargar(self, mensaje):
        self.txt_nombre.SetValue(mensaje.get("nombre", ""))
        self.txt_texto.SetValue(mensaje.get("texto", ""))
        self.cho_destino.SetSelection(
            _DESTINOS.index(mensaje.get("destino", "chat")))
        self._elegir_estilo(mensaje.get("estilo", "clasico"))
        self.sp_segundos.SetValue(mensaje.get("segundos_pantalla", 10))
        self.sp_min.SetValue(mensaje.get("minutos_min", 10))
        self.sp_max.SetValue(mensaje.get(
            "minutos_max", mensaje.get("minutos_min", 10)))
        self.sp_entre.SetValue(mensaje.get("mensajes_entre", 0))
        self.chk_activo.SetValue(mensaje.get("activo", True))

    def _elegir_estilo(self, clave):
        for indice, estilo in enumerate(self._estilos):
            if estilo["clave"] == clave:
                self.cho_estilo.SetSelection(indice)
                return
        self.cho_estilo.SetSelection(0)

    def _aceptar(self, _evento):
        nombre = self.txt_nombre.GetValue()
        error = programados.validar_nombre(nombre, self._otros)
        if error:
            anunciar(error)
            self.txt_nombre.SetFocus()
            return
        texto = self.txt_texto.GetValue()
        minimo = self.sp_min.GetValue()
        maximo = self.sp_max.GetValue()
        error, aviso = programados.validar_mensaje(texto, minimo, maximo)
        if error:
            anunciar(error)
            self._foco_del_error(texto, minimo)
            return
        if aviso:
            anunciar(aviso)
        self.EndModal(wx.ID_OK)

    def _foco_del_error(self, texto, minimo):
        if not texto.strip() or len(texto) > programados.MAX_CARACTERES:
            self.txt_texto.SetFocus()
        elif minimo < programados.MINUTOS_MINIMOS:
            self.sp_min.SetFocus()
        else:
            self.sp_max.SetFocus()

    def datos(self) -> dict:
        """El mensaje tal como se guarda, sin tocar su próximo envío."""
        return {
            "nombre": self.txt_nombre.GetValue().strip(),
            "texto": self.txt_texto.GetValue(),
            "destino": _DESTINOS[self.cho_destino.GetSelection()],
            "estilo": self._estilos[self.cho_estilo.GetSelection()]["clave"],
            "segundos_pantalla": self.sp_segundos.GetValue(),
            "minutos_min": self.sp_min.GetValue(),
            "minutos_max": self.sp_max.GetValue(),
            "mensajes_entre": self.sp_entre.GetValue(),
            "activo": self.chk_activo.GetValue(),
        }

    def _al_tecla(self, evento):
        tecla_escape.cancelar_si_escape(self, evento)


class DialogoNombre(wx.Dialog):
    """Pide un nombre, sin validarlo: el bucle de la ventana lo repite."""

    def __init__(self, padre, nombre):
        super().__init__(padre, title=_("Cambiar nombre"),
                         name="DialogoNombreMensaje")
        caja = wx.BoxSizer(wx.VERTICAL)
        caja.Add(fila_label(self, _("&Nombre:")), 0, wx.ALL, 8)
        self.txt_nombre = wx.TextCtrl(
            self, name=nombre_de_etiqueta(_("Nombre:")))
        nombre_accesible(self.txt_nombre, self.txt_nombre.GetName())
        self.txt_nombre.SetValue(nombre)
        caja.Add(self.txt_nombre, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        fila = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_aceptar = wx.Button(self, wx.ID_OK, _("&Aceptar"), name=_("Aceptar"))
        self.btn_cancelar = wx.Button(
            self, wx.ID_CANCEL, _("&Cancelar"), name=_("Cancelar"))
        self.btn_aceptar.SetDefault()
        fila.Add(self.btn_aceptar, 0, wx.RIGHT, 6)
        fila.Add(self.btn_cancelar, 0)
        caja.Add(fila, 0, wx.ALIGN_RIGHT | wx.ALL, 8)
        self.SetSizerAndFit(caja)
        self.SetMinSize((360, -1))
        self.Centre()
        paleta.pintar_ventana(self)
        self.Bind(wx.EVT_CHAR_HOOK, self._al_tecla)
        self.txt_nombre.SetFocus()

    def nombre(self) -> str:
        return self.txt_nombre.GetValue().strip()

    def _al_tecla(self, evento):
        tecla_escape.cancelar_si_escape(self, evento)


def abrir(padre, mensaje=None, otros=()):
    """Abre el cuadro y devuelve el mensaje, o None si se cancela."""
    dialogo = DialogoMensaje(padre, mensaje or {}, otros)
    try:
        if dialogo.ShowModal() != wx.ID_OK:
            return None
        return dialogo.datos()
    finally:
        dialogo.Destroy()


def pedir_nombre(padre, nombre) -> str | None:
    """Abre el cuadro del nombre y devuelve el texto, o None."""
    dialogo = DialogoNombre(padre, nombre)
    try:
        if dialogo.ShowModal() != wx.ID_OK:
            return None
        return dialogo.nombre()
    finally:
        dialogo.Destroy()
