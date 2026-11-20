# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Cuadro que edita un comando del chat y el que cambia solo su palabra.

Recoge los datos y valida: no guarda. La colección y el disco los maneja la
ventana de comandos del chat.
"""

from __future__ import annotations

import re

import wx

from guyrapu.core import paths
from guyrapu.core.idioma import N_, _
from guyrapu.interaction import comandos
from guyrapu.interaction import comandos_guardados, estilo_elegido
from guyrapu.interaction.texto import normalizar
from guyrapu.obs import estilos_aviso
from guyrapu.ui import formulario, paleta, tecla_escape
from guyrapu.ui.accesibilidad import ContadorAccesible, anunciar, nombre_accesible
from guyrapu.ui.preferencias_comun import fila_label, nombre_de_etiqueta

TITULO_AGREGAR = N_("Agregar comando")
TITULO_EDITAR = N_("Editar comando")
AYUDA_VARIABLES = N_("Puedes usar {usuario}, {contador} y {texto}.")
AYUDA_LISTA = N_("Puedes usar {usuario}, {contador}, {texto} y {lista}.")

_VARIABLE_RE = re.compile(r"\{([^{}]*)\}")


def _destinos():
    return [_("En el vídeo"), _("En el chat"),
            _("En el vídeo y en el chat")]


def _permisos():
    return [_("Todos"), _("Solo moderadores"), _("Una lista de nombres")]


def _nombre_invalido(nombre: str) -> bool:
    limpio = normalizar(nombre)
    return not limpio or limpio.isdecimal() or len(limpio.split()) > 1


class DialogoComando(wx.Dialog):
    """Campos, respuesta, destino, permiso, esperas y aspecto de un comando."""

    def __init__(self, padre, datos, otros):
        super().__init__(
            padre,
            title=_(TITULO_EDITAR if datos else TITULO_AGREGAR),
            name="DialogoComando")
        self._es_lista = bool((datos or {}).get("lista"))
        self._otros = [comandos_guardados.a_comando(otro) for otro in otros]
        self._usuario = estilos_aviso.cargar_estilos(paths.estilos_avisos())
        self._por_tipo = estilos_aviso.cargar_por_tipo(paths.estilos_avisos())
        self._estilos = estilos_aviso.todos(self._usuario)
        self._crear_controles(datos)
        self.Bind(wx.EVT_CHAR_HOOK, self._al_tecla)
        self.Fit()
        self.Centre()
        paleta.pintar_ventana(self)
        self.txt_palabra.SetFocus()

    def _crear_controles(self, datos):
        panel = wx.Panel(self, name="PanelComando")
        vs = wx.BoxSizer(wx.VERTICAL)
        rotulo = fila_label(panel, _("&Palabra:"))
        self.txt_palabra = self._campo(panel, _("&Palabra:"))
        formulario.agregar_fila(vs, rotulo, self.txt_palabra)
        rotulo = fila_label(panel, _("A&lias:"))
        self.txt_alias = self._campo(panel, _("A&lias:"))
        formulario.agregar_fila(vs, rotulo, self.txt_alias)
        rotulo = fila_label(panel, _("&Respuesta:"))
        self.txt_respuesta = self._campo(panel, _("&Respuesta:"))
        formulario.agregar_fila(
            vs, rotulo, self.txt_respuesta,
            hueco=formulario.ETIQUETA_A_CONTROL)
        self.ayuda = wx.StaticText(panel, label=_(AYUDA_VARIABLES))
        formulario.agregar_fila(vs, None, self.ayuda)
        rotulo = fila_label(panel, _("Dónde &sale:"))
        self.cho_destino = wx.Choice(
            panel, choices=_destinos(),
            name=nombre_de_etiqueta(_("Dónde &sale:")))
        nombre_accesible(self.cho_destino, self.cho_destino.GetName())
        formulario.agregar_fila(vs, rotulo, self.cho_destino)
        rotulo = fila_label(panel, _("&Quién puede usarlo:"))
        self.cho_permiso = wx.Choice(
            panel, choices=_permisos(),
            name=nombre_de_etiqueta(_("&Quién puede usarlo:")))
        nombre_accesible(self.cho_permiso, self.cho_permiso.GetName())
        formulario.agregar_fila(vs, rotulo, self.cho_permiso)
        rotulo = fila_label(panel, _("&Nombres:"))
        self.txt_nombres = self._campo(panel, _("&Nombres:"))
        formulario.agregar_fila(vs, rotulo, self.txt_nombres)
        self._crear_aspecto(panel, vs)
        formulario.agregar_pie(vs, self._botones(panel))
        formulario.ajustar_tamano(self, panel, vs)
        self._cargar(datos)

    def _crear_aspecto(self, panel, vs):
        for rotulo_texto, atributo, limites in (
                (_("Espera entre &usos (segundos):"), "sp_espera", (0, 3600, 5)),
                (_("Espera por pers&ona (segundos):"), "sp_persona", (0, 3600, 30)),
                (_("Se&gundos en pantalla:"), "sp_segundos", (3, 60, 8))):
            rotulo = fila_label(panel, rotulo_texto)
            control = self._contador(panel, rotulo_texto, *limites)
            setattr(self, atributo, control)
            formulario.agregar_fila(vs, rotulo, control, numerico=True)
        rotulo = fila_label(panel, _("&Estilo:"))
        self.cho_estilo = wx.Choice(
            panel, choices=estilo_elegido.opciones(
                self._usuario, self._por_tipo, "comando"),
            name=nombre_de_etiqueta(_("&Estilo:")))
        nombre_accesible(self.cho_estilo, self.cho_estilo.GetName())
        formulario.agregar_fila(vs, rotulo, self.cho_estilo)
        self.chk_activo = wx.CheckBox(
            panel, label=_("Acti&vado"), name=nombre_de_etiqueta(_("Acti&vado")))
        self.chk_en_lista = wx.CheckBox(
            panel, label=_("&Mostrar en la lista de comandos"),
            name=nombre_de_etiqueta(_("&Mostrar en la lista de comandos")))
        formulario.agregar_casillas(
            vs, (self.chk_activo, self.chk_en_lista), hueco=0)

    def _campo(self, panel, etiqueta):
        campo = wx.TextCtrl(panel, name=nombre_de_etiqueta(etiqueta))
        nombre_accesible(campo, nombre_de_etiqueta(etiqueta))
        return campo

    def _contador(self, panel, etiqueta, minimo, maximo, inicial):
        nombre = nombre_de_etiqueta(etiqueta)
        control = ContadorAccesible(
            panel, min=minimo, max=maximo, initial=inicial, name=nombre)
        nombre_accesible(control, nombre)
        return control

    def _botones(self, panel):
        self.btn_aceptar = wx.Button(panel, wx.ID_OK, _("&Aceptar"), name=_("Aceptar"))
        self.btn_cancelar = wx.Button(
            panel, wx.ID_CANCEL, _("&Cancelar"), name=_("Cancelar"))
        self.btn_aceptar.SetDefault()
        self.btn_aceptar.Bind(wx.EVT_BUTTON, self._aceptar)
        self.btn_cancelar.Bind(
            wx.EVT_BUTTON, lambda _evento: self.EndModal(wx.ID_CANCEL))
        return [self.btn_aceptar, self.btn_cancelar]

    def _cargar(self, datos):
        comando = comandos_guardados.a_comando(datos or {})
        self.txt_palabra.SetValue(comando.nombre)
        self.txt_alias.SetValue(", ".join(comando.alias))
        self.txt_respuesta.SetValue(comando.respuesta)
        self.cho_destino.SetSelection(comandos.DESTINOS.index(comando.destino))
        self.cho_permiso.SetSelection(comandos.PERMISOS.index(comando.permiso))
        self.txt_nombres.SetValue(", ".join(comando.nombres))
        self.sp_espera.SetValue(int(comando.espera_general))
        self.sp_persona.SetValue(int(comando.espera_persona))
        self._elegir_estilo(comando.estilo if datos else "")
        self.sp_segundos.SetValue(comando.segundos)
        self.chk_activo.SetValue(comando.activo)
        self.chk_en_lista.SetValue(comando.en_lista)
        if self._es_lista:
            self.ayuda.SetLabel(_(AYUDA_LISTA))
            self.chk_en_lista.Hide()

    def _elegir_estilo(self, clave):
        self.cho_estilo.SetSelection(
            estilo_elegido.indice_de(clave, self._estilos))

    def _comando_de_campos(self):
        return comandos.Comando(
            nombre=self.txt_palabra.GetValue(),
            alias=comandos.separar_alias(self.txt_alias.GetValue()),
            respuesta=self.txt_respuesta.GetValue(),
            destino=comandos.DESTINOS[self.cho_destino.GetSelection()],
            permiso=comandos.PERMISOS[self.cho_permiso.GetSelection()],
            nombres=comandos.separar_nombres(self.txt_nombres.GetValue()),
            espera_general=float(self.sp_espera.GetValue()),
            espera_persona=float(self.sp_persona.GetValue()),
            activo=self.chk_activo.GetValue(),
            estilo=estilo_elegido.clave_de(
                self.cho_estilo.GetSelection(), self._estilos),
            segundos=self.sp_segundos.GetValue(),
            lista=self._es_lista,
            en_lista=self.chk_en_lista.GetValue(),
        )

    def _aceptar(self, _evento):
        comando = self._comando_de_campos()
        error = comandos.validar(comando, self._otros)
        if error:
            anunciar(error)
            self._campo_del_error(comando).SetFocus()
            return
        self.EndModal(wx.ID_OK)

    def _campo_del_error(self, comando):
        if _nombre_invalido(comando.nombre):
            return self.txt_palabra
        if any(_nombre_invalido(alias) for alias in comando.alias):
            return self.txt_alias
        ajenos = {normalizar(nombre) for otro in self._otros
                  for nombre in (otro.nombre, *otro.alias)}
        if normalizar(comando.nombre) in ajenos:
            return self.txt_palabra
        if any(normalizar(alias) in ajenos for alias in comando.alias):
            return self.txt_alias
        respuesta = comando.respuesta or ""
        permitidas = (comandos.VARIABLES + ("lista",) if comando.lista
                      else comandos.VARIABLES)
        desconocida = any(variable not in permitidas
                          for variable in _VARIABLE_RE.findall(respuesta))
        if (not respuesta.strip() or desconocida
                or (comando.destino in ("chat", "ambos")
                    and len(respuesta) > comandos.MAXIMO_CHAT)):
            return self.txt_respuesta
        return self.txt_nombres

    def datos(self) -> dict:
        """El comando tal como se guarda."""
        return comandos_guardados.desde_comando(self._comando_de_campos())

    def _al_tecla(self, evento):
        tecla_escape.cancelar_si_escape(self, evento)


class DialogoPalabra(wx.Dialog):
    """Pide una palabra, sin validarla: el bucle de la ventana lo repite."""

    def __init__(self, padre, palabra):
        super().__init__(padre, title=_("Cambiar palabra"),
                         name="DialogoPalabraComando")
        panel = wx.Panel(self, name="PanelPalabra")
        caja = wx.BoxSizer(wx.VERTICAL)
        rotulo = fila_label(panel, _("&Palabra:"))
        self.txt_palabra = wx.TextCtrl(
            panel, name=nombre_de_etiqueta(_("&Palabra:")))
        nombre_accesible(self.txt_palabra, self.txt_palabra.GetName())
        self.txt_palabra.SetValue(palabra)
        formulario.agregar_fila(caja, rotulo, self.txt_palabra, hueco=0)
        self.btn_aceptar = wx.Button(panel, wx.ID_OK, _("&Aceptar"), name=_("Aceptar"))
        self.btn_cancelar = wx.Button(
            panel, wx.ID_CANCEL, _("&Cancelar"), name=_("Cancelar"))
        self.btn_aceptar.SetDefault()
        formulario.agregar_pie(caja, [self.btn_aceptar, self.btn_cancelar])
        formulario.ajustar_tamano(self, panel, caja)
        self.Centre()
        paleta.pintar_ventana(self)
        self.Bind(wx.EVT_CHAR_HOOK, self._al_tecla)
        self.txt_palabra.SetFocus()

    def palabra(self) -> str:
        return self.txt_palabra.GetValue().strip()

    def _al_tecla(self, evento):
        tecla_escape.cancelar_si_escape(self, evento)


def abrir(padre, datos=None, otros=()):
    """Abre el cuadro y devuelve los datos del comando, o None."""
    dialogo = DialogoComando(padre, datos or {}, otros)
    try:
        if dialogo.ShowModal() != wx.ID_OK:
            return None
        return dialogo.datos()
    finally:
        dialogo.Destroy()


def pedir_palabra(padre, palabra) -> str | None:
    """Abre el cuadro de la palabra y devuelve el texto, o None."""
    dialogo = DialogoPalabra(padre, palabra)
    try:
        if dialogo.ShowModal() != wx.ID_OK:
            return None
        return dialogo.palabra()
    finally:
        dialogo.Destroy()
