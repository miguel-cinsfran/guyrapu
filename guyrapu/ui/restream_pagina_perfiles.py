# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pestaña Perfiles de Restream: los perfiles guardados de esta instalación.

Lista, crea, edita, cambia el nombre, duplica y elimina los perfiles. Cada
acción tiene su botón y su entrada en el menú contextual, con su tecla.
"""

from __future__ import annotations

from dataclasses import replace

import wx

from guyrapu.core.idioma import _
from guyrapu.obs import nombres_escena
from guyrapu.restream import perfiles, resumen_cuenta
from guyrapu.ui import confirmar
from guyrapu.ui.accesibilidad import anunciar, nombre_accesible
from guyrapu.ui.lista_acciones import Accion, ListaConAcciones
from guyrapu.ui.preferencias_comun import fila_horizontal, nombre_de_etiqueta
from guyrapu.ui.restream_perfil import (
    DialogoNombrePerfil,
    DialogoPerfilRestream,
)


class PaginaPerfiles(wx.Panel):

    def __init__(self, parent, ruta, obtener_canales, nombres_destinos=None,
                 destinos_leidos=None, esta_conectada=None):
        super().__init__(parent, name="PaginaPerfilesRestream")
        self._ruta = ruta
        self._obtener_canales = obtener_canales
        self._nombres_destinos = nombres_destinos
        self._destinos_leidos = destinos_leidos
        self._esta_conectada = esta_conectada
        self._perfiles = []
        self._crear_ui()
        self.poblar()

    def _crear_ui(self):
        vs = wx.BoxSizer(wx.VERTICAL)
        self.lista_perfiles = wx.ListBox(
            self, style=wx.LB_SINGLE | wx.LB_HSCROLL, name=_("Perfiles"))
        nombre_accesible(self.lista_perfiles, _("Perfiles"))
        etiquetas = self._etiquetas()
        self._lista_acciones = self._crear_lista_acciones(etiquetas)
        vs.Add(self.lista_perfiles, 1, wx.EXPAND | wx.ALL, 8)
        self._crear_botones(etiquetas)
        vs.Add(fila_horizontal(self._botones), 0, wx.ALL, 10)
        self.SetSizer(vs)

    def _etiquetas(self):
        return {
            "nuevo": _("Nuevo &perfil…"),
            "editar": _("&Editar…"),
            "renombrar": _("Cambiar &nombre…"),
            "duplicar": _("&Duplicar"),
            "eliminar": _("E&liminar"),
        }

    def _crear_lista_acciones(self, etiquetas):
        return ListaConAcciones(
            self.lista_perfiles,
            (
                Accion("nuevo", etiquetas["nuevo"], lambda: self.nuevo(),
                       necesita_elemento=False),
                Accion("editar", etiquetas["editar"], lambda: self.editar(),
                       tecla="intro"),
                Accion("renombrar", etiquetas["renombrar"],
                       lambda: self.renombrar(), tecla="f2"),
                Accion("duplicar", etiquetas["duplicar"],
                       lambda: self.duplicar(), tecla="ctrl+d"),
                Accion("eliminar", etiquetas["eliminar"],
                       lambda: self.eliminar(), tecla="suprimir"),
            ),
            _("No hay perfiles de Restream. Usa Nuevo perfil… para crear "
              "uno."))

    def _crear_botones(self, etiquetas):
        self.btn_nuevo = wx.Button(
            self, label=etiquetas["nuevo"], name=_("Nuevo perfil"))
        nombre_accesible(self.btn_nuevo, self.btn_nuevo.GetName())
        self.btn_nuevo.Bind(
            wx.EVT_BUTTON,
            lambda _evento: self._lista_acciones.ejecutar("nuevo"))
        self.btn_editar = self._boton(etiquetas["editar"], "editar")
        self.btn_renombrar = self._boton(etiquetas["renombrar"], "renombrar")
        self.btn_duplicar = self._boton(etiquetas["duplicar"], "duplicar")
        self.btn_eliminar = self._boton(etiquetas["eliminar"], "eliminar")
        self._botones = (self.btn_nuevo, self.btn_editar, self.btn_renombrar,
                         self.btn_duplicar, self.btn_eliminar)

    def _boton(self, etiqueta, clave):
        control = wx.Button(
            self, label=etiqueta, name=nombre_de_etiqueta(etiqueta))
        nombre_accesible(control, control.GetName())
        control.Bind(
            wx.EVT_BUTTON,
            lambda _evento: self._lista_acciones.ejecutar(clave))
        return control

    def cantidad(self):
        return len(self._perfiles)

    def _nombres(self):
        if self._nombres_destinos is None:
            return {}
        try:
            return dict(self._nombres_destinos())
        except Exception:
            return {}

    def _leidos(self):
        if self._destinos_leidos is None:
            return False
        try:
            return bool(self._destinos_leidos())
        except Exception:
            return False

    def _conectada(self):
        if self._esta_conectada is None:
            return True
        try:
            return bool(self._esta_conectada())
        except Exception:
            return False

    def _etiqueta(self, perfil):
        return resumen_cuenta.fila_perfil(
            perfil, self._nombres(), self._leidos())

    def poblar(self, indice=None):
        self._perfiles = perfiles.cargar(self._ruta)
        if self._perfiles:
            if indice is None:
                indice = 0
            indice = max(0, min(indice, len(self._perfiles) - 1))
        self._lista_acciones.fijar(
            [self._etiqueta(perfil) for perfil in self._perfiles], indice)

    def actualizar(self):
        indice = self.lista_perfiles.GetSelection()
        self.poblar(indice if indice >= 0 else None)

    def _indice_seleccionado(self):
        return self._lista_acciones.indice()

    def nuevo(self):
        perfil = self._pedir_perfil(None, self._perfiles)
        if perfil is None:
            return
        self._perfiles.append(perfil)
        perfiles.guardar(self._ruta, self._perfiles)
        self.poblar(len(self._perfiles) - 1)
        anunciar(_("Perfil de Restream guardado. Elígelo en Transmitir a, "
                   "al pulsar Transmitir en directo."))

    def editar(self):
        indice = self._indice_seleccionado()
        if indice is None:
            anunciar(_("Sin selección"))
            return
        actual = self._perfiles[indice]
        existentes = [perfil for posicion, perfil
                      in enumerate(self._perfiles) if posicion != indice]
        perfil = self._pedir_perfil(actual, existentes)
        if perfil is None:
            return
        self._perfiles[indice] = perfil
        perfiles.guardar(self._ruta, self._perfiles)
        self.poblar(indice)
        anunciar(_("Perfil de Restream guardado."))

    def renombrar(self):
        indice = self._indice_seleccionado()
        if indice is None:
            anunciar(_("Sin selección"))
            return
        actual = self._perfiles[indice]
        existentes = [perfil for posicion, perfil
                      in enumerate(self._perfiles) if posicion != indice]
        nombre = self._pedir_nombre(actual, existentes)
        if nombre is None:
            return
        self._perfiles[indice] = replace(actual, nombre=nombre)
        perfiles.guardar(self._ruta, self._perfiles)
        self.poblar(indice)
        self.lista_perfiles.SetFocus()
        anunciar(_("Nombre cambiado."))

    def duplicar(self):
        indice = self._indice_seleccionado()
        if indice is None:
            anunciar(_("Sin selección"))
            return
        actual = self._perfiles[indice]
        copia = replace(actual, nombre=self._nombre_copia(actual.nombre))
        self._perfiles.append(copia)
        perfiles.guardar(self._ruta, self._perfiles)
        self.poblar(len(self._perfiles) - 1)
        anunciar(_("Perfil de Restream duplicado."))

    def eliminar(self):
        indice = self._indice_seleccionado()
        if indice is None:
            anunciar(_("Sin selección"))
            return
        if not self.confirmar(self._perfiles[indice]):
            return
        del self._perfiles[indice]
        perfiles.guardar(self._ruta, self._perfiles)
        self.poblar(indice)
        self.lista_perfiles.SetFocus()
        anunciar(_("Perfil de Restream eliminado."))

    def confirmar(self, perfil):
        return confirmar.preguntar(
            self, _("¿Eliminar el perfil {nombre}?").format(
                nombre=perfil.nombre),
            _("Eliminar perfil"), _("&Eliminar"), _("&Cancelar"),
            predeterminado_si=False)

    def _nombre_copia(self, nombre):
        return nombres_escena.nombre_de_copia(
            nombre, {perfil.nombre for perfil in self._perfiles})

    def _pedir_perfil(self, perfil, existentes):
        canales = list(self._obtener_canales())
        if perfil is not None:
            perfil = perfiles.normalizar_youtube(perfil, canales)
        dialogo = DialogoPerfilRestream(
            self, perfil, perfiles.destinos_para_perfil(canales), existentes,
            sin_cuenta=not self._conectada())
        try:
            if dialogo.ShowModal() != wx.ID_OK:
                return None
            return dialogo.perfil()
        finally:
            dialogo.Destroy()

    def _pedir_nombre(self, actual, existentes):
        nombre = actual.nombre
        while True:
            dialogo = DialogoNombrePerfil(self, nombre)
            try:
                if dialogo.ShowModal() != wx.ID_OK:
                    return None
                nombre = dialogo.nombre()
            finally:
                dialogo.Destroy()
            mensajes = perfiles.validar(
                replace(actual, nombre=nombre), existentes)
            if not mensajes:
                return nombre
            anunciar(" ".join(mensajes))
