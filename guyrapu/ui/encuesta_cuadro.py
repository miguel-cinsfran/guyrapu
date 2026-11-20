# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Cuadro que edita una encuesta guardada.

Recoge los datos y valida: no guarda. La colección y el disco los maneja la
página de encuestas.
"""

from __future__ import annotations

import wx

from guyrapu.core import paths
from guyrapu.core.idioma import N_, _
from guyrapu.interaction import encuestas, encuestas_guardadas
from guyrapu.interaction import estilo_elegido
from guyrapu.obs import estilos_aviso
from guyrapu.ui import formulario, paleta, tecla_escape
from guyrapu.ui.accesibilidad import anunciar, nombre_accesible
from guyrapu.ui.preferencias_comun import fila_label, nombre_de_etiqueta

TITULO_AGREGAR = N_("Agregar encuesta")
TITULO_EDITAR = N_("Editar encuesta")

DURACIONES = (
    (30, N_("30 segundos")),
    (60, N_("1 minuto")),
    (120, N_("2 minutos")),
    (180, N_("3 minutos")),
    (300, N_("5 minutos")),
    (600, N_("10 minutos")),
    (900, N_("15 minutos")),
    (1800, N_("30 minutos")),
)

DESTINOS = (
    ("video", N_("Vídeo")),
    ("chat", N_("Chat de YouTube")),
    ("ambos", N_("Vídeo y chat de YouTube")),
)


class DialogoEncuesta(wx.Dialog):
    """Pregunta, respuestas, duración, destino y estilo de una encuesta."""

    def __init__(self, padre, datos):
        super().__init__(
            padre,
            title=_(TITULO_EDITAR if datos else TITULO_AGREGAR),
            name="DialogoEncuesta")
        self._usuario = estilos_aviso.cargar_estilos(paths.estilos_avisos())
        self._por_tipo = estilos_aviso.cargar_por_tipo(paths.estilos_avisos())
        self._estilos = estilos_aviso.todos(self._usuario)
        self._crear_controles(datos)
        self.Bind(wx.EVT_CHAR_HOOK, self._al_tecla)
        self.Fit()
        self.Centre()
        paleta.pintar_ventana(self)
        self.txt_pregunta.SetFocus()

    def _crear_controles(self, datos):
        panel = wx.Panel(self, name="PanelEncuesta")
        vs = wx.BoxSizer(wx.VERTICAL)
        rotulo = fila_label(panel, _("&Pregunta:"))
        self.txt_pregunta = self._campo(panel, "&Pregunta:")
        formulario.agregar_fila(vs, rotulo, self.txt_pregunta)
        rotulo = fila_label(panel, _("&Respuestas, una por línea:"))
        self.txt_respuestas = wx.TextCtrl(
            panel, style=wx.TE_MULTILINE,
            name=nombre_de_etiqueta(_("&Respuestas, una por línea:")))
        nombre_accesible(self.txt_respuestas, self.txt_respuestas.GetName())
        self.txt_respuestas.SetMinSize((-1, 120))
        formulario.agregar_fila(vs, rotulo, self.txt_respuestas)
        rotulo = fila_label(panel, _("&Duración:"))
        self.cho_duracion = wx.Choice(
            panel, choices=[_(texto) for _segundos, texto in DURACIONES],
            name=nombre_de_etiqueta(_("&Duración:")))
        nombre_accesible(self.cho_duracion, self.cho_duracion.GetName())
        formulario.agregar_fila(vs, rotulo, self.cho_duracion)
        rotulo = fila_label(panel, _("&Mostrar resultado en:"))
        self.cho_destino = wx.Choice(
            panel, choices=[_(texto) for _clave, texto in DESTINOS],
            name=nombre_de_etiqueta(_("&Mostrar resultado en:")))
        nombre_accesible(self.cho_destino, self.cho_destino.GetName())
        formulario.agregar_fila(vs, rotulo, self.cho_destino)
        rotulo = fila_label(panel, _("&Estilo:"))
        self.cho_estilo = wx.Choice(
            panel, choices=estilo_elegido.opciones(
                self._usuario, self._por_tipo, "encuesta"),
            name=nombre_de_etiqueta(_("&Estilo:")))
        nombre_accesible(self.cho_estilo, self.cho_estilo.GetName())
        formulario.agregar_fila(vs, rotulo, self.cho_estilo)
        formulario.agregar_pie(vs, self._botones(panel))
        formulario.ajustar_tamano(self, panel, vs)
        self._cargar(datos)

    def _campo(self, panel, etiqueta):
        campo = wx.TextCtrl(panel, name=nombre_de_etiqueta(_(etiqueta)))
        nombre_accesible(campo, nombre_de_etiqueta(_(etiqueta)))
        return campo

    def _botones(self, panel):
        self.btn_aceptar = wx.Button(panel, wx.ID_OK, _("&Aceptar"),
                                     name=_("Aceptar"))
        self.btn_cancelar = wx.Button(
            panel, wx.ID_CANCEL, _("&Cancelar"), name=_("Cancelar"))
        self.btn_aceptar.SetDefault()
        self.btn_aceptar.Bind(wx.EVT_BUTTON, self._aceptar)
        self.btn_cancelar.Bind(
            wx.EVT_BUTTON, lambda _evento: self.EndModal(wx.ID_CANCEL))
        return [self.btn_aceptar, self.btn_cancelar]

    def _cargar(self, datos):
        encuesta = encuestas_guardadas.normalizar(datos or {})
        self.txt_pregunta.SetValue(encuesta["pregunta"])
        self.txt_respuestas.SetValue("\n".join(encuesta["opciones"]))
        self.cho_duracion.SetSelection(
            next((indice for indice, (segundos, _texto) in enumerate(DURACIONES)
                  if segundos == encuesta["segundos"]), 2))
        self.cho_destino.SetSelection(
            next((indice for indice, (clave, _texto) in enumerate(DESTINOS)
                  if clave == encuesta["destino"]), 0))
        self._elegir_estilo(encuesta["estilo"] if datos else "")

    def _elegir_estilo(self, clave):
        self.cho_estilo.SetSelection(
            estilo_elegido.indice_de(clave, self._estilos))

    def _datos_de_campos(self):
        return {
            "pregunta": self.txt_pregunta.GetValue(),
            "opciones": [linea.strip() for linea in
                         self.txt_respuestas.GetValue().splitlines()
                         if linea.strip()],
            "segundos": DURACIONES[self.cho_duracion.GetSelection()][0],
            "destino": DESTINOS[self.cho_destino.GetSelection()][0],
            "estilo": estilo_elegido.clave_de(
                self.cho_estilo.GetSelection(), self._estilos),
        }

    def _aceptar(self, _evento):
        datos = self._datos_de_campos()
        error = encuestas.validar_encuesta(datos["pregunta"], datos["opciones"])
        if error:
            anunciar(error)
            self._campo_del_error(datos).SetFocus()
            return
        self.EndModal(wx.ID_OK)

    def _campo_del_error(self, datos):
        if not (datos["pregunta"] or "").strip():
            return self.txt_pregunta
        return self.txt_respuestas

    def datos(self) -> dict:
        """La encuesta tal como se guarda."""
        return self._datos_de_campos()

    def _al_tecla(self, evento):
        tecla_escape.cancelar_si_escape(self, evento)


def abrir(padre, datos=None):
    """Abre el cuadro y devuelve los datos de la encuesta, o None."""
    dialogo = DialogoEncuesta(padre, datos or {})
    try:
        if dialogo.ShowModal() != wx.ID_OK:
            return None
        return dialogo.datos()
    finally:
        dialogo.Destroy()
