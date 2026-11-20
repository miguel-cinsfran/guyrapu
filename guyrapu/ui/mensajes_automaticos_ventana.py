# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Mensajes automáticos: la lista y todas sus acciones.

Cada cambio se guarda al momento. El panel vive en la ventana Interacción y,
al cerrarla, la ventana principal relee la lista del disco.
"""

from __future__ import annotations

import wx

from guyrapu.core import paths
from guyrapu.core.idioma import N_, _, ngettext
from guyrapu.capture import programados
from guyrapu.interaction import coleccion, paquetes
from guyrapu.obs import estilos_aviso
from guyrapu.ui import botonera
from guyrapu.ui import confirmar
from guyrapu.ui import mensaje_automatico_cuadro, probar_aviso
from guyrapu.ui.accesibilidad import anunciar, nombre_accesible
from guyrapu.ui.lista_acciones import Accion, ListaConAcciones
from guyrapu.ui.preferencias_comun import ANCHO_NOTA, fila_label
from guyrapu.ui.tema import _T

EXPLICACION = N_(
    "Los mensajes automáticos salen cada cierto tiempo en el chat de tu "
    "directo, en el vídeo o en los dos. En el chat necesitan sesión de Google "
    "iniciada y un directo de YouTube conectado. El intervalo mínimo son 5 "
    "minutos y cada mensaje admite 200 caracteres. YouTube suele bloquear los "
    "enlaces en el chat del directo: conviene escribir el nombre de usuario en "
    "vez del enlace completo.")
VACIO = N_("No hay mensajes automáticos. Usa Agregar para crear uno.")
WILDCARD = N_("Paquete de Guyrapu (*.zip)|*.zip")


def _acciones(panel):
    return (
        Accion("agregar", _("A&gregar"), panel._agregar,
               necesita_elemento=False),
        Accion("editar", _("&Editar"), panel._editar, tecla="intro"),
        Accion("renombrar", _("Cambiar n&ombre"), panel._renombrar,
               tecla="f2"),
        Accion("duplicar", _("&Duplicar"), panel._duplicar, tecla="ctrl+d"),
        Accion("subir", _("&Subir"), lambda: panel._mover(-1)),
        Accion("bajar", _("Ba&jar"), lambda: panel._mover(1)),
        Accion("pausar", _("&Pausar o reanudar"), panel._pausar),
        Accion("escuchar", _("Escuc&har"), panel._escuchar),
        Accion("probar", _("Pro&bar"), panel._probar),
        Accion("eliminar", _("E&liminar"), panel._eliminar,
               tecla="suprimir"),
        Accion("exportar", _("Expo&rtar"), panel._exportar,
               necesita_elemento=False),
        Accion("importar", _("&Importar"), panel._importar,
               necesita_elemento=False),
    )


class PanelMensajesAutomaticos(wx.Panel):
    """La lista de mensajes automáticos con sus acciones, fuera de cualquier ventana."""

    def __init__(self, padre, principal):
        super().__init__(padre, name="PanelMensajesAutomaticos")
        self._padre = principal
        self._ruta = paths.mensajes_programados()
        self._mensajes = programados.cargar(self._ruta)
        self._crear_controles()
        self.lista.SetFocus()

    def _crear_controles(self):
        vs = wx.BoxSizer(wx.VERTICAL)
        nota = wx.StaticText(self, name="ExplicacionMensajes", label=_(EXPLICACION))
        nota.SetForegroundColour(_T.dim)
        nota.Wrap(ANCHO_NOTA)
        vs.Add(nota, 0, wx.ALL, 10)

        self.chk_programados = wx.CheckBox(
            self, label=_("Acti&var mensajes automáticos"),
            name="ActivarProgramados")
        self.chk_programados.SetValue(
            bool(self._padre._config.get("programados_activo", False)))
        self.chk_programados.Bind(wx.EVT_CHECKBOX, self._al_alternar)
        vs.Add(self.chk_programados, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        vs.Add(fila_label(self, _("Lista de &mensajes:")), 0,
               wx.LEFT | wx.RIGHT, 10)
        self.lista = wx.ListBox(
            self, style=wx.LB_SINGLE | wx.LB_HSCROLL, name="ListaProgramados")
        nombre_accesible(self.lista, _("Mensajes automáticos guardados"))
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
        return [programados.describir_mensaje(mensaje)
                for mensaje in self._mensajes]

    def _fijar(self, indice=-1):
        self._lista.fijar(self._textos(), indice)
        self.lista.SetFocus()

    def _guardar(self):
        programados.guardar(self._ruta, self._mensajes)

    def _elegido(self):
        return self._lista.indice()

    def _al_alternar(self, _evento):
        from guyrapu.ui import comando_mensajes_automaticos
        comando_mensajes_automaticos.alternar(self._padre)
        self.chk_programados.SetValue(
            bool(self._padre._config.get("programados_activo", False)))

    def _agregar(self):
        mensaje = mensaje_automatico_cuadro.abrir(self, otros=self._mensajes)
        if mensaje is None:
            return
        mensaje["proximo"] = 0.0
        self._mensajes.append(mensaje)
        self._guardar()
        self._fijar(len(self._mensajes) - 1)
        anunciar(_("Mensaje agregado"))

    def _editar(self):
        indice = self._elegido()
        if indice is None:
            return
        actual = self._mensajes[indice]
        otros = [m for posicion, m in enumerate(self._mensajes)
                 if posicion != indice]
        mensaje = mensaje_automatico_cuadro.abrir(self, actual, otros)
        if mensaje is None:
            return
        mensaje["proximo"] = actual.get("proximo", 0.0)
        self._mensajes[indice] = mensaje
        self._guardar()
        self._fijar(indice)
        anunciar(_("Mensaje guardado"))

    def _renombrar(self):
        indice = self._elegido()
        if indice is None:
            return
        otros = [m["nombre"] for posicion, m in enumerate(self._mensajes)
                 if posicion != indice]
        nombre = self._pedir_nombre(self._mensajes[indice]["nombre"], otros)
        if nombre is None:
            return
        self._mensajes[indice]["nombre"] = nombre
        self._guardar()
        self._fijar(indice)
        anunciar(_("Nombre cambiado"))

    def _pedir_nombre(self, actual, otros):
        while True:
            nombre = mensaje_automatico_cuadro.pedir_nombre(self, actual)
            if nombre is None:
                return None
            error = programados.validar_nombre(nombre, otros)
            if not error:
                return nombre
            anunciar(error)

    def _duplicar(self):
        indice = self._elegido()
        if indice is None:
            return
        copia = dict(self._mensajes[indice])
        copia["nombre"] = coleccion.nombre_de_copia(
            copia.get("nombre", ""), self._mensajes)
        copia["proximo"] = 0.0
        self._mensajes.insert(indice + 1, copia)
        self._guardar()
        self._fijar(indice + 1)
        anunciar(_("Mensaje duplicado"))

    def _mover(self, paso):
        indice = self._elegido()
        if indice is None:
            return
        nuevo = coleccion.mover(self._mensajes, indice, paso)
        if nuevo is None:
            self._anunciar_posicion(indice)
            return
        self._guardar()
        self._fijar(nuevo)
        self._anunciar_posicion(nuevo)

    def _anunciar_posicion(self, indice):
        anunciar(_("Posición {n} de {total}").format(
            n=indice + 1, total=len(self._mensajes)))

    def _pausar(self):
        indice = self._elegido()
        if indice is None:
            return
        mensaje = self._mensajes[indice]
        mensaje["activo"] = not mensaje.get("activo", False)
        self._guardar()
        self._fijar(indice)
        anunciar(_("Activo") if mensaje["activo"] else _("Pausado"))

    def _escuchar(self):
        indice = self._elegido()
        if indice is None:
            return
        mensaje = self._mensajes[indice]
        texto = mensaje.get("texto", "")
        if mensaje.get("destino") not in ("video", "ambos"):
            anunciar(texto)
            return
        usuario = estilos_aviso.cargar_estilos(paths.estilos_avisos())
        por_tipo = estilos_aviso.cargar_por_tipo(paths.estilos_avisos())
        estilo = estilos_aviso.buscar_para(
            mensaje.get("estilo", ""), "mensaje", usuario, por_tipo)
        anunciar(_("{texto}. Estilo: {estilo}.").format(
            texto=texto, estilo=_(estilo.get("nombre", ""))))

    def _probar(self):
        indice = self._elegido()
        if indice is None:
            return
        mensaje = self._mensajes[indice]
        texto = mensaje.get("texto", "")
        if mensaje.get("destino") not in ("video", "ambos"):
            probar_aviso.probar(None, None, al_chat=texto)
            return
        usuario = estilos_aviso.cargar_estilos(paths.estilos_avisos())
        por_tipo = estilos_aviso.cargar_por_tipo(paths.estilos_avisos())
        estilo = estilos_aviso.buscar_para(
            mensaje.get("estilo", ""), "mensaje", usuario, por_tipo)
        if mensaje.get("destino") == "ambos":
            probar_aviso.probar(texto, estilo, al_chat=texto)
        else:
            probar_aviso.probar(texto, estilo)

    def _eliminar(self):
        indice = self._elegido()
        if indice is None:
            return
        mensaje = self._mensajes[indice]
        if not confirmar.preguntar(
                self,
                _("¿Quieres eliminar el mensaje «{nombre}»?").format(
                    nombre=mensaje.get("nombre", "")),
                _("Eliminar mensaje automático"), _("&Eliminar"),
                _("&Cancelar"), predeterminado_si=False):
            return
        self._mensajes.pop(indice)
        self._guardar()
        self._fijar(min(indice, len(self._mensajes) - 1))
        anunciar(_("Mensaje eliminado"))

    def _exportar(self):
        if not self._mensajes:
            anunciar(_("No hay mensajes automáticos para exportar."))
            return
        ruta = self._pedir_ruta(guardar=True)
        if not ruta:
            return
        try:
            paquetes.exportar(ruta, "avisos", self._mensajes)
        except Exception as exc:
            confirmar.avisar(
                self, _("No se pudo escribir el paquete:\n\n{exc}").format(exc=exc),
                _("Exportar mensajes automáticos"), _("Aceptar"),
                icono=confirmar.ICON_ERROR)

    def _importar(self):
        ruta = self._pedir_ruta(guardar=False)
        if not ruta:
            return
        try:
            paquete = paquetes.leer(ruta, "avisos")
        except paquetes.PaqueteRechazado as exc:
            confirmar.avisar(
                self, str(exc), _("Importar mensajes automáticos"),
                _("Aceptar"), icono=confirmar.ICON_ERROR)
            return
        self._incorporar(paquete.elementos)

    def _incorporar(self, elementos):
        nuevos = [programados._normalizar_mensaje(elemento)
                  for elemento in elementos]
        for mensaje in nuevos:
            mensaje["activo"] = False
            mensaje["proximo"] = 0.0
        repetidos = paquetes.repetidos(nuevos, self._mensajes)
        reemplazar = bool(repetidos) and self._preguntar_reemplazo(repetidos)
        anteriores = {id(mensaje) for mensaje in self._mensajes}
        self._mensajes = coleccion.combinar(
            self._mensajes, nuevos, reemplazar)
        self._guardar()
        indice = next((posicion for posicion, mensaje
                       in enumerate(self._mensajes)
                       if id(mensaje) not in anteriores), 0)
        self._fijar(indice)
        anunciar(ngettext("Se importó un mensaje.",
                          "Se importaron {n} mensajes.",
                          len(nuevos)).format(n=len(nuevos)))

    def _preguntar_reemplazo(self, repetidos):
        return confirmar.preguntar(
            self,
            _("Ya hay mensajes llamados {nombres}. "
              "¿Quieres reemplazarlos?").format(nombres=", ".join(repetidos)),
            _("Importar mensajes automáticos"), _("&Sí"), _("&No"),
            predeterminado_si=False)

    def _pedir_ruta(self, guardar):
        estilo = ((wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) if guardar
                  else (wx.FD_OPEN | wx.FD_FILE_MUST_EXIST))
        dialogo = wx.FileDialog(
            self,
            _("Exportar mensajes automáticos") if guardar
            else _("Importar mensajes automáticos"),
            wildcard=_(WILDCARD), style=estilo)
        try:
            if dialogo.ShowModal() != wx.ID_OK:
                return None
            return dialogo.GetPath()
        finally:
            dialogo.Destroy()
