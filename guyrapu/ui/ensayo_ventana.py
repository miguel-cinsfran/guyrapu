# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""La ventana Prueba sin directo y el final del ensayo.

Los mensajes se arman con `ensayo.registro` y entran por `chat_vivo.encolar`,
el mismo reparto que un mensaje del directo. No se toca la captura ni la voz.
"""

from __future__ import annotations

import wx

from guyrapu.core import plataformas
from guyrapu.core.idioma import N_, _
from guyrapu.interaction import ensayo, informe_ensayo
from guyrapu.ui import (
    ayuda_manual, encuesta_en_vivo, formulario, gui_envio_chat,
    lista_acciones, preguntas_en_vivo, tecla_escape)
from guyrapu.ui.accesibilidad import anunciar, nombre_accesible
from guyrapu.ui.paleta import pintar_ventana
from guyrapu.ui.preferencias_comun import fila_label, nombre_de_etiqueta
from guyrapu.voice import sound_player as _snd

# Traductores: única fila de Resultados sin resultados; dice qué aparece y cómo se llena.
VACIO_RESULTADOS = N_(
    "No hay resultados. Aquí aparece lo que respondió a cada mensaje de prueba. "
    "Escribe un mensaje y usa Enviar.")


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
    """Los campos del tipo elegido, sus resultados y sus botones."""

    def __init__(self, frame):
        super().__init__(
            frame, title=_("Prueba sin directo"), name=_("Prueba sin directo"),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self._frame = frame
        self.cerrado = False
        self._resultados = []
        self._crear_controles()
        self._actualizar_tipos()
        self.Bind(wx.EVT_CHAR_HOOK, self._al_tecla)
        self.Bind(wx.EVT_CLOSE, self._cerrar)
        pintar_ventana(self)
        self.Centre()
        self.txt_mensaje.SetFocus()

    def _crear_controles(self):
        panel = wx.Panel(self, name="PanelEnsayo")
        vs = wx.BoxSizer(wx.VERTICAL)
        self._rotulos = {}
        self._agregar(vs, panel, _("P&lataforma:"), "cho_plataforma", wx.Choice,
                      opciones=[plataformas.nombre(plataformas.YOUTUBE),
                                plataformas.nombre(plataformas.TIKTOK)])
        self.cho_plataforma.SetSelection(0)
        self.cho_plataforma.Bind(wx.EVT_CHOICE, self._al_cambiar_plataforma)
        self._agregar(vs, panel, _("&Tipo:"), "cho_tipo", wx.Choice)
        self.cho_tipo.Bind(wx.EVT_CHOICE, self._al_cambiar_tipo)
        self._agregar(vs, panel, _("&Rol:"), "cho_rol", wx.Choice,
                      opciones=[_(rotulo) for rotulo, _valor in ensayo.ROLES])
        self._agregar(vs, panel, _("&Autor:"), "txt_autor", wx.TextCtrl)
        self.txt_autor.SetValue(_(ensayo.AUTOR_PREDETERMINADO))
        self._campos = {}
        for rotulo, nombre in (
                (_("&Nombre del regalo:"), "txt_regalo"),
                (_("Canti&dad:"), "txt_cantidad"),
                (_("M&ensaje:"), "txt_mensaje")):
            self._agregar(vs, panel, rotulo, nombre, wx.TextCtrl)
            self._campos[nombre.removeprefix("txt_")] = getattr(self, nombre)
        self.btn_enviar = self._boton(panel, _("En&viar"))
        self.btn_enviar.SetDefault()
        self.btn_enviar.Bind(wx.EVT_BUTTON, self._enviar)
        self.btn_cerrar = self._boton(panel, _("&Cerrar"))
        self.btn_cerrar.Bind(wx.EVT_BUTTON, self._cerrar)
        formulario.agregar_pie(vs, [self.btn_enviar, self.btn_cerrar])
        self._agregar(vs, panel, _("Res&ultados:"), "lista_resultados",
                      wx.ListBox)
        vs.GetChildren()[-1].SetProportion(1)
        self.lista_resultados.SetMinSize((-1, 110))
        self._vacia = lista_acciones.ListaConVacio(
            self.lista_resultados, _(VACIO_RESULTADOS))
        self._vacia.fijar([])
        formulario.ajustar_tamano(self, panel, vs)

    def _agregar(self, vs, panel, etiqueta, nombre, clase, opciones=()):
        rotulo = fila_label(panel, etiqueta)
        control = clase(panel, choices=list(opciones), name=nombre) \
            if opciones else clase(panel, name=nombre)
        nombre_accesible(control, nombre_de_etiqueta(etiqueta))
        setattr(self, nombre, control)
        self._rotulos[nombre] = rotulo
        formulario.agregar_fila(vs, rotulo, control)

    def _boton(self, panel, etiqueta):
        boton = wx.Button(panel, label=etiqueta, name=nombre_de_etiqueta(etiqueta))
        nombre_accesible(boton, nombre_de_etiqueta(etiqueta))
        return boton

    def _plataforma(self):
        return (plataformas.YOUTUBE, plataformas.TIKTOK)[
            self.cho_plataforma.GetSelection()]

    def _tipo(self):
        return ensayo.tipos_de(self._plataforma())[self.cho_tipo.GetSelection()]

    def _rol(self):
        indice = self.cho_rol.GetSelection()
        return ensayo.ROLES[max(indice, 0)][1]

    def _al_cambiar_plataforma(self, _evento):
        self._actualizar_tipos()

    def _al_cambiar_tipo(self, _evento):
        self._actualizar_campos()

    def _actualizar_tipos(self):
        tipos = ensayo.tipos_de(self._plataforma())
        self.cho_tipo.SetItems([_(tipo.rotulo) for tipo in tipos])
        self.cho_tipo.SetSelection(0)
        self.cho_rol.SetSelection(0)
        self._actualizar_campos()

    def _actualizar_campos(self):
        visibles = set(self._tipo().campos)
        for nombre, control in self._campos.items():
            control.Show(nombre in visibles)
            self._rotulos["txt_" + nombre].Show(nombre in visibles)
        con_rol = ensayo.con_rol(self._plataforma())
        self.cho_rol.Show(con_rol)
        self._rotulos["cho_rol"].Show(con_rol)
        self.GetChildren()[0].Layout()

    def _enviar(self, _evento=None):
        registro = ensayo.registro(
            self.txt_autor.GetValue().strip(), self.txt_mensaje.GetValue(),
            self._plataforma(), self._tipo().clave,
            self.txt_cantidad.GetValue().strip(), rol=self._rol(),
            regalo=self.txt_regalo.GetValue().strip())
        self._frame.chat_vivo.encolar(registro)
        self.txt_mensaje.SetValue("")
        self.txt_mensaje.SetFocus()

    def agregar_resultado(self, registro, texto):
        """Escribe un resultado al final de la lista, con hora y mensaje."""
        enviado = registro.texto or registro.autor
        self._resultados.append(
            informe_ensayo.fila(registro.hora, enviado, texto))
        self._vacia.fijar(self._resultados)

    def _al_tecla(self, evento):
        if ayuda_manual.atender_f1(self, evento, "ensayo"):
            return
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
