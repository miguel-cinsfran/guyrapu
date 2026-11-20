# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""La ventana Prueba sin directo y el final del ensayo.

Los mensajes se arman con `ensayo.registro` y entran por `chat_vivo.encolar`,
el mismo reparto que un mensaje del directo. No se toca la captura ni la voz.
"""

from __future__ import annotations

import wx

from guyrapu.core import plataformas
from guyrapu.core.idioma import _
from guyrapu.interaction import ensayo
from guyrapu.ui import (
    encuesta_en_vivo, formulario, gui_envio_chat, preguntas_en_vivo,
    tecla_escape)
from guyrapu.ui.accesibilidad import anunciar, nombre_accesible
from guyrapu.ui.paleta import pintar_ventana
from guyrapu.ui.preferencias_comun import fila_label, nombre_de_etiqueta
from guyrapu.voice import sound_player as _snd

TIPOS = (ensayo.MENSAJE, ensayo.SUPER_CHAT, ensayo.REGALO)


def terminar(frame):
    """Cierra el ensayo con la limpieza de una desconexión y lo que esta no toca."""
    frame._ensayo = False
    frame._reiniciar_datos_sesion()
    gui_envio_chat.capa_de_video(frame).vaciar()
    encuesta_en_vivo.descartar(frame)
    preguntas_en_vivo.vaciar(frame)


def abrir(frame):
    """Abre la ventana, o dice por qué no si hay un directo conectado."""
    if frame._conectado:
        _snd.reproducir("error")
        # Traductores: motivo de no poder probar sin directo estando conectado.
        anunciar(_("Desconecta el directo para probar sin él."))
        return
    abierta = getattr(frame, "_ventana_ensayo", None)
    if abierta is not None and not abierta.cerrado:
        abierta.Raise()
        abierta.txt_mensaje.SetFocus()
        return
    frame._ensayo = True
    ventana = VentanaEnsayo(frame)
    frame._ventana_ensayo = ventana
    ventana.Show()


class VentanaEnsayo(wx.Dialog):
    """Los campos de un mensaje de prueba y sus botones Enviar y Cerrar."""

    def __init__(self, frame):
        super().__init__(
            frame, title=_("Prueba sin directo"), name=_("Prueba sin directo"),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self._frame = frame
        self.cerrado = False
        self._crear_controles()
        self.Bind(wx.EVT_CHAR_HOOK, self._al_tecla)
        self.Bind(wx.EVT_CLOSE, self._cerrar)
        pintar_ventana(self)
        self.Centre()
        self.txt_autor.SetFocus()

    def _crear_controles(self):
        panel = wx.Panel(self, name="PanelEnsayo")
        vs = wx.BoxSizer(wx.VERTICAL)
        self._agregar(vs, panel, _("&Autor:"), "txt_autor", wx.TextCtrl)
        self.txt_autor.SetValue(_(ensayo.AUTOR_PREDETERMINADO))
        self._agregar(vs, panel, _("P&lataforma:"), "cho_plataforma", wx.Choice,
                      opciones=[plataformas.nombre(plataformas.YOUTUBE),
                                plataformas.nombre(plataformas.TIKTOK)])
        self.cho_plataforma.SetSelection(0)
        # Traductores: opciones del tipo de mensaje de la ventana de ensayo.
        self._agregar(vs, panel, _("&Tipo:"), "cho_tipo", wx.Choice,
                      opciones=[_("Mensaje"), _("Super Chat"), _("Regalo")])
        self.cho_tipo.SetSelection(0)
        self._agregar(vs, panel, _("Canti&dad:"), "txt_cantidad", wx.TextCtrl)
        self._agregar(vs, panel, _("M&ensaje:"), "txt_mensaje", wx.TextCtrl,
                      hueco=0)
        self.btn_enviar = self._boton(panel, _("En&viar"))
        self.btn_enviar.SetDefault()
        self.btn_enviar.Bind(wx.EVT_BUTTON, self._enviar)
        self.btn_cerrar = self._boton(panel, _("Ce&rrar"))
        self.btn_cerrar.Bind(wx.EVT_BUTTON, self._cerrar)
        formulario.agregar_pie(vs, [self.btn_enviar, self.btn_cerrar])
        formulario.ajustar_tamano(self, panel, vs)

    def _agregar(self, vs, panel, etiqueta, nombre, clase, opciones=(),
                 hueco=formulario.CONTROL_A_ETIQUETA):
        rotulo = fila_label(panel, etiqueta)
        control = clase(panel, choices=list(opciones), name=nombre) \
            if opciones else clase(panel, name=nombre)
        nombre_accesible(control, nombre_de_etiqueta(etiqueta))
        setattr(self, nombre, control)
        formulario.agregar_fila(vs, rotulo, control, hueco=hueco)

    def _boton(self, panel, etiqueta):
        boton = wx.Button(panel, label=etiqueta, name=nombre_de_etiqueta(etiqueta))
        nombre_accesible(boton, nombre_de_etiqueta(etiqueta))
        return boton

    def _enviar(self, _evento=None):
        plataforma = (plataformas.YOUTUBE, plataformas.TIKTOK)[
            self.cho_plataforma.GetSelection()]
        tipo = TIPOS[self.cho_tipo.GetSelection()]
        registro = ensayo.registro(
            self.txt_autor.GetValue().strip(), self.txt_mensaje.GetValue(),
            plataforma, tipo, self.txt_cantidad.GetValue().strip())
        self._frame.chat_vivo.encolar(registro)
        self.txt_mensaje.SetValue("")
        self.txt_mensaje.SetFocus()
        # Traductores: aviso después de enviar un mensaje de prueba.
        anunciar(_("Enviado a la prueba."))

    def _al_tecla(self, evento):
        if tecla_escape.es_escape(evento.GetKeyCode()):
            self._cerrar()
            return
        evento.Skip()

    def _cerrar(self, _evento=None):
        if self.cerrado:
            return
        self.cerrado = True
        terminar(self._frame)
        self.Destroy()
