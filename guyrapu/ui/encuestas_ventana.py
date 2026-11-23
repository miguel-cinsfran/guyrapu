# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""La página de las encuestas guardadas y sus acciones.

El panel se puede poner dentro de cualquier ventana. Cada cambio se guarda
al momento.
"""

from __future__ import annotations

import wx

from guyrapu.core import paths
from guyrapu.core.idioma import N_, _, ngettext
from guyrapu.interaction import coleccion, encuestas_guardadas, paquetes
from guyrapu.ui import botonera
from guyrapu.ui import confirmar, encuesta_cuadro, encuesta_en_vivo
from guyrapu.ui import paquetes_ventana
from guyrapu.ui.accesibilidad import anunciar, nombre_accesible
from guyrapu.ui.lista_acciones import Accion, ListaConAcciones
from guyrapu.ui.preferencias_comun import fila_label

VACIO = N_(
    "No hay encuestas. Aquí aparecen las encuestas listas para iniciar en el "
    "directo. El público vota con un número precedido de un signo de "
    "exclamación, como 1 o 2. Usa Agregar para crear una.")


def _ventana(panel):
    """La ventana principal, aunque el panel viva dentro del cuadro Interacción."""
    ventana = panel.GetTopLevelParent()
    padre = ventana.GetParent()
    return padre if padre is not None else ventana


def _acciones(panel):
    return (
        Accion("agregar", _("A&gregar"), panel._agregar,
               necesita_elemento=False),
        Accion("editar", _("&Editar"), panel._editar, tecla="intro"),
        Accion("iniciar", _("Inici&ar"), panel._iniciar),
        Accion("duplicar", _("&Duplicar"), panel._duplicar, tecla="ctrl+d"),
        Accion("escuchar", _("Escuc&har"), panel._escuchar),
        Accion("eliminar", _("E&liminar"), panel._eliminar,
               tecla="suprimir"),
        Accion("exportar", _("Expo&rtar"), panel._exportar,
               necesita_elemento=False),
        Accion("importar", _("&Importar"), panel._importar,
               necesita_elemento=False),
    )


class PanelEncuestas(wx.Panel):
    """La lista de encuestas, sus botones y sus acciones."""

    def __init__(self, padre):
        super().__init__(padre, name="PanelEncuestas")
        self._ruta = paths.encuestas()
        self._encuestas = encuestas_guardadas.cargar(self._ruta)
        self._crear_controles()

    def _crear_controles(self):
        vs = wx.BoxSizer(wx.VERTICAL)
        vs.Add(fila_label(self, _("Lista de e&ncuestas:")), 0,
               wx.LEFT | wx.RIGHT | wx.TOP, 10)
        self.lista = wx.ListBox(
            self, style=wx.LB_SINGLE | wx.LB_HSCROLL, name="ListaEncuestas")
        nombre_accesible(self.lista, _("Encuestas guardadas"))
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
        return [encuestas_guardadas.fila(encuesta)
                for encuesta in self._encuestas]

    def _fijar(self, indice=-1):
        self._lista.fijar(self._textos(), indice)
        self.lista.SetFocus()

    def _guardar(self):
        encuestas_guardadas.guardar(self._ruta, self._encuestas)

    def _elegido(self):
        return self._lista.indice()

    def _agregar(self):
        datos = encuesta_cuadro.abrir(self)
        if datos is None:
            return
        self._encuestas.append(encuestas_guardadas.normalizar(datos))
        self._guardar()
        self._fijar(len(self._encuestas) - 1)
        anunciar(_("Encuesta agregada"))

    def _editar(self):
        indice = self._elegido()
        if indice is None:
            return
        datos = encuesta_cuadro.abrir(self, self._encuestas[indice])
        if datos is None:
            return
        self._encuestas[indice] = encuestas_guardadas.normalizar(datos)
        self._guardar()
        self._fijar(indice)
        anunciar(_("Encuesta guardada"))

    def _iniciar(self):
        indice = self._elegido()
        if indice is None:
            return
        ventana = _ventana(self)
        if encuesta_en_vivo.abierta(ventana):
            if not confirmar.preguntar(
                    self,
                    _("Ya hay una encuesta abierta. ¿Quieres cerrarla y abrir "
                      "la nueva?"),
                    _("Iniciar encuesta"), _("&Sí"), _("&No"),
                    predeterminado_si=False):
                return
            encuesta_en_vivo.cerrar(ventana)
        encuesta_en_vivo.iniciar(ventana, self._encuestas[indice])

    def _duplicar(self):
        indice = self._elegido()
        if indice is None:
            return
        copia = dict(self._encuestas[indice])
        nombre = coleccion.nombre_de_copia(
            copia.get("pregunta", ""), self._encuestas)
        copia["pregunta"] = nombre
        copia["nombre"] = nombre
        self._encuestas.insert(indice + 1, copia)
        self._guardar()
        self._fijar(indice + 1)
        anunciar(_("Encuesta duplicada"))

    def _escuchar(self):
        indice = self._elegido()
        if indice is None:
            return
        anunciar(encuestas_guardadas.escuchar(self._encuestas[indice]))

    def _eliminar(self):
        indice = self._elegido()
        if indice is None:
            return
        encuesta = self._encuestas[indice]
        if not confirmar.preguntar(
                self,
                _("¿Quieres eliminar la encuesta «{pregunta}»?").format(
                    pregunta=encuesta.get("pregunta", "")),
                _("Eliminar encuesta"), _("&Eliminar"), _("&Cancelar"),
                predeterminado_si=False):
            return
        self._encuestas.pop(indice)
        self._guardar()
        self._fijar(min(indice, len(self._encuestas) - 1))
        anunciar(_("Encuesta eliminada"))

    def _exportar(self):
        if not self._encuestas:
            anunciar(_("No hay encuestas para exportar."))
            return
        ruta = self._pedir_ruta(guardar=True)
        if not ruta:
            return
        paquetes_ventana.escribir(
            self, ruta, "encuestas", self._encuestas, _("Exportar encuestas"))

    def _importar(self):
        ruta = self._pedir_ruta(guardar=False)
        if not ruta:
            return
        paquete = paquetes_ventana.leer(
            self, ruta, "encuestas", _("Importar encuestas"))
        if paquete is None:
            return
        self._incorporar(paquete.elementos)

    def _incorporar(self, elementos):
        nuevos = [encuestas_guardadas.normalizar(elemento)
                  for elemento in elementos]
        repetidos = paquetes.repetidos(nuevos, self._encuestas)
        reemplazar = bool(repetidos) and self._preguntar_reemplazo(repetidos)
        anteriores = {id(encuesta) for encuesta in self._encuestas}
        self._encuestas = coleccion.combinar(
            self._encuestas, nuevos, reemplazar)
        for encuesta in self._encuestas:
            encuesta["pregunta"] = encuesta["nombre"]
        self._guardar()
        indice = coleccion.primero_nuevo(self._encuestas, anteriores)
        self._fijar(indice)
        anunciar(ngettext("Se importó una encuesta.",
                          "Se importaron {n} encuestas.",
                          len(nuevos)).format(n=len(nuevos)))

    def _preguntar_reemplazo(self, repetidos):
        return confirmar.preguntar(
            self,
            _("Ya hay encuestas llamadas {nombres}. "
              "¿Quieres reemplazarlas?").format(nombres=", ".join(repetidos)),
            _("Importar encuestas"), _("&Sí"), _("&No"),
            predeterminado_si=False)

    def _pedir_ruta(self, guardar):
        return paquetes_ventana.pedir_ruta(
            self, _("Exportar encuestas") if guardar
            else _("Importar encuestas"), guardar)
