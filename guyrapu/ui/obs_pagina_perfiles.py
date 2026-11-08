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
from guyrapu.ui.dialogo_usos_perfil import DialogoUsosPerfil
from guyrapu.ui.preferencias_comun import (
    fila_horizontal,
    nombre_de_etiqueta,
)


class DialogoNombrePerfil(wx.Dialog):
    """Pide el nombre y, para uno nuevo, la orientación."""

    def __init__(self, padre, existentes=(), con_orientacion=False,
                 titulo="", accion=""):
        super().__init__(padre, title=titulo or _("Nombre del perfil"),
                         name="DialogoNombrePerfil")
        self._existentes = {str(nombre) for nombre in existentes}
        self._con_orientacion = con_orientacion
        caja = wx.BoxSizer(wx.VERTICAL)
        self.rot_nombre = wx.StaticText(self, label=_("&Nombre:"))
        self.txt_nombre = wx.TextCtrl(
            self, name=nombre_de_etiqueta(_("&Nombre:")))
        nombre_accesible(self.txt_nombre, self.txt_nombre.GetName())
        fila = wx.BoxSizer(wx.HORIZONTAL)
        fila.Add(self.rot_nombre, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 6)
        fila.Add(self.txt_nombre, 1, wx.EXPAND | wx.ALL, 6)
        caja.Add(fila, 0, wx.EXPAND)
        if con_orientacion:
            self.rad_orientacion = wx.RadioBox(
                self, label=_("Orientación"),
                choices=[_("Horizontal"), _("Vertical")], majorDimension=2,
                style=wx.RA_SPECIFY_ROWS, name=_("Orientación"))
            nombre_accesible(self.rad_orientacion, _("Orientación"))
            self.rad_orientacion.SetSelection(0)
            caja.Add(self.rad_orientacion, 0, wx.ALL, 6)
        self.txt_error = wx.StaticText(self, label="")
        caja.Add(self.txt_error, 0, wx.LEFT | wx.RIGHT, 8)
        fila_botones = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_aceptar = wx.Button(
            self, wx.ID_OK, accion or _("C&rear"),
            name=nombre_de_etiqueta(accion or _("C&rear")))
        self.btn_cancelar = wx.Button(
            self, wx.ID_CANCEL, _("&Cancelar"),
            name=nombre_de_etiqueta(_("&Cancelar")))
        self.btn_aceptar.SetDefault()
        fila_botones.Add(self.btn_aceptar, 0, wx.RIGHT, 6)
        fila_botones.Add(self.btn_cancelar, 0)
        caja.Add(fila_botones, 0, wx.ALIGN_RIGHT | wx.ALL, 10)
        self.SetSizerAndFit(caja)
        self.SetMinSize((420, -1))
        self.Centre()
        self.btn_aceptar.Bind(wx.EVT_BUTTON, self._al_aceptar)
        self.txt_nombre.SetFocus()

    def _al_aceptar(self, _evento):
        nombre = self.nombre()
        if not nombre:
            self.txt_error.SetLabel(_("Escribe un nombre para el perfil."))
            self.txt_nombre.SetFocus()
            self.Layout()
            self.Fit()
            return
        if nombre in self._existentes:
            self.txt_error.SetLabel(_(perfiles_obs.MENSAJE_EXISTE))
            self.txt_nombre.SetFocus()
            self.Layout()
            self.Fit()
            return
        self.EndModal(wx.ID_OK)

    def nombre(self) -> str:
        return self.txt_nombre.GetValue().strip()

    def vertical(self) -> bool:
        if not self._con_orientacion:
            return False
        return self.rad_orientacion.GetSelection() == 1


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
        self._enlazar_eventos()
        self.acciones = (self.lista, self.btn_usar, self.btn_usar_para,
                         self.btn_nuevo, self.btn_duplicar, self.btn_eliminar,
                         self.btn_editar)

    def _crear_controles(self):
        caja = wx.BoxSizer(wx.VERTICAL)
        self.lista = wx.ListBox(
            self, style=wx.LB_SINGLE | wx.LB_HSCROLL,
            name=_("Perfiles de OBS"))
        nombre_accesible(self.lista, _("Perfiles de OBS"))
        caja.Add(self.lista, 1, wx.EXPAND | wx.ALL, 8)
        self.btn_usar = self._boton(_("&Usar este perfil"),
                                    _("&Usar este perfil"), self.usar)
        self.btn_usar_para = self._boton(_("Usar p&ara…"), _("Usar para…"),
                                         self.usar_para)
        self.btn_nuevo = self._boton(_("&Nuevo…"), _("&Nuevo…"), self.nuevo)
        self.btn_duplicar = self._boton(_("&Duplicar…"), _("&Duplicar…"),
                                        self.duplicar)
        self.btn_eliminar = self._boton(_("&Eliminar perfil"), _("&Eliminar perfil"),
                                        self.eliminar)
        self.btn_editar = self._boton(_("Editar a&justes…"),
                                      _("Editar a&justes…"), self.editar)
        caja.Add(fila_horizontal((self.btn_usar, self.btn_usar_para,
                                  self.btn_nuevo, self.btn_duplicar,
                                  self.btn_eliminar, self.btn_editar)),
                 0, wx.ALL, 6)
        self.SetSizer(caja)

    def _boton(self, etiqueta, nombre, manejador):
        control = wx.Button(self, label=etiqueta,
                            name=nombre_de_etiqueta(nombre))
        nombre_accesible(control, control.GetName())
        control.Bind(wx.EVT_BUTTON, lambda _evento: manejador())
        return control

    def _enlazar_eventos(self):
        self.lista.Bind(wx.EVT_LISTBOX_DCLICK,
                        lambda _evento: self.editar())

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
        self.lista.Clear()
        for nombre in self._perfiles:
            self.lista.Append(self._etiqueta(nombre))
        if not self._perfiles:
            return
        indice = self._indice(foco)
        if indice is None:
            indice = self._indice(self._actual)
        self.lista.SetSelection(0 if indice is None else indice)
        if foco is not None:
            self.lista.SetFocus()

    def _indice(self, nombre):
        if nombre in self._perfiles:
            return self._perfiles.index(nombre)
        return None

    def _elegido(self):
        indice = self.lista.GetSelection()
        if 0 <= indice < len(self._perfiles):
            return self._perfiles[indice]
        return ""

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
            lambda _resultado: self._hecho(
                _("Perfil creado: {nombre}.").format(nombre=nombre), nombre))

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

    def _abrir_ajustes(self, datos):
        (nombre, ajustes, avanzado, personalizado, salidas,
         codificadores) = datos
        dialogo = DialogoAjustesPerfil(
            self, ajustes, nombre, avanzado=avanzado,
            personalizado=personalizado, salidas=salidas,
            codificadores=codificadores)
        try:
            if dialogo.ShowModal() != wx.ID_OK:
                return
            pasar = dialogo.pasar_a_sencillo_pedido()
            nuevos = None if pasar else dialogo.ajustes()
        finally:
            dialogo.Destroy()
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
