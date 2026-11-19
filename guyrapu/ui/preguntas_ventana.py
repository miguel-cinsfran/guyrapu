# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""La cola de preguntas del público y sus acciones.

El panel vive en la ventana Interacción. Se pone al día solo cuando la cola
cambia, aunque el aviso venga del hilo de la captura.
"""

from __future__ import annotations

import wx

from guyrapu.core import plataformas
from guyrapu.core.idioma import N_, _
from guyrapu.ui import confirmar, preguntas_en_vivo
from guyrapu.ui.accesibilidad import anunciar, nombre_accesible
from guyrapu.ui.lista_acciones import Accion, ListaConAcciones
from guyrapu.ui.preferencias_comun import fila_label, nombre_de_etiqueta

VACIO = N_(
    "No hay preguntas. El público las hace con el comando pregunta y el texto.")


def _fila(pregunta):
    """Autor, plataforma y texto de una pregunta, en ese orden."""
    return _("{autor}, {plataforma}: {texto}").format(
        autor=pregunta.autor,
        plataforma=plataformas.nombre(pregunta.plataforma)
        or pregunta.plataforma,
        texto=pregunta.texto)


def _acciones(panel):
    return (
        Accion("mostrar", _("&Mostrar en el vídeo"), panel._mostrar,
               tecla="intro", motivo=panel._motivo_video),
        Accion("responder", _("Marcar como &respondida"), panel._responder),
        Accion("eliminar", _("E&liminar"), panel._eliminar,
               tecla="suprimir"),
        Accion("vaciar", _("&Vaciar cola"), panel._vaciar,
               necesita_elemento=False),
    )


class PanelPreguntas(wx.Panel):
    """La cola de preguntas con sus botones y sus acciones."""

    def __init__(self, padre, frame):
        super().__init__(padre, name="PanelPreguntas")
        self._frame = frame
        self._preguntas = preguntas_en_vivo.pendientes(frame)
        self._vivo = True
        self._crear_controles()
        preguntas_en_vivo.suscribir(frame, self._al_cambiar)
        self.Bind(wx.EVT_WINDOW_DESTROY, self._al_destruir)

    def _crear_controles(self):
        vs = wx.BoxSizer(wx.VERTICAL)
        vs.Add(fila_label(self, _("&Preguntas:")), 0,
               wx.LEFT | wx.RIGHT | wx.TOP, 10)
        self.lista = wx.ListBox(
            self, style=wx.LB_SINGLE | wx.LB_HSCROLL, name="ListaPreguntas")
        nombre_accesible(self.lista, _("Preguntas del público"))
        self._acciones = _acciones(self)
        self._lista = ListaConAcciones(self.lista, self._acciones, _(VACIO))
        self._lista.fijar(self._textos())
        vs.Add(self.lista, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        vs.Add(self._fila_de_botones(), 0,
               wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        self.SetSizer(vs)
        self.lista.SetFocus()

    def _fila_de_botones(self):
        fila = wx.WrapSizer(wx.HORIZONTAL, flags=0)
        for accion in self._acciones:
            boton = wx.Button(self, label=accion.etiqueta,
                              name=nombre_de_etiqueta(accion.etiqueta))
            boton.Bind(wx.EVT_BUTTON,
                       lambda _evento, clave=accion.clave:
                       self._lista.ejecutar(clave))
            fila.Add(boton, 0, wx.RIGHT | wx.BOTTOM, 6)
        return fila

    def _textos(self):
        return [_fila(pregunta) for pregunta in self._preguntas]

    def _elegida(self):
        indice = self._lista.indice()
        if indice is None:
            return None
        return self._preguntas[indice]

    def _al_cambiar(self):
        if not self._vivo:
            return
        try:
            wx.CallAfter(self._poner_al_dia)
        except RuntimeError:
            pass

    def _poner_al_dia(self):
        if not self._vivo:
            return
        elegida = self._elegida()
        self._preguntas = preguntas_en_vivo.pendientes(self._frame)
        self._lista.poner_al_dia(
            [pregunta.id for pregunta in self._preguntas],
            self._textos(),
            None if elegida is None else elegida.id)

    def _al_destruir(self, evento):
        self._vivo = False
        preguntas_en_vivo.desuscribir(self._frame, self._al_cambiar)
        evento.Skip()

    def _motivo_video(self):
        from guyrapu.ui import gui_envio_chat
        if "video" in gui_envio_chat.destinos_disponibles(self._frame):
            return ""
        return _("Sin conexión con OBS")

    def _mostrar(self):
        pregunta = self._elegida()
        if pregunta is None:
            return
        if preguntas_en_vivo.mostrar(self._frame, pregunta.id):
            anunciar(_("Pregunta en el vídeo"))

    def _responder(self):
        pregunta = self._elegida()
        if pregunta is None:
            return
        if preguntas_en_vivo.responder(self._frame, pregunta.id):
            anunciar(_("Pregunta respondida"))

    def _eliminar(self):
        pregunta = self._elegida()
        if pregunta is None:
            return
        if preguntas_en_vivo.descartar(self._frame, pregunta.id):
            anunciar(_("Pregunta eliminada"))

    def _vaciar(self):
        if not confirmar.preguntar(
                self,
                _("¿Quieres vaciar la cola de preguntas?"),
                _("Vaciar cola de preguntas"), _("&Vaciar"), _("&Cancelar"),
                predeterminado_si=False):
            return
        preguntas_en_vivo.vaciar(self._frame)
        anunciar(_("Cola de preguntas vaciada"))
