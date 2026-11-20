# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Ventana Estilos del vídeo: la lista de estilos y todas sus acciones.

Cada cambio se guarda al momento. La ventana se abre desde el menú
Interacción y los mensajes que usan un estilo lo leen del disco al mostrarse.
"""

from __future__ import annotations

import wx

from guyrapu.capture import programados
from guyrapu.core import paths
from guyrapu.core.idioma import N_, _, ngettext
from guyrapu.interaction import coleccion, paquetes
from guyrapu.obs import descripcion_estilo, estilos_aviso
from guyrapu.ui import botonera
from guyrapu.ui import confirmar, estilo_cuadro, estilo_tipos_cuadro, probar_aviso
from guyrapu.ui.accesibilidad import anunciar, nombre_accesible
from guyrapu.ui.lista_acciones import Accion, ListaConAcciones
from guyrapu.ui.preferencias_comun import fila_label

VACIO = N_("No hay estilos. Usa Agregar para crear uno.")
WILDCARD = N_("Paquete de Guyrapu (*.zip)|*.zip")
MOTIVO_FABRICA = N_("Los estilos de fábrica no se cambian. Usa Duplicar para "
                    "crear uno propio.")


def _acciones(panel):
    return (
        Accion("agregar", _("A&gregar"), panel._agregar,
               necesita_elemento=False),
        Accion("editar", _("&Editar"), panel._editar, tecla="intro"),
        Accion("renombrar", _("Cambiar n&ombre"), panel._renombrar,
               tecla="f2"),
        Accion("duplicar", _("&Duplicar"), panel._duplicar, tecla="ctrl+d"),
        Accion("escuchar", _("Escuc&har"), panel._escuchar),
        Accion("probar", _("Pro&bar"), panel._probar),
        Accion("predeterminado", _("Establecer como &predeterminado…"),
               panel._predeterminado),
        Accion("eliminar", _("E&liminar"), panel._eliminar,
               tecla="suprimir"),
        Accion("exportar", _("Expo&rtar"), panel._exportar,
               necesita_elemento=False),
        Accion("importar", _("&Importar"), panel._importar,
               necesita_elemento=False),
    )


class PanelEstilos(wx.Panel):
    """La lista de estilos con sus acciones, fuera de cualquier ventana."""

    def __init__(self, padre):
        super().__init__(padre, name="PanelEstilos")
        self._ruta = paths.estilos_avisos()
        self._usuario = estilos_aviso.cargar_estilos(self._ruta)
        self._por_tipo = estilos_aviso.cargar_por_tipo(self._ruta)
        self._crear_controles()
        self.lista.SetFocus()

    def _crear_controles(self):
        vs = wx.BoxSizer(wx.VERTICAL)
        vs.Add(fila_label(self, _("Estilos del &vídeo:")), 0,
               wx.LEFT | wx.RIGHT | wx.TOP, 10)
        self.lista = wx.ListBox(
            self, style=wx.LB_SINGLE | wx.LB_HSCROLL, name="ListaEstilosVideo")
        nombre_accesible(self.lista, _("Estilos del vídeo guardados"))
        self._acciones = _acciones(self)
        self._lista = ListaConAcciones(self.lista, self._acciones, _(VACIO))
        self._lista.fijar(self._textos())
        vs.Add(self.lista, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        vs.Add(self._fila_de_botones(), 0,
               wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        self.SetSizer(vs)

    def _fila_de_botones(self):
        return botonera.armar(self, self._acciones, self._lista)

    def _textos(self):
        textos = [self._fila(estilo, True)
                  for estilo in estilos_aviso.FABRICA]
        textos.extend(self._fila(estilo, False) for estilo in self._usuario)
        return textos

    def _fila(self, estilo, de_fabrica):
        texto = (_("{nombre} (de fábrica)").format(nombre=_(estilo["nombre"]))
                 if de_fabrica else _(estilo["nombre"]))
        tipos = _unir([_(nombre).lower()
                       for tipo, nombre in estilos_aviso.TIPOS
                       if self._por_tipo.get(tipo) == estilo["clave"]])
        if tipos:
            texto += _(", predeterminado de {tipos}").format(tipos=tipos)
        return texto

    def _fijar(self, indice=-1):
        self._lista.fijar(self._textos(), indice)
        self.lista.SetFocus()

    def _guardar(self):
        estilos_aviso.guardar_estilos(self._ruta, self._usuario)

    def _elegido(self):
        return self._lista.indice()

    def _es_de_fabrica(self, indice) -> bool:
        return indice < len(estilos_aviso.FABRICA)

    def _posicion_usuario(self, indice) -> int:
        return indice - len(estilos_aviso.FABRICA)

    def _rechazar_fabrica(self):
        anunciar(_(MOTIVO_FABRICA))

    def _agregar(self):
        estilo = estilo_cuadro.abrir(self, otros=self._usuario)
        if estilo is None:
            return
        self._usuario.append(estilo)
        self._guardar()
        self._fijar(len(estilos_aviso.FABRICA) + len(self._usuario) - 1)
        anunciar(_("Estilo agregado"))

    def _editar(self):
        indice = self._elegido()
        if indice is None:
            return
        if self._es_de_fabrica(indice):
            self._rechazar_fabrica()
            return
        posicion = self._posicion_usuario(indice)
        actual = self._usuario[posicion]
        otros = [estilo for lugar, estilo in enumerate(self._usuario)
                 if lugar != posicion]
        estilo = estilo_cuadro.abrir(self, actual, otros)
        if estilo is None:
            return
        self._usuario[posicion] = estilo
        self._guardar()
        self._fijar(indice)
        anunciar(_("Estilo guardado"))

    def _renombrar(self):
        indice = self._elegido()
        if indice is None:
            return
        if self._es_de_fabrica(indice):
            self._rechazar_fabrica()
            return
        posicion = self._posicion_usuario(indice)
        actual = self._usuario[posicion]
        otros = [estilo for lugar, estilo in enumerate(self._usuario)
                 if lugar != posicion]
        nombre = self._pedir_nombre(actual, otros)
        if nombre is None:
            return
        actual["nombre"] = nombre
        self._guardar()
        self._fijar(indice)
        anunciar(_("Nombre cambiado"))

    def _pedir_nombre(self, actual, otros):
        while True:
            nombre = estilo_cuadro.pedir_nombre(self, actual.get("nombre", ""))
            if nombre is None:
                return None
            error = estilos_aviso.validar_estilo(
                dict(actual, nombre=nombre), otros)
            if not error:
                return nombre
            anunciar(error)

    def _duplicar(self):
        indice = self._elegido()
        if indice is None:
            return
        actual = estilos_aviso.todos(self._usuario)[indice]
        copia = dict(actual)
        copia["nombre"] = coleccion.nombre_de_copia(
            actual.get("nombre", ""), estilos_aviso.todos(self._usuario))
        copia["clave"] = estilo_cuadro.clave_nueva(self._usuario)
        if self._es_de_fabrica(indice):
            posicion = len(self._usuario)
        else:
            posicion = self._posicion_usuario(indice) + 1
        self._usuario.insert(posicion, copia)
        self._guardar()
        self._fijar(len(estilos_aviso.FABRICA) + posicion)
        anunciar(_("Estilo duplicado"))

    def _escuchar(self):
        indice = self._elegido()
        if indice is None:
            return
        estilo = estilos_aviso.todos(self._usuario)[indice]
        anunciar(descripcion_estilo.describir(estilo))

    def _probar(self):
        indice = self._elegido()
        if indice is None:
            return
        estilo = estilos_aviso.todos(self._usuario)[indice]
        probar_aviso.probar(
            _("Así se ve un mensaje con este estilo."), estilo)

    def _predeterminado(self):
        indice = self._elegido()
        if indice is None:
            return
        estilo = estilos_aviso.todos(self._usuario)[indice]
        marcados = estilo_tipos_cuadro.abrir(self, {
            tipo for tipo, _nombre in estilos_aviso.TIPOS
            if self._por_tipo.get(tipo) == estilo["clave"]})
        if marcados is None:
            return
        for tipo, _nombre in estilos_aviso.TIPOS:
            if tipo in marcados:
                self._por_tipo[tipo] = estilo["clave"]
            elif self._por_tipo.get(tipo) == estilo["clave"]:
                self._por_tipo[tipo] = "clasico"
        estilos_aviso.guardar_por_tipo(self._ruta, self._por_tipo)
        self._fijar(indice)
        anunciar(_("Predeterminados guardados"))

    def _eliminar(self):
        indice = self._elegido()
        if indice is None:
            return
        if self._es_de_fabrica(indice):
            self._rechazar_fabrica()
            return
        posicion = self._posicion_usuario(indice)
        estilo = self._usuario[posicion]
        ruta = paths.mensajes_programados()
        mensajes = programados.cargar(ruta)
        usados = [mensaje for mensaje in mensajes
                  if mensaje.get("estilo") == estilo["clave"]]
        pregunta = _("¿Quieres eliminar el estilo «{nombre}»?").format(
            nombre=_(estilo.get("nombre", "")))
        if usados:
            pregunta += "\n\n" + _(
                "Lo usan {cantidad} mensajes automáticos. Esos mensajes pasan "
                "a usar Clásico.").format(cantidad=len(usados))
        if not confirmar.preguntar(
                self, pregunta, _("Eliminar estilo del vídeo"),
                _("&Eliminar"), _("&Cancelar"), predeterminado_si=False):
            return
        self._usuario.pop(posicion)
        for tipo, predeterminado in self._por_tipo.items():
            if predeterminado == estilo["clave"]:
                self._por_tipo[tipo] = "clasico"
        self._guardar()
        estilos_aviso.guardar_por_tipo(self._ruta, self._por_tipo)
        if usados:
            for mensaje in mensajes:
                if mensaje.get("estilo") == estilo["clave"]:
                    mensaje["estilo"] = "clasico"
            programados.guardar(ruta, mensajes)
        self._fijar(min(indice, len(self._textos()) - 1))
        anunciar(_("Estilo eliminado"))

    def _exportar(self):
        if not self._usuario:
            anunciar(_("No hay estilos propios para exportar."))
            return
        ruta = self._pedir_ruta(guardar=True)
        if not ruta:
            return
        try:
            paquetes.exportar(ruta, "estilos", self._usuario)
        except Exception as exc:
            confirmar.avisar(
                self, _("No se pudo escribir el paquete:\n\n{exc}").format(
                    exc=exc),
                _("Exportar estilos del vídeo"), _("Aceptar"),
                icono=confirmar.ICON_ERROR)

    def _importar(self):
        ruta = self._pedir_ruta(guardar=False)
        if not ruta:
            return
        try:
            paquete = paquetes.leer(ruta, "estilos")
        except paquetes.PaqueteRechazado as exc:
            confirmar.avisar(
                self, str(exc), _("Importar estilos del vídeo"), _("Aceptar"),
                icono=confirmar.ICON_ERROR)
            return
        self._incorporar(paquete.elementos)

    def _incorporar(self, elementos):
        nuevos = []
        for elemento in elementos:
            estilo = dict(estilos_aviso.FABRICA[0], **elemento)
            nombre = str(estilo.get("nombre", "")).strip()
            if any(_mismo_nombre(nombre, otro)
                   for otro in estilos_aviso.FABRICA):
                estilo["nombre"] = coleccion.nombre_de_copia(
                    nombre, estilos_aviso.todos(self._usuario) + nuevos)
            estilo["clave"] = estilo_cuadro.clave_nueva(
                self._usuario + nuevos)
            nuevos.append(estilo)
        anteriores = {id(estilo) for estilo in self._usuario}
        self._usuario = coleccion.combinar(self._usuario, nuevos, False)
        self._guardar()
        indice = next((len(estilos_aviso.FABRICA) + posicion
                       for posicion, estilo in enumerate(self._usuario)
                       if id(estilo) not in anteriores),
                      len(estilos_aviso.FABRICA))
        self._fijar(indice)
        anunciar(ngettext("Se importó un estilo.",
                          "Se importaron {n} estilos.",
                          len(nuevos)).format(n=len(nuevos)))

    def _pedir_ruta(self, guardar):
        estilo = ((wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) if guardar
                  else (wx.FD_OPEN | wx.FD_FILE_MUST_EXIST))
        dialogo = wx.FileDialog(
            self,
            _("Exportar estilos del vídeo") if guardar
            else _("Importar estilos del vídeo"),
            wildcard=_(WILDCARD), style=estilo)
        try:
            if dialogo.ShowModal() != wx.ID_OK:
                return None
            return dialogo.GetPath()
        finally:
            dialogo.Destroy()

def _unir(textos) -> str:
    """Lista con comas y «y» final, en formatos completos traducibles."""
    if not textos:
        return ""
    if len(textos) == 1:
        return textos[0]
    if len(textos) == 2:
        return _("{a} y {b}").format(a=textos[0], b=textos[1])
    return _("{primeros} y {ultimo}").format(
        primeros=", ".join(textos[:-1]), ultimo=textos[-1])


def _mismo_nombre(nombre, estilo) -> bool:
    return (str(estilo.get("nombre", "")).strip().casefold()
            == nombre.strip().casefold())
