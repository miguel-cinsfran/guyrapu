# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""La lista de disparadores y sus acciones.

El panel se puede poner dentro de cualquier ventana. Cada cambio se guarda
al momento.
"""

from __future__ import annotations

import wx

from guyrapu.core import paths
from guyrapu.core.idioma import N_, _, ngettext
from guyrapu.interaction import coleccion, disparadores, disparadores_guardados
from guyrapu.interaction import descripcion_disparador, paquetes
from guyrapu.ui import botonera
from guyrapu.ui import disparador_cuadro, confirmar
from guyrapu.ui import paquetes_ventana
from guyrapu.ui.accesibilidad import anunciar, nombre_accesible
from guyrapu.ui.lista_acciones import Accion, ListaConAcciones
from guyrapu.ui.pagina_de_lista import agregar_botones, agregar_lista
from guyrapu.ui.preferencias_comun import fila_label

VACIO = N_(
    "No hay alertas. Una alerta muestra una tarjeta o un medio en el vídeo "
    "cuando llega un regalo, Super Chat, miembro o seguidor. "
    "Usa Agregar para crear una.")


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


class PanelDisparadores(wx.Panel):
    """La lista de disparadores, sus botones y sus acciones."""

    def __init__(self, padre):
        super().__init__(padre, name="PanelDisparadores")
        self._ruta = paths.disparadores()
        self._disparadores = disparadores_guardados.cargar(self._ruta)
        self._crear_controles()

    def _crear_controles(self):
        vs = wx.BoxSizer(wx.VERTICAL)
        rotulo = fila_label(self, _("Lista de &alertas:"))
        self.lista = wx.ListBox(
            self, style=wx.LB_SINGLE | wx.LB_HSCROLL,
            name="ListaDisparadores")
        nombre_accesible(self.lista, _("Alertas guardadas"))
        self._acciones = _acciones(self)
        self._lista = ListaConAcciones(self.lista, self._acciones, _(VACIO))
        self._lista.fijar(self._textos())
        agregar_lista(vs, rotulo, self.lista)
        agregar_botones(vs, self._fila_de_botones())
        self.SetSizer(vs)
        self.lista.SetFocus()

    def _fila_de_botones(self):
        return botonera.armar(self, self._acciones, self._lista)

    def _textos(self):
        return [
            descripcion_disparador.fila(
                disparadores_guardados.a_disparador(disparador))
            for disparador in self._disparadores]

    def _fijar(self, indice=-1):
        self._lista.fijar(self._textos(), indice)
        self.lista.SetFocus()

    def _guardar(self):
        disparadores_guardados.guardar(self._ruta, self._disparadores)

    def _elegido(self):
        return self._lista.indice()

    def _agregar(self):
        datos = disparador_cuadro.abrir(
            self, otros=self._disparadores)
        if datos is None:
            return
        self._disparadores.append(datos)
        self._guardar()
        self._fijar(len(self._disparadores) - 1)
        anunciar(_("Alerta agregada"))

    def _editar(self):
        indice = self._elegido()
        if indice is None:
            return
        actual = self._disparadores[indice]
        otros = [disparador for posicion, disparador
                 in enumerate(self._disparadores) if posicion != indice]
        datos = disparador_cuadro.abrir(self, actual, otros)
        if datos is None:
            return
        self._disparadores[indice] = datos
        self._guardar()
        self._fijar(indice)
        anunciar(_("Alerta guardada"))

    def _renombrar(self):
        indice = self._elegido()
        if indice is None:
            return
        actual = self._disparadores[indice]
        otros = [disparador for posicion, disparador
                 in enumerate(self._disparadores) if posicion != indice]
        nombre = self._pedir_nombre(actual, otros)
        if nombre is None:
            return
        self._disparadores[indice]["nombre"] = nombre
        self._guardar()
        self._fijar(indice)
        anunciar(_("Nombre cambiado"))

    def _pedir_nombre(self, actual, otros):
        while True:
            nombre = disparador_cuadro.pedir_nombre(
                self, actual["nombre"])
            if nombre is None:
                return None
            prueba = disparadores_guardados.a_disparador(
                {**actual, "nombre": nombre})
            error = disparadores.validar(
                prueba, [disparadores_guardados.a_disparador(otro)
                         for otro in otros])
            if not error:
                return prueba.nombre
            anunciar(error)

    def _duplicar(self):
        indice = self._elegido()
        if indice is None:
            return
        copia = dict(self._disparadores[indice])
        copia["nombre"] = coleccion.nombre_de_copia(
            copia.get("nombre", ""), self._disparadores)
        self._disparadores.insert(indice + 1, copia)
        self._guardar()
        self._fijar(indice + 1)
        anunciar(_("Alerta duplicada"))

    def _pausar(self):
        indice = self._elegido()
        if indice is None:
            return
        disparador = self._disparadores[indice]
        disparador["activo"] = not disparador.get("activo", False)
        self._guardar()
        self._fijar(indice)
        anunciar(_("Activo") if disparador["activo"] else _("Pausado"))

    def _escuchar(self):
        indice = self._elegido()
        if indice is None:
            return
        disparador = disparadores_guardados.a_disparador(
            self._disparadores[indice])
        anunciar(descripcion_disparador.escuchar(disparador))

    def _eliminar(self):
        indice = self._elegido()
        if indice is None:
            return
        disparador = self._disparadores[indice]
        nombre = str(disparador.get("nombre", ""))
        if not confirmar.preguntar(
                self,
                _("¿Quieres eliminar la alerta «{nombre}»?").format(
                    nombre=nombre),
                _("Eliminar alerta"), _("&Eliminar"), _("&Cancelar"),
                predeterminado_si=False):
            return
        self._disparadores.pop(indice)
        self._guardar()
        self._fijar(min(indice, len(self._disparadores) - 1))
        anunciar(_("Alerta eliminada"))

    def _exportar(self):
        if not self._disparadores:
            anunciar(_("No hay alertas para exportar."))
            return
        ruta = self._pedir_ruta(guardar=True)
        if not ruta:
            return
        paquetes_ventana.escribir(
            self, ruta, "disparadores", self._disparadores,
            _("Exportar alertas"))

    def _importar(self):
        ruta = self._pedir_ruta(guardar=False)
        if not ruta:
            return
        paquete = paquetes_ventana.leer(
            self, ruta, "disparadores", _("Importar alertas"))
        if paquete is None:
            return
        self._incorporar(paquete.elementos)

    def _incorporar(self, elementos):
        nuevos = [disparadores_guardados.normalizar(elemento)
                  for elemento in elementos]
        for disparador in nuevos:
            disparador["activo"] = False
        repetidos = paquetes.repetidos(nuevos, self._disparadores)
        reemplazar = bool(repetidos) and self._preguntar_reemplazo(repetidos)
        anteriores = {id(disparador) for disparador in self._disparadores}
        self._disparadores = coleccion.combinar(
            self._disparadores, nuevos, reemplazar)
        self._guardar()
        indice = coleccion.primero_nuevo(self._disparadores, anteriores)
        self._fijar(indice)
        anunciar(ngettext("Se importó una alerta.",
                          "Se importaron {n} alertas.",
                          len(nuevos)).format(n=len(nuevos)))

    def _preguntar_reemplazo(self, repetidos):
        return confirmar.preguntar(
            self,
            _("Ya hay alertas llamadas {nombres}. "
              "¿Quieres reemplazarlos?").format(
                  nombres=", ".join(repetidos)),
            _("Importar alertas"), _("&Sí"), _("&No"),
            predeterminado_si=False)

    def _pedir_ruta(self, guardar):
        return paquetes_ventana.pedir_ruta(
            self, _("Exportar alertas") if guardar
            else _("Importar alertas"), guardar)
