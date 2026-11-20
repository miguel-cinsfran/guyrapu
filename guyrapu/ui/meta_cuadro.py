# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Cuadro que edita una meta y el que cambia solo su nombre.

Recoge los datos y valida: no guarda. La colección y el disco los maneja la
ventana de metas.
"""

from __future__ import annotations

import wx

from guyrapu.core import paths
from guyrapu.core.idioma import N_, _
from guyrapu.interaction import estilo_elegido, medios_guardados, metas
from guyrapu.interaction import metas_guardadas
from guyrapu.interaction.texto import normalizar
from guyrapu.obs import estilos_aviso
from guyrapu.ui import formulario, paleta, tecla_escape
from guyrapu.ui.accesibilidad import ContadorAccesible, anunciar, nombre_accesible
from guyrapu.ui.preferencias_comun import fila_label, nombre_de_etiqueta

TITULO_AGREGAR = N_("Agregar meta")
TITULO_EDITAR = N_("Editar meta")
OBJETIVO_MAXIMO = 1000000


def _que_cuenta():
    return [_(metas.NOMBRES_QUE_CUENTA[clave]) for clave in metas.QUE_CUENTA]


def _medios():
    return medios_guardados.cargar(paths.medios())


class DialogoMeta(wx.Dialog):
    """Nombre, qué cuenta, objetivo, estilo y festejo de una meta."""

    def __init__(self, padre, datos, otros):
        super().__init__(
            padre,
            title=_(TITULO_EDITAR if datos else TITULO_AGREGAR),
            name="DialogoMeta")
        self._otros = [metas_guardadas.a_meta(otro) for otro in otros]
        self._usuario = estilos_aviso.cargar_estilos(paths.estilos_avisos())
        self._por_tipo = estilos_aviso.cargar_por_tipo(paths.estilos_avisos())
        self._estilos = estilos_aviso.todos(self._usuario)
        self._medios = _medios()
        self._crear_controles(datos)
        self.Bind(wx.EVT_CHAR_HOOK, self._al_tecla)
        self.Fit()
        self.Centre()
        paleta.pintar_ventana(self)
        self.txt_nombre.SetFocus()

    def _crear_controles(self, datos):
        panel = wx.Panel(self, name="PanelMeta")
        vs = wx.BoxSizer(wx.VERTICAL)
        rotulo = fila_label(panel, _("&Nombre:"))
        self.txt_nombre = self._campo(panel, _("&Nombre:"))
        formulario.agregar_fila(vs, rotulo, self.txt_nombre)
        rotulo = fila_label(panel, _("&Tipo:"))
        self.cho_que_cuenta = self._eleccion(
            panel, _("&Tipo:"), _que_cuenta())
        formulario.agregar_fila(vs, rotulo, self.cho_que_cuenta)
        rotulo = fila_label(panel, _("&Objetivo:"))
        self.sp_objetivo = self._contador(
            panel, _("&Objetivo:"), 0, OBJETIVO_MAXIMO, 1)
        formulario.agregar_fila(vs, rotulo, self.sp_objetivo, numerico=True)
        rotulo = fila_label(panel, _("Esti&lo:"))
        self.cho_estilo = self._eleccion(
            panel, _("Esti&lo:"), estilo_elegido.opciones(
                self._usuario, self._por_tipo, "meta"))
        formulario.agregar_fila(vs, rotulo, self.cho_estilo)
        rotulo = fila_label(panel, _("&Festejo:"))
        self.cho_festejo = self._eleccion(
            panel, _("&Festejo:"), [_("Ninguno")] + self._nombres_de_medios())
        formulario.agregar_fila(vs, rotulo, self.cho_festejo)
        etiqueta = _("Mostrar a&vance en el vídeo")
        self.chk_en_video = wx.CheckBox(
            panel, label=etiqueta, name=nombre_de_etiqueta(etiqueta))
        nombre_accesible(self.chk_en_video, self.chk_en_video.GetName())
        formulario.agregar_casillas(vs, (self.chk_en_video,))
        formulario.agregar_pie(vs, self._botones(panel))
        formulario.ajustar_tamano(self, panel, vs)
        self._cargar(datos)

    def _nombres_de_medios(self):
        return [str(medio.get("nombre", "")) for medio in self._medios]

    def _campo(self, panel, etiqueta):
        campo = wx.TextCtrl(panel, name=nombre_de_etiqueta(etiqueta))
        nombre_accesible(campo, nombre_de_etiqueta(etiqueta))
        return campo

    def _eleccion(self, panel, etiqueta, opciones):
        eleccion = wx.Choice(
            panel, choices=opciones, name=nombre_de_etiqueta(etiqueta))
        nombre_accesible(eleccion, eleccion.GetName())
        return eleccion

    def _contador(self, panel, etiqueta, minimo, maximo, inicial):
        nombre = nombre_de_etiqueta(etiqueta)
        control = ContadorAccesible(
            panel, min=minimo, max=maximo, initial=inicial, name=nombre)
        nombre_accesible(control, nombre)
        return control

    def _botones(self, panel):
        self.btn_aceptar = wx.Button(
            panel, wx.ID_OK, _("&Aceptar"), name=_("Aceptar"))
        self.btn_cancelar = wx.Button(
            panel, wx.ID_CANCEL, _("&Cancelar"), name=_("Cancelar"))
        self.btn_aceptar.SetDefault()
        self.btn_aceptar.Bind(wx.EVT_BUTTON, self._aceptar)
        self.btn_cancelar.Bind(
            wx.EVT_BUTTON, lambda _evento: self.EndModal(wx.ID_CANCEL))
        return [self.btn_aceptar, self.btn_cancelar]

    def _cargar(self, datos):
        meta = metas_guardadas.a_meta(datos or {})
        self._activa = meta.activa
        self.txt_nombre.SetValue(meta.nombre)
        self.cho_que_cuenta.SetSelection(
            metas.QUE_CUENTA.index(meta.que_cuenta))
        self.sp_objetivo.SetValue(meta.objetivo)
        self._elegir_festejo(meta.festejo)
        self._elegir_estilo(meta.estilo if datos else "")
        self.chk_en_video.SetValue(meta.en_video)

    def _elegir_festejo(self, nombre):
        nombres = self._nombres_de_medios()
        try:
            indice = nombres.index(nombre) + 1
        except ValueError:
            indice = 0
        self.cho_festejo.SetSelection(indice)

    def _elegir_estilo(self, clave):
        self.cho_estilo.SetSelection(
            estilo_elegido.indice_de(clave, self._estilos))

    def _festejo_elegido(self):
        indice = self.cho_festejo.GetSelection()
        if indice <= 0:
            return ""
        return self._nombres_de_medios()[indice - 1]

    def _meta_de_campos(self):
        return metas.Meta(
            nombre=self.txt_nombre.GetValue(),
            que_cuenta=metas.QUE_CUENTA[self.cho_que_cuenta.GetSelection()],
            objetivo=self.sp_objetivo.GetValue(),
            estilo=estilo_elegido.clave_de(
                self.cho_estilo.GetSelection(), self._estilos),
            festejo=self._festejo_elegido(),
            activa=self._activa,
            en_video=self.chk_en_video.GetValue(),
        )

    def _aceptar(self, _evento):
        meta = self._meta_de_campos()
        error = metas.validar(meta, self._otros)
        if error:
            anunciar(error)
            self._campo_del_error(meta).SetFocus()
            return
        self.EndModal(wx.ID_OK)

    def _campo_del_error(self, meta):
        if not normalizar(meta.nombre):
            return self.txt_nombre
        if any(normalizar(otra.nombre) == normalizar(meta.nombre)
               for otra in self._otros):
            return self.txt_nombre
        if (isinstance(meta.objetivo, bool)
                or not isinstance(meta.objetivo, int)
                or meta.objetivo <= 0):
            return self.sp_objetivo
        return self.txt_nombre

    def datos(self) -> dict:
        """La meta tal como se guarda."""
        return metas_guardadas.desde_meta(self._meta_de_campos())

    def _al_tecla(self, evento):
        tecla_escape.cancelar_si_escape(self, evento)


class DialogoNombre(wx.Dialog):
    """Pide un nombre, sin validarlo: el bucle de la ventana lo repite."""

    def __init__(self, padre, nombre):
        super().__init__(padre, title=_("Cambiar nombre"),
                         name="DialogoNombreMeta")
        panel = wx.Panel(self, name="PanelNombreMeta")
        caja = wx.BoxSizer(wx.VERTICAL)
        rotulo = fila_label(panel, _("&Nombre:"))
        self.txt_nombre = wx.TextCtrl(
            panel, name=nombre_de_etiqueta(_("&Nombre:")))
        nombre_accesible(self.txt_nombre, self.txt_nombre.GetName())
        self.txt_nombre.SetValue(nombre)
        formulario.agregar_fila(caja, rotulo, self.txt_nombre)
        self.btn_aceptar = wx.Button(
            panel, wx.ID_OK, _("&Aceptar"), name=_("Aceptar"))
        self.btn_cancelar = wx.Button(
            panel, wx.ID_CANCEL, _("&Cancelar"), name=_("Cancelar"))
        self.btn_aceptar.SetDefault()
        formulario.agregar_pie(caja, [self.btn_aceptar, self.btn_cancelar])
        formulario.ajustar_tamano(self, panel, caja)
        self.Centre()
        paleta.pintar_ventana(self)
        self.Bind(wx.EVT_CHAR_HOOK, self._al_tecla)
        self.txt_nombre.SetFocus()

    def nombre(self) -> str:
        return self.txt_nombre.GetValue().strip()

    def _al_tecla(self, evento):
        tecla_escape.cancelar_si_escape(self, evento)


def abrir(padre, datos=None, otros=()):
    """Abre el cuadro y devuelve los datos de la meta, o None."""
    dialogo = DialogoMeta(padre, datos or {}, otros)
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
