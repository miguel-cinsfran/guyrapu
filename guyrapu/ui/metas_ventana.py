# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""La lista de metas del directo y sus acciones.

El panel se puede poner dentro de cualquier ventana. Cada cambio se guarda
al momento.
"""

from __future__ import annotations

import wx

from guyrapu.core import paths
from guyrapu.core.idioma import N_, _, ngettext
from guyrapu.interaction import coleccion, descripcion_meta, metas
from guyrapu.interaction import metas_guardadas, paquetes
from guyrapu.obs import estilos_aviso
from guyrapu.ui import botonera
from guyrapu.ui import confirmar, meta_cuadro
from guyrapu.ui.accesibilidad import anunciar, nombre_accesible
from guyrapu.ui.lista_acciones import Accion, ListaConAcciones
from guyrapu.ui.preferencias_comun import fila_label

VACIO = N_("No hay metas. Usa Agregar para crear una.")
WILDCARD = N_("Paquete de Guyrapu (*.zip)|*.zip")


def _acciones(panel):
    return (
        Accion("agregar", _("A&gregar"), panel._agregar,
               necesita_elemento=False),
        Accion("editar", _("&Editar"), panel._editar, tecla="intro"),
        Accion("renombrar", _("Cambiar n&ombre"), panel._renombrar,
               tecla="f2"),
        Accion("duplicar", _("&Duplicar"), panel._duplicar, tecla="ctrl+d"),
        Accion("pausar", _("&Pausar o reanudar"), panel._pausar),
        Accion("escuchar", _("Escuc&har"), panel._escuchar),
        Accion("eliminar", _("E&liminar"), panel._eliminar,
               tecla="suprimir"),
        Accion("exportar", _("Expo&rtar"), panel._exportar,
               necesita_elemento=False),
        Accion("importar", _("&Importar"), panel._importar,
               necesita_elemento=False),
    )


class PanelMetas(wx.Panel):
    """La lista de metas, sus botones y sus acciones."""

    def __init__(self, padre):
        super().__init__(padre, name="PanelMetas")
        self._ruta = paths.metas()
        self._metas = metas_guardadas.cargar(self._ruta)
        self._crear_controles()

    def _crear_controles(self):
        vs = wx.BoxSizer(wx.VERTICAL)
        vs.Add(fila_label(self, _("Lista de met&as:")), 0,
               wx.LEFT | wx.RIGHT | wx.TOP, 10)
        self.lista = wx.ListBox(
            self, style=wx.LB_SINGLE | wx.LB_HSCROLL,
            name="ListaMetas")
        nombre_accesible(self.lista, _("Metas guardadas"))
        self._acciones = _acciones(self)
        self._lista = ListaConAcciones(self.lista, self._acciones, _(VACIO))
        self._lista.fijar(self._textos())
        vs.Add(self.lista, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        vs.Add(self._fila_de_botones(), 0,
               wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        self.SetSizer(vs)
        self.lista.SetFocus()

    def _fila_de_botones(self):
        return botonera.armar(self, self._acciones, self._lista)

    def _textos(self):
        return [descripcion_meta.fila(metas_guardadas.a_meta(meta))
                for meta in self._metas]

    def _fijar(self, indice=-1):
        self._lista.fijar(self._textos(), indice)
        self.lista.SetFocus()

    def _guardar(self):
        metas_guardadas.guardar(self._ruta, self._metas)

    def _elegido(self):
        return self._lista.indice()

    def _agregar(self):
        datos = meta_cuadro.abrir(self, otros=self._metas)
        if datos is None:
            return
        self._metas.append(datos)
        self._guardar()
        self._fijar(len(self._metas) - 1)
        anunciar(_("Meta agregada"))

    def _editar(self):
        indice = self._elegido()
        if indice is None:
            return
        actual = self._metas[indice]
        otros = [meta for posicion, meta
                 in enumerate(self._metas) if posicion != indice]
        datos = meta_cuadro.abrir(self, actual, otros)
        if datos is None:
            return
        self._metas[indice] = datos
        self._guardar()
        self._fijar(indice)
        anunciar(_("Meta guardada"))

    def _renombrar(self):
        indice = self._elegido()
        if indice is None:
            return
        actual = self._metas[indice]
        otros = [meta for posicion, meta
                 in enumerate(self._metas) if posicion != indice]
        nombre = self._pedir_nombre(actual, otros)
        if nombre is None:
            return
        self._metas[indice]["nombre"] = nombre
        self._guardar()
        self._fijar(indice)
        anunciar(_("Nombre cambiado"))

    def _pedir_nombre(self, actual, otros):
        while True:
            nombre = meta_cuadro.pedir_nombre(self, actual["nombre"])
            if nombre is None:
                return None
            prueba = metas_guardadas.a_meta({**actual, "nombre": nombre})
            error = metas.validar(
                prueba, [metas_guardadas.a_meta(otro) for otro in otros])
            if not error:
                return prueba.nombre
            anunciar(error)

    def _duplicar(self):
        indice = self._elegido()
        if indice is None:
            return
        copia = dict(self._metas[indice])
        copia["nombre"] = coleccion.nombre_de_copia(
            copia.get("nombre", ""), self._metas)
        self._metas.insert(indice + 1, copia)
        self._guardar()
        self._fijar(indice + 1)
        anunciar(_("Meta duplicada"))

    def _pausar(self):
        indice = self._elegido()
        if indice is None:
            return
        meta = self._metas[indice]
        meta["activa"] = not meta.get("activa", True)
        self._guardar()
        self._fijar(indice)
        anunciar(_("Activa") if meta["activa"] else _("Pausada"))

    def _escuchar(self):
        indice = self._elegido()
        if indice is None:
            return
        meta = metas_guardadas.a_meta(self._metas[indice])
        anunciar(descripcion_meta.escuchar(
            meta, self._nombre_del_estilo(meta.estilo)))

    def _nombre_del_estilo(self, clave):
        usuario = estilos_aviso.cargar_estilos(paths.estilos_avisos())
        por_tipo = estilos_aviso.cargar_por_tipo(paths.estilos_avisos())
        return _(estilos_aviso.buscar_para(
            clave, "meta", usuario, por_tipo)["nombre"])

    def _eliminar(self):
        indice = self._elegido()
        if indice is None:
            return
        meta = self._metas[indice]
        nombre = str(meta.get("nombre", ""))
        if not confirmar.preguntar(
                self,
                _("¿Quieres eliminar la meta «{nombre}»?").format(
                    nombre=nombre),
                _("Eliminar meta"), _("&Eliminar"), _("&Cancelar"),
                predeterminado_si=False):
            return
        self._metas.pop(indice)
        self._guardar()
        self._fijar(min(indice, len(self._metas) - 1))
        anunciar(_("Meta eliminada"))

    def _exportar(self):
        if not self._metas:
            anunciar(_("No hay metas para exportar."))
            return
        ruta = self._pedir_ruta(guardar=True)
        if not ruta:
            return
        try:
            paquetes.exportar(ruta, "metas", self._metas)
        except Exception as exc:
            confirmar.avisar(
                self,
                _("No se pudo escribir el paquete:\n\n{exc}").format(
                    exc=exc),
                _("Exportar metas"), _("Aceptar"),
                icono=confirmar.ICON_ERROR)

    def _importar(self):
        ruta = self._pedir_ruta(guardar=False)
        if not ruta:
            return
        try:
            paquete = paquetes.leer(ruta, "metas")
        except paquetes.PaqueteRechazado as exc:
            confirmar.avisar(
                self, str(exc), _("Importar metas"),
                _("Aceptar"), icono=confirmar.ICON_ERROR)
            return
        self._incorporar(paquete.elementos)

    def _incorporar(self, elementos):
        nuevos = [metas_guardadas.desde_meta(
            metas_guardadas.a_meta(elemento))
            for elemento in elementos]
        for meta in nuevos:
            meta["activa"] = False
        repetidos = paquetes.repetidos(nuevos, self._metas)
        reemplazar = bool(repetidos) and self._preguntar_reemplazo(repetidos)
        anteriores = {id(meta) for meta in self._metas}
        self._metas = coleccion.combinar(self._metas, nuevos, reemplazar)
        self._guardar()
        indice = next((posicion for posicion, meta
                       in enumerate(self._metas)
                       if id(meta) not in anteriores), 0)
        self._fijar(indice)
        anunciar(ngettext("Se importó una meta.",
                          "Se importaron {n} metas.",
                          len(nuevos)).format(n=len(nuevos)))

    def _preguntar_reemplazo(self, repetidos):
        return confirmar.preguntar(
            self,
            _("Ya hay metas llamadas {nombres}. "
              "¿Quieres reemplazarlas?").format(
                  nombres=", ".join(repetidos)),
            _("Importar metas"), _("&Sí"), _("&No"),
            predeterminado_si=False)

    def _pedir_ruta(self, guardar):
        estilo = ((wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) if guardar
                  else (wx.FD_OPEN | wx.FD_FILE_MUST_EXIST))
        dialogo = wx.FileDialog(
            self,
            _("Exportar metas") if guardar
            else _("Importar metas"),
            wildcard=_(WILDCARD), style=estilo)
        try:
            if dialogo.ShowModal() != wx.ID_OK:
                return None
            return dialogo.GetPath()
        finally:
            dialogo.Destroy()
