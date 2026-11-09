# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pestaña Perfiles del panel de OBS: ver, usar y administrar los perfiles.

Cada acción corre en un hilo con `operaciones.en_hilo`, como las demás
pestañas: OBS se consulta fuera del hilo de la interfaz. La lógica de
`perfiles_obs` es la que crea, duplica, elimina y guarda.
"""

from __future__ import annotations

import wx

from guyrapu.core.idioma import _
from guyrapu.obs import codificadores_obs, obs_cliente, perfiles_obs
from guyrapu.obs import salidas_audio
from guyrapu.obs import usos_perfil
from guyrapu.ui import confirmar
from guyrapu.ui.accesibilidad import anunciar, nombre_accesible
from guyrapu.ui.dialogo_ajustes_perfil import DialogoAjustesPerfil
from guyrapu.ui.dialogo_asistente_perfiles import AsistentePerfilesPanel
from guyrapu.ui.dialogo_nombre_perfil_obs import DialogoNombrePerfil
from guyrapu.ui.dialogo_usos_perfil import DialogoUsosPerfil
from guyrapu.ui.lista_acciones import Accion, ListaConAcciones
from guyrapu.ui.preferencias_comun import (
    fila_horizontal,
    nombre_de_etiqueta,
)


class PaginaPerfiles(wx.Panel):

    def __init__(self, parent, principal, gestor, operaciones):
        super().__init__(parent, name="PaginaPerfilesObs")
        self._principal = principal
        self._config = principal._config
        self._gestor = gestor
        self._operaciones = operaciones
        self._perfiles = []
        self._actual = ""
        self._foco_pendiente = None
        self._crear_controles()
        self.acciones = (self.lista, self.btn_usar, self.btn_usar_para,
                         self.btn_nuevo, self.btn_duplicar, self.btn_eliminar,
                         self.btn_editar, self.btn_preparar)

    def _crear_controles(self):
        caja = wx.BoxSizer(wx.VERTICAL)
        self.lista = wx.ListBox(
            self, style=wx.LB_SINGLE | wx.LB_HSCROLL,
            name=_("Perfiles de OBS"))
        nombre_accesible(self.lista, _("Perfiles de OBS"))
        caja.Add(self.lista, 1, wx.EXPAND | wx.ALL, 8)
        etiquetas = self._etiquetas()
        self._crear_lista_acciones(etiquetas)
        self._crear_botones(etiquetas)
        caja.Add(fila_horizontal((self.btn_usar, self.btn_usar_para,
                                  self.btn_nuevo, self.btn_duplicar,
                                  self.btn_eliminar, self.btn_editar,
                                  self.btn_preparar)),
                 0, wx.ALL, 6)
        self.SetSizer(caja)

    def _etiquetas(self):
        return {
            "usar": _("&Usar este perfil"),
            "usar_para": _("Usar p&ara…"),
            "nuevo": _("&Nuevo…"),
            "duplicar": _("&Duplicar…"),
            "eliminar": _("&Eliminar perfil"),
            "editar": _("Editar a&justes…"),
            "preparar": _("&Preparar perfiles…"),
        }

    def _crear_lista_acciones(self, etiquetas):
        self._lista_acciones = ListaConAcciones(
            self.lista,
            (
                Accion("usar", etiquetas["usar"], self.usar),
                Accion("usar_para", etiquetas["usar_para"], self.usar_para),
                Accion("nuevo", etiquetas["nuevo"], self.nuevo,
                       necesita_elemento=False),
                Accion("duplicar", etiquetas["duplicar"], self.duplicar),
                Accion("eliminar", etiquetas["eliminar"], self.eliminar,
                       tecla="suprimir"),
                Accion("editar", etiquetas["editar"], self.editar,
                       tecla="intro"),
                Accion("preparar", etiquetas["preparar"],
                       self.preparar_perfiles, necesita_elemento=False),
            ),
            _("No hay perfiles en OBS. Usa Nuevo… para crear uno."))

    def _crear_botones(self, etiquetas):
        self.btn_usar = self._boton(
            etiquetas["usar"], etiquetas["usar"], "usar")
        self.btn_usar_para = self._boton(
            etiquetas["usar_para"], _("Usar para…"), "usar_para")
        self.btn_nuevo = self._boton(
            etiquetas["nuevo"], etiquetas["nuevo"], "nuevo")
        self.btn_duplicar = self._boton(
            etiquetas["duplicar"], etiquetas["duplicar"], "duplicar")
        self.btn_eliminar = self._boton(
            etiquetas["eliminar"], etiquetas["eliminar"], "eliminar")
        self.btn_editar = self._boton(
            etiquetas["editar"], etiquetas["editar"], "editar")
        self.btn_preparar = self._boton(
            etiquetas["preparar"], _("Preparar perfiles…"), "preparar")

    def _boton(self, etiqueta, nombre, clave):
        control = wx.Button(self, label=etiqueta,
                            name=nombre_de_etiqueta(nombre))
        nombre_accesible(control, control.GetName())
        control.Bind(
            wx.EVT_BUTTON,
            lambda _evento: self._lista_acciones.ejecutar(clave))
        return control

    def _cliente(self):
        cliente = getattr(self._gestor, "_cliente", None)
        if cliente is None:
            raise obs_cliente.ObsError(_("OBS no está disponible."))
        return cliente

    def _etiqueta(self, nombre):
        usos = usos_perfil.usos_de(nombre, self._config)
        return usos_perfil.etiqueta_fila(nombre, nombre == self._actual, usos)

    def fijar(self, perfiles, actual, foco=None):
        """Pone la lista que se leyó de OBS y elige el perfil afectado."""
        self._perfiles = list(perfiles)
        self._actual = actual or ""
        indice = self._indice(foco)
        if indice is None:
            indice = self._indice(self._actual)
        self._lista_acciones.fijar(
            [self._etiqueta(nombre) for nombre in self._perfiles], indice)
        if foco is not None:
            self.lista.SetFocus()

    def _indice(self, nombre):
        if nombre in self._perfiles:
            return self._perfiles.index(nombre)
        return None

    def _elegido(self):
        indice = self._lista_acciones.indice()
        if indice is None:
            return ""
        return self._perfiles[indice]

    def _sin_seleccion(self):
        anunciar(_("Sin selección"))

    def releer(self):
        self._recargar()

    def _recargar(self, foco=None):
        self._foco_pendiente = foco
        self._operaciones.en_hilo(self._leer_lista, self._lista_leida)

    def _leer_lista(self):
        return perfiles_obs.listar_perfiles(self._cliente())

    def _lista_leida(self, datos):
        foco = self._foco_pendiente
        self._foco_pendiente = None
        self.fijar(datos[0], datos[1], foco)

    def _hecho(self, texto, foco=None):
        anunciar(texto)
        self._recargar(foco)

    def usar(self):
        nombre = self._elegido()
        if not nombre:
            return self._sin_seleccion()
        self._operaciones.en_hilo(
            lambda: perfiles_obs.cambiar_perfil(self._cliente(), nombre),
            lambda _resultado: self._hecho(
                _("Perfil en uso: {nombre}.").format(nombre=nombre), nombre))

    def usar_para(self):
        nombre = self._elegido()
        if not nombre:
            return self._sin_seleccion()
        cambios = self._pedir_usos(nombre)
        if cambios is None:
            return
        if not cambios:
            anunciar(_("Sin cambios."))
            return
        self._guardar_cambios(cambios)
        self._hecho(self._resultado_usos(nombre), nombre)

    def _pedir_usos(self, nombre):
        dialogo = DialogoUsosPerfil(self, nombre, self._config)
        try:
            if dialogo.ShowModal() != wx.ID_OK:
                return None
            return usos_perfil.cambios(
                nombre, dialogo.marcados(), self._config)
        finally:
            dialogo.Destroy()

    def _guardar_cambios(self, cambios):
        from guyrapu.ui import gui

        for clave, valor in cambios:
            self._config[clave] = valor
            gui.guardar_opcion(gui.RUTA_CONFIG, usos_perfil.SECCION,
                               clave, valor)

    def _resultado_usos(self, nombre):
        usos = usos_perfil.usos_de(nombre, self._config)
        if not usos:
            return _("{nombre} ya no tiene usos asignados.").format(
                nombre=nombre)
        return _("{nombre}: {usos}.").format(
            nombre=nombre, usos=usos_perfil.texto_para(usos))

    def nuevo(self):
        datos = self._pedir_nombre(
            _("Nuevo perfil"), _("C&rear"), con_orientacion=True)
        if datos is None:
            return
        nombre, vertical = datos
        self._operaciones.en_hilo(
            lambda: perfiles_obs.crear_perfil(
                self._cliente(), nombre, vertical=vertical),
            lambda _resultado: self._creado(nombre))

    def _creado(self, nombre):
        anunciar(_("Perfil creado: {nombre}.").format(nombre=nombre))
        self._operaciones.en_hilo(
            lambda: self._leer_para_editar(nombre),
            lambda datos: self._abrir_ajustes(datos, foco=nombre))

    def duplicar(self):
        origen = self._elegido()
        if not origen:
            return self._sin_seleccion()
        datos = self._pedir_nombre(_("Duplicar perfil"), _("&Duplicar"))
        if datos is None:
            return
        nombre, _vertical = datos
        self._operaciones.en_hilo(
            lambda: perfiles_obs.duplicar_perfil(
                self._cliente(), origen, nombre),
            lambda _resultado: self._hecho(
                _("Perfil duplicado: {nombre}.").format(nombre=nombre),
                nombre))

    def _pedir_nombre(self, titulo, accion, con_orientacion=False):
        dialogo = DialogoNombrePerfil(
            self, existentes=self._perfiles, con_orientacion=con_orientacion,
            titulo=titulo, accion=accion)
        try:
            if dialogo.ShowModal() != wx.ID_OK:
                return None
            return dialogo.nombre(), dialogo.vertical()
        finally:
            dialogo.Destroy()

    def eliminar(self):
        nombre = self._elegido()
        if not nombre:
            return self._sin_seleccion()
        if nombre == self._actual:
            anunciar(_(perfiles_obs.MENSAJE_EN_USO))
            return
        if len(self._perfiles) <= 1:
            anunciar(_(perfiles_obs.MENSAJE_UNICO))
            return
        indice = self._indice(nombre)
        mensaje = _("¿Eliminar el perfil {nombre}?").format(nombre=nombre)
        aviso = usos_perfil.texto_al_eliminar(nombre, self._config)
        if aviso:
            mensaje = "{} {}".format(mensaje, aviso)
        if not confirmar.preguntar(
                self, mensaje,
                _("Eliminar perfil"), _("&Eliminar"), _("&Cancelar"),
                predeterminado_si=False):
            return
        siguiente = self._siguiente(indice)
        cambios = usos_perfil.cambios_al_eliminar(nombre, self._config)
        self._operaciones.en_hilo(
            lambda: perfiles_obs.eliminar_perfil(self._cliente(), nombre),
            lambda _resultado: self._eliminado(nombre, siguiente, cambios))

    def _eliminado(self, nombre, siguiente, cambios):
        self._guardar_cambios(cambios)
        self._hecho(
            _("Perfil eliminado: {nombre}.").format(nombre=nombre),
            siguiente)

    def _siguiente(self, indice):
        if indice is None:
            return None
        for posicion in range(indice + 1, len(self._perfiles)):
            return self._perfiles[posicion]
        if indice > 0:
            return self._perfiles[indice - 1]
        return None

    def editar(self):
        nombre = self._elegido()
        if not nombre:
            return self._sin_seleccion()
        self._operaciones.en_hilo(
            lambda: self._leer_para_editar(nombre), self._abrir_ajustes)

    def _leer_para_editar(self, nombre):
        cliente = self._cliente()
        ajustes, avanzado, personalizado = perfiles_obs.leer_para_editar(
            cliente, nombre)
        return (nombre, ajustes, avanzado, personalizado,
                salidas_audio.salidas(cliente),
                codificadores_obs.codificadores_disponibles())

    def _abrir_ajustes(self, datos, foco=None):
        (nombre, ajustes, avanzado, personalizado, salidas,
         codificadores) = datos
        dialogo = DialogoAjustesPerfil(
            self, ajustes, nombre, avanzado=avanzado,
            personalizado=personalizado, salidas=salidas,
            codificadores=codificadores)
        aceptado = False
        try:
            if dialogo.ShowModal() == wx.ID_OK:
                aceptado = True
                pasar = dialogo.pasar_a_sencillo_pedido()
                nuevos = None if pasar else dialogo.ajustes()
        finally:
            dialogo.Destroy()
        if not aceptado:
            if foco is not None:
                self._recargar(foco)
            return
        if pasar:
            self._operaciones.en_hilo(
                lambda: perfiles_obs.pasar_a_sencillo(
                    self._cliente(), nombre),
                lambda _resultado: self._hecho(
                    _("Perfil {nombre} en modo Sencillo.").format(
                        nombre=nombre), nombre))
            return
        self._operaciones.en_hilo(
            lambda: perfiles_obs.guardar_ajustes(
                self._cliente(), nuevos, nombre),
            lambda _resultado: self._hecho(
                _("Ajustes guardados en el perfil {nombre}.").format(
                    nombre=nombre), nombre))

    def preparar_perfiles(self):
        AsistentePerfilesPanel(
            self, self._operaciones, self._cliente, self._config,
            self._asistente_terminado).empezar()

    def _asistente_terminado(self, resultado):
        self._guardar_cambios([(perfil.uso, perfil.nombre)
                               for perfil in resultado.perfiles])
        foco = resultado.perfiles[0].nombre if resultado.perfiles else None
        self._recargar(foco)
