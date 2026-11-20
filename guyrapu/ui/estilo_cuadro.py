# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Cuadro que edita un estilo del vídeo y el que cambia solo su nombre.

Recoge los datos y valida: no guarda. La colección y el disco los maneja la
ventana de estilos del vídeo.
"""

from __future__ import annotations

import uuid

import wx

from guyrapu.core.idioma import N_, _
from guyrapu.obs import estilos_aviso
from guyrapu.ui import confirmar, estilo_opciones, formulario, paleta, tecla_escape
from guyrapu.ui.accesibilidad import (ContadorAccesible, anunciar,
                                      nombre_accesible)
from guyrapu.ui.preferencias_comun import (EleccionTexto, fila_label,
                                           nombre_de_etiqueta)

TITULO_AGREGAR = N_("Agregar estilo del vídeo")
TITULO_EDITAR = N_("Editar estilo del vídeo")


def clave_nueva(usados) -> str:
    """Una clave que no usa ningún estilo de fábrica ni del usuario."""
    claves = {estilo["clave"] for estilo in estilos_aviso.FABRICA}
    claves.update(estilo.get("clave") for estilo in usados)
    while True:
        clave = "estilo_" + uuid.uuid4().hex[:12]
        if clave not in claves:
            return clave


class DialogoEstilo(wx.Dialog):
    """Todos los campos de un estilo del vídeo."""

    def __init__(self, padre, estilo, otros):
        super().__init__(
            padre,
            title=_(TITULO_EDITAR if estilo else TITULO_AGREGAR),
            name="DialogoEstiloVideo")
        self._otros = list(otros)
        self._base = (dict(estilo) if estilo
                      else dict(estilos_aviso.FABRICA[0], nombre="", clave=""))
        self._clave = (self._base.get("clave", "") if estilo
                       else clave_nueva(self._otros))
        self._crear_controles()
        self.Bind(wx.EVT_CHAR_HOOK, self._al_tecla)
        self.Fit()
        self.Centre()
        paleta.pintar_ventana(self)
        self.txt_nombre.SetFocus()

    def _crear_controles(self):
        panel = wx.Panel(self, name="PanelEstiloVideo")
        vs = wx.BoxSizer(wx.VERTICAL)
        izquierda = self._columna_izquierda(panel)
        derecha = self._columna_derecha(panel)
        formulario.columnas(vs, izquierda, derecha)
        self.btn_aceptar = wx.Button(panel, wx.ID_OK, _("&Aceptar"),
                                     name=_("Aceptar"))
        self.btn_cancelar = wx.Button(panel, wx.ID_CANCEL, _("&Cancelar"),
                                      name=_("Cancelar"))
        self.btn_aceptar.SetDefault()
        self.btn_aceptar.Bind(wx.EVT_BUTTON, self._aceptar)
        self.btn_cancelar.Bind(
            wx.EVT_BUTTON, lambda _evento: self.EndModal(wx.ID_CANCEL))
        formulario.agregar_pie(vs, [self.btn_aceptar, self.btn_cancelar])
        formulario.ajustar_tamano(self, panel, vs)
        self._cargar()

    def _columna_izquierda(self, panel):
        columna = wx.BoxSizer(wx.VERTICAL)
        rotulo = fila_label(panel, _("&Nombre:"))
        self.txt_nombre = wx.TextCtrl(
            panel, name=nombre_de_etiqueta(_("Nombre:")))
        nombre_accesible(self.txt_nombre, self.txt_nombre.GetName())
        formulario.agregar_fila(columna, rotulo, self.txt_nombre)

        rotulo = fila_label(panel, _("&Fuente:"))
        self._fuente = estilo_opciones.Fuente(
            panel, _("&Fuente:"), self._base.get("fuente", ""))
        self.cho_fuente = self._fuente.control
        formulario.agregar_fila(columna, rotulo, self.cho_fuente)

        rotulo = fila_label(panel, _("&Tamaño (% del lado menor del vídeo):"))
        self.sp_tamano = wx.SpinCtrlDouble(
            panel, min=2, max=15, initial=5, inc=0.5,
            name=nombre_de_etiqueta(_("&Tamaño (% del lado menor del vídeo):")))
        self.sp_tamano.SetDigits(1)
        formulario.agregar_fila(
            columna, rotulo, self.sp_tamano, numerico=True)

        self.chk_negrita = wx.CheckBox(
            panel, label=_("Ne&grita"),
            name=nombre_de_etiqueta(_("Negrita")))
        formulario.agregar_fila(columna, None, self.chk_negrita)

        self._color_texto = self._campo_color(
            columna, panel, _("Color del te&xto:"),
            self._base.get("color_texto", ""))
        self.cho_color_texto = self._color_texto.control
        self._color_contorno = self._campo_color(
            columna, panel, _("Color del c&ontorno:"),
            self._base.get("color_contorno", ""))
        self.cho_color_contorno = self._color_contorno.control

        self.sp_ancho = self._fila_contador(
            columna, panel, _("Anc&ho del contorno:"), 0, 12, 0)
        self._color_fondo = self._campo_color(
            columna, panel, _("Color del fon&do:"),
            self._base.get("color_fondo", ""))
        self.cho_color_fondo = self._color_fondo.control
        self.sp_opacidad = self._fila_contador(
            columna, panel, _("O&pacidad del fondo:"), 0, 100, 0, hueco=0)
        return columna

    def _fila_contador(self, columna, panel, rotulo, minimo, maximo, inicial,
                       hueco=formulario.CONTROL_A_ETIQUETA):
        etiqueta = fila_label(panel, rotulo)
        control = ContadorAccesible(
            panel, min=minimo, max=maximo, initial=inicial,
            name=nombre_de_etiqueta(rotulo))
        formulario.agregar_fila(columna, etiqueta, control, numerico=True,
                                hueco=hueco)
        return control

    def _fila_eleccion(self, columna, panel, rotulo, opciones):
        etiqueta = fila_label(panel, rotulo)
        control = EleccionTexto(panel, opciones,
                                name=nombre_de_etiqueta(rotulo))
        formulario.agregar_fila(columna, etiqueta, control)
        return control

    def _fila_numero(self, columna, panel, rotulo, minimo, maximo, inicial):
        etiqueta = fila_label(panel, rotulo)
        control = wx.SpinCtrlDouble(
            panel, min=minimo, max=maximo, initial=inicial, inc=50,
            name=nombre_de_etiqueta(rotulo))
        control.SetDigits(0)
        formulario.agregar_fila(columna, etiqueta, control, numerico=True)
        return control

    def _columna_derecha(self, panel):
        columna = wx.BoxSizer(wx.VERTICAL)
        self.cho_alineacion = self._fila_eleccion(
            columna, panel, _("A&lineación:"),
            estilo_opciones.opciones_alineacion())
        self.cho_zona = self._fila_eleccion(
            columna, panel, _("&Zona:"), estilo_opciones.opciones_zona())
        self.cho_entrada = self._fila_eleccion(
            columna, panel, _("Animación de &entrada:"),
            estilo_opciones.opciones_entrada())
        self.sp_ms_entrada = self._fila_numero(
            columna, panel, _("Du&ración de la entrada:"), 100, 1000, 350)
        self.cho_salida = self._fila_eleccion(
            columna, panel, _("Animación de &salida:"),
            estilo_opciones.opciones_salida())
        self.sp_ms_salida = self._fila_numero(
            columna, panel, _("D&uración de la salida:"), 100, 1000, 250)
        self.chk_esquinas = wx.CheckBox(
            panel, label=_("Es&quinas redondeadas"),
            name=nombre_de_etiqueta(_("Esquinas redondeadas")))
        self.chk_sombra = wx.CheckBox(
            panel, label=_("So&mbra"),
            name=nombre_de_etiqueta(_("Sombra")))
        formulario.agregar_casillas(
            columna, (self.chk_esquinas, self.chk_sombra), hueco=0)
        return columna

    def _campo_color(self, columna, panel, rotulo, codigo):
        etiqueta = fila_label(panel, rotulo)
        color = estilo_opciones.Color(panel, rotulo, codigo)
        formulario.agregar_fila(columna, etiqueta, color.control)
        return color

    def _cargar(self):
        self.txt_nombre.SetValue(self._base.get("nombre", ""))
        self.sp_tamano.SetValue(float(self._base.get("tamano", 5)))
        self.chk_negrita.SetValue(bool(self._base.get("negrita", False)))
        self.sp_ancho.SetValue(int(self._base.get("ancho_contorno", 0)))
        self.sp_opacidad.SetValue(int(self._base.get("opacidad_fondo", 0)))
        self.cho_alineacion.SetValue(self._base.get("alineacion", "izquierda"))
        self.cho_zona.SetValue(self._base.get("zona", "automatica"))
        self.cho_entrada.SetValue(self._base.get("entrada", "suave"))
        self.sp_ms_entrada.SetValue(float(self._base.get("ms_entrada", 350)))
        self.cho_salida.SetValue(self._base.get("salida", "fundido"))
        self.sp_ms_salida.SetValue(float(self._base.get("ms_salida", 250)))
        self.chk_esquinas.SetValue(
            self._base.get("esquinas", "redondeadas") == "redondeadas")
        self.chk_sombra.SetValue(bool(self._base.get("sombra", False)))

    def datos(self) -> dict:
        """El estilo tal como se guarda, con su clave estable."""
        return {
            "clave": self._clave,
            "nombre": self.txt_nombre.GetValue().strip(),
            "fuente": self._fuente.valor(),
            "tamano": round(float(self.sp_tamano.GetValue()), 1),
            "negrita": self.chk_negrita.GetValue(),
            "color_texto": self._color_texto.valor(),
            "color_contorno": self._color_contorno.valor(),
            "ancho_contorno": int(self.sp_ancho.GetValue()),
            "color_fondo": self._color_fondo.valor(),
            "opacidad_fondo": int(self.sp_opacidad.GetValue()),
            "alineacion": self.cho_alineacion.GetValue(),
            "zona": self.cho_zona.GetValue(),
            "entrada": self.cho_entrada.GetValue(),
            "ms_entrada": int(round(self.sp_ms_entrada.GetValue())),
            "salida": self.cho_salida.GetValue(),
            "ms_salida": int(round(self.sp_ms_salida.GetValue())),
            "esquinas": ("redondeadas" if self.chk_esquinas.GetValue()
                         else "rectas"),
            "sombra": self.chk_sombra.GetValue(),
        }

    def _aceptar(self, _evento):
        estilo = self.datos()
        error = estilos_aviso.validar_estilo(estilo, self._otros)
        if error:
            anunciar(error)
            self._campo_del_error(estilo).SetFocus()
            return
        aviso = estilos_aviso.aviso_contraste(estilo)
        if aviso and not confirmar.preguntar(
                self,
                _("¿Quieres guardar el estilo igual?") + "\n\n" + aviso,
                _("Guardar estilo del vídeo"), _("&Sí"), _("&No"),
                predeterminado_si=False):
            return
        self.EndModal(wx.ID_OK)

    def _campo_del_error(self, estilo):
        """El primer campo que `validar_estilo` rechaza, en su mismo orden."""
        nombre = str(estilo.get("nombre", "")).strip()
        if not nombre or self._nombre_repetido(nombre):
            return self.txt_nombre
        if not 2 <= float(estilo.get("tamano", 0)) <= 15:
            return self.sp_tamano
        for control, clave in ((self.cho_color_texto, "color_texto"),
                               (self.cho_color_contorno, "color_contorno"),
                               (self.cho_color_fondo, "color_fondo")):
            if not estilos_aviso._COLOR_RE.fullmatch(estilo[clave]):
                return control
        if not 0 <= float(estilo.get("opacidad_fondo", 0)) <= 100:
            return self.sp_opacidad
        if not 100 <= float(estilo.get("ms_entrada", 0)) <= 1000:
            return self.sp_ms_entrada
        return self.sp_ms_salida

    def _nombre_repetido(self, nombre) -> bool:
        for referencia in estilos_aviso.FABRICA + tuple(self._otros):
            if referencia.get("clave") == self._clave:
                continue
            if (str(referencia.get("nombre", "")).strip().casefold()
                    == nombre.casefold()):
                return True
        return False

    def _al_tecla(self, evento):
        tecla_escape.cancelar_si_escape(self, evento)


class DialogoNombre(wx.Dialog):
    """Pide un nombre, sin validarlo: el bucle de la ventana lo repite."""

    def __init__(self, padre, nombre):
        super().__init__(padre, title=_("Cambiar nombre"),
                         name="DialogoNombreEstilo")
        panel = wx.Panel(self, name="PanelNombreEstilo")
        caja = wx.BoxSizer(wx.VERTICAL)
        rotulo = fila_label(panel, _("&Nombre:"))
        self.txt_nombre = wx.TextCtrl(
            panel, name=nombre_de_etiqueta(_("Nombre:")))
        nombre_accesible(self.txt_nombre, self.txt_nombre.GetName())
        self.txt_nombre.SetValue(nombre)
        formulario.agregar_fila(caja, rotulo, self.txt_nombre, hueco=0)
        self.btn_aceptar = wx.Button(panel, wx.ID_OK, _("&Aceptar"),
                                     name=_("Aceptar"))
        self.btn_cancelar = wx.Button(panel, wx.ID_CANCEL, _("&Cancelar"),
                                      name=_("Cancelar"))
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


def abrir(padre, estilo=None, otros=()):
    """Abre el cuadro y devuelve el estilo, o None si se cancela."""
    dialogo = DialogoEstilo(padre, estilo, otros)
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
