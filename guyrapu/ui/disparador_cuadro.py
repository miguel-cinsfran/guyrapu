# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Cuadro que edita un disparador y el que cambia solo su nombre.

Recoge los datos y valida: no guarda. La colección y el disco los maneja la
ventana de disparadores.
"""

from __future__ import annotations

import wx

from guyrapu.core import paths
from guyrapu.core.idioma import N_, _
from guyrapu.interaction import comandos, disparadores, disparadores_guardados
from guyrapu.interaction import medios_guardados
from guyrapu.interaction.texto import normalizar
from guyrapu.obs import estilos_aviso
from guyrapu.ui import paleta, tecla_escape
from guyrapu.ui.accesibilidad import ContadorAccesible, anunciar, nombre_accesible
from guyrapu.ui.preferencias_comun import fila_label, nombre_de_etiqueta

TITULO_AGREGAR = N_("Agregar disparador")
TITULO_EDITAR = N_("Editar disparador")


def _cuandos():
    return [_("Comando del chat"), _("Evento del directo")]


def _eventos():
    return [_(disparadores.NOMBRES_EVENTOS[clave])
            for clave in disparadores.EVENTOS_DEL_DIRECTO]


def _permisos():
    return [_("Todos"), _("Solo moderadores"), _("Una lista de nombres")]


def _estilos():
    return estilos_aviso.todos(
        estilos_aviso.cargar_estilos(paths.estilos_avisos()))


def _medios():
    return medios_guardados.cargar(paths.medios())


def _numero(valor) -> str:
    numero = float(valor)
    if numero.is_integer():
        return str(int(numero))
    return f"{numero:g}"


class DialogoDisparador(wx.Dialog):
    """Cuándo, qué, aspecto, permiso y esperas de un disparador."""

    def __init__(self, padre, datos, otros):
        super().__init__(
            padre,
            title=_(TITULO_EDITAR if datos else TITULO_AGREGAR),
            name="DialogoDisparador")
        self._otros = [disparadores_guardados.a_disparador(otro)
                       for otro in otros]
        self._estilos = _estilos()
        self._medios = _medios()
        self._crear_controles(datos)
        self.Bind(wx.EVT_CHAR_HOOK, self._al_tecla)
        self.Fit()
        self.Centre()
        paleta.pintar_ventana(self)
        self.txt_nombre.SetFocus()

    def _crear_controles(self, datos):
        panel = wx.Panel(self, name="PanelDisparador")
        vs = wx.BoxSizer(wx.VERTICAL)
        self._crear_cuando(panel, vs)
        self._crear_que(panel, vs)
        self._crear_alcance(panel, vs)
        vs.Add(self._botones(panel), 0, wx.ALIGN_RIGHT | wx.ALL, 8)
        panel.SetSizer(vs)
        self._cargar(datos)

    def _crear_cuando(self, panel, vs):
        vs.Add(fila_label(panel, _("&Nombre:")), 0, wx.ALL, 8)
        self.txt_nombre = self._campo(panel, _("&Nombre:"))
        vs.Add(self.txt_nombre, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        vs.Add(fila_label(panel, _("C&uándo:")), 0, wx.LEFT | wx.RIGHT, 8)
        self.cho_cuando = self._eleccion(panel, _("C&uándo:"), _cuandos())
        vs.Add(self.cho_cuando, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        vs.Add(fila_label(panel, _("Co&mandos del chat:")), 0,
               wx.LEFT | wx.RIGHT, 8)
        self.txt_comandos = self._campo(panel, _("Co&mandos del chat:"))
        vs.Add(self.txt_comandos, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        vs.Add(fila_label(panel, _("&Evento:")), 0, wx.LEFT | wx.RIGHT, 8)
        self.cho_evento = self._eleccion(panel, _("&Evento:"), _eventos())
        vs.Add(self.cho_evento, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        vs.Add(fila_label(panel, _("Cantidad mín&ima:")), 0,
               wx.LEFT | wx.RIGHT, 8)
        self.txt_minimo = self._campo(panel, _("Cantidad mín&ima:"))
        vs.Add(self.txt_minimo, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

    def _crear_que(self, panel, vs):
        vs.Add(fila_label(panel, _("Me&dio:")), 0, wx.LEFT | wx.RIGHT, 8)
        self.cho_medio = self._eleccion(
            panel, _("Me&dio:"), [_("Ninguno")] + self._nombres_de_medios())
        vs.Add(self.cho_medio, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        vs.Add(fila_label(panel, _("&Texto de la tarjeta:")), 0,
               wx.LEFT | wx.RIGHT, 8)
        self.txt_tarjeta = self._campo(panel, _("&Texto de la tarjeta:"))
        vs.Add(self.txt_tarjeta, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        vs.Add(fila_label(panel, _("Esti&lo:")), 0, wx.LEFT | wx.RIGHT, 8)
        self.cho_estilo = self._eleccion(
            panel, _("Esti&lo:"), [_(estilo["nombre"])
                                   for estilo in self._estilos])
        vs.Add(self.cho_estilo, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        self.sp_segundos = self._contador(
            panel, _("&Segundos en pantalla:"), 3, 60, 8)
        vs.Add(fila_label(panel, _("&Segundos en pantalla:")), 0,
               wx.LEFT | wx.RIGHT, 8)
        vs.Add(self.sp_segundos, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

    def _crear_alcance(self, panel, vs):
        vs.Add(fila_label(panel, _("Pe&rmiso:")), 0, wx.LEFT | wx.RIGHT, 8)
        self.cho_permiso = self._eleccion(
            panel, _("Pe&rmiso:"), _permisos())
        vs.Add(self.cho_permiso, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        vs.Add(fila_label(panel, _("Nombres &permitidos:")), 0,
               wx.LEFT | wx.RIGHT, 8)
        self.txt_nombres = self._campo(panel, _("Nombres &permitidos:"))
        vs.Add(self.txt_nombres, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        self.sp_espera = self._contador(
            panel, _("Espera &general (segundos):"), 0, 3600, 5)
        vs.Add(fila_label(panel, _("Espera &general (segundos):")), 0,
               wx.LEFT | wx.RIGHT, 8)
        vs.Add(self.sp_espera, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        self.sp_persona = self._contador(
            panel, _("Espera por pers&ona (segundos):"), 0, 3600, 30)
        vs.Add(fila_label(panel, _("Espera por pers&ona (segundos):")), 0,
               wx.LEFT | wx.RIGHT, 8)
        vs.Add(self.sp_persona, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

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
        fila = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_aceptar = wx.Button(
            panel, wx.ID_OK, _("&Aceptar"), name=_("Aceptar"))
        self.btn_cancelar = wx.Button(
            panel, wx.ID_CANCEL, _("&Cancelar"), name=_("Cancelar"))
        self.btn_aceptar.SetDefault()
        self.btn_aceptar.Bind(wx.EVT_BUTTON, self._aceptar)
        self.btn_cancelar.Bind(
            wx.EVT_BUTTON, lambda _evento: self.EndModal(wx.ID_CANCEL))
        fila.Add(self.btn_aceptar, 0, wx.RIGHT, 6)
        fila.Add(self.btn_cancelar, 0)
        return fila

    def _cargar(self, datos):
        disparador = disparadores_guardados.a_disparador(datos or {})
        self._activo = disparador.activo
        self.txt_nombre.SetValue(disparador.nombre)
        self.cho_cuando.SetSelection(
            disparadores.CUANDOS.index(disparador.cuando))
        self.txt_comandos.SetValue(", ".join(disparador.comandos))
        self._elegir_evento(disparador.evento)
        self.txt_minimo.SetValue(
            "" if disparador.minimo is None
            else _numero(disparador.minimo))
        self._elegir_medio(disparador.medio)
        self.txt_tarjeta.SetValue(disparador.tarjeta)
        self._elegir_estilo(disparador.estilo)
        self.sp_segundos.SetValue(disparador.segundos)
        self.cho_permiso.SetSelection(
            comandos.PERMISOS.index(disparador.permiso))
        self.txt_nombres.SetValue(", ".join(disparador.nombres))
        self.sp_espera.SetValue(int(disparador.espera_general))
        self.sp_persona.SetValue(int(disparador.espera_persona))

    def _elegir_evento(self, clave):
        try:
            indice = disparadores.EVENTOS_DEL_DIRECTO.index(clave)
        except ValueError:
            indice = 0
        self.cho_evento.SetSelection(indice)

    def _elegir_medio(self, nombre):
        nombres = self._nombres_de_medios()
        try:
            indice = nombres.index(nombre) + 1
        except ValueError:
            indice = 0
        self.cho_medio.SetSelection(indice)

    def _elegir_estilo(self, clave):
        for indice, estilo in enumerate(self._estilos):
            if estilo["clave"] == clave:
                self.cho_estilo.SetSelection(indice)
                return
        self.cho_estilo.SetSelection(0)

    def _minimo_de_campo(self):
        texto = self.txt_minimo.GetValue().strip()
        if not texto:
            return None
        try:
            return float(texto.replace(",", "."))
        except ValueError:
            return None

    def _medio_elegido(self):
        indice = self.cho_medio.GetSelection()
        if indice <= 0:
            return ""
        return self._nombres_de_medios()[indice - 1]

    def _disparador_de_campos(self):
        cuando = disparadores.CUANDOS[self.cho_cuando.GetSelection()]
        return disparadores.Disparador(
            nombre=self.txt_nombre.GetValue(),
            cuando=cuando,
            comandos=(comandos.separar_alias(self.txt_comandos.GetValue())
                      if cuando == "comando" else ()),
            evento=(disparadores.EVENTOS_DEL_DIRECTO[
                self.cho_evento.GetSelection()]
                if cuando == "evento" else ""),
            minimo=(self._minimo_de_campo()
                    if cuando == "evento" else None),
            medio=self._medio_elegido(),
            tarjeta=self.txt_tarjeta.GetValue(),
            estilo=self._estilos[self.cho_estilo.GetSelection()]["clave"],
            segundos=self.sp_segundos.GetValue(),
            permiso=comandos.PERMISOS[self.cho_permiso.GetSelection()],
            nombres=comandos.separar_nombres(self.txt_nombres.GetValue()),
            espera_general=float(self.sp_espera.GetValue()),
            espera_persona=float(self.sp_persona.GetValue()),
            activo=self._activo,
        )

    def _aceptar(self, _evento):
        disparador = self._disparador_de_campos()
        error = disparadores.validar(disparador, self._otros)
        if error:
            anunciar(error)
            self._campo_del_error(disparador).SetFocus()
            return
        self.EndModal(wx.ID_OK)

    def _campo_del_error(self, disparador):
        if not normalizar(disparador.nombre):
            return self.txt_nombre
        if any(normalizar(otro.nombre) == normalizar(disparador.nombre)
               for otro in self._otros):
            return self.txt_nombre
        if disparador.cuando == "comando":
            propios = {normalizar(nombre)
                       for nombre in disparador.comandos}
            propios.discard("")
            if not propios:
                return self.txt_comandos
            for otro in self._otros:
                if propios & {normalizar(nombre)
                              for nombre in otro.comandos}:
                    return self.txt_comandos
        else:
            if disparador.evento not in disparadores.EVENTOS_DEL_DIRECTO:
                return self.cho_evento
            if (disparador.minimo is not None
                    and disparador.minimo < 0):
                return self.txt_minimo
        if (not (disparador.medio or "").strip()
                and not (disparador.tarjeta or "").strip()):
            return self.txt_tarjeta
        return self.txt_nombre

    def datos(self) -> dict:
        """El disparador tal como se guarda."""
        return disparadores_guardados.desde_disparador(
            self._disparador_de_campos())

    def _al_tecla(self, evento):
        tecla_escape.cancelar_si_escape(self, evento)


class DialogoNombre(wx.Dialog):
    """Pide un nombre, sin validarlo: el bucle de la ventana lo repite."""

    def __init__(self, padre, nombre):
        super().__init__(padre, title=_("Cambiar nombre"),
                         name="DialogoNombreDisparador")
        caja = wx.BoxSizer(wx.VERTICAL)
        caja.Add(fila_label(self, _("&Nombre:")), 0, wx.ALL, 8)
        self.txt_nombre = wx.TextCtrl(
            self, name=nombre_de_etiqueta(_("&Nombre:")))
        nombre_accesible(self.txt_nombre, self.txt_nombre.GetName())
        self.txt_nombre.SetValue(nombre)
        caja.Add(self.txt_nombre, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        fila = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_aceptar = wx.Button(
            self, wx.ID_OK, _("&Aceptar"), name=_("Aceptar"))
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


def abrir(padre, datos=None, otros=()):
    """Abre el cuadro y devuelve los datos del disparador, o None."""
    dialogo = DialogoDisparador(padre, datos or {}, otros)
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
