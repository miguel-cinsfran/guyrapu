# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""La lista de comandos del chat y sus acciones.

El panel se puede poner dentro de cualquier ventana. Cada cambio se guarda
al momento.
"""

from __future__ import annotations

import wx

from guyrapu.core import paths
from guyrapu.core.idioma import N_, _, ngettext
from guyrapu.interaction import coleccion, comandos, comandos_guardados
from guyrapu.interaction import descripcion_comando, paquetes
from guyrapu.obs import estilos_aviso
from guyrapu.ui import botonera
from guyrapu.ui import comando_cuadro, confirmar
from guyrapu.ui import paquetes_ventana
from guyrapu.ui.accesibilidad import anunciar, nombre_accesible
from guyrapu.ui.lista_acciones import Accion, ListaConAcciones
from guyrapu.ui.pagina_de_lista import agregar_botones, agregar_lista
from guyrapu.ui.preferencias_comun import fila_label

VACIO = N_(
    "No hay comandos. Aquí aparecen las palabras que el público escribe en "
    "el chat con un signo de exclamación delante, como hola. "
    "También aparece lo que responde cada una. Usa Agregar para crear uno.")
MOTIVO_LISTA = N_("La lista de comandos no se puede eliminar ni duplicar")


def _acciones(panel):
    return (
        Accion("agregar", _("A&gregar"), panel._agregar,
               necesita_elemento=False),
        Accion("editar", _("&Editar"), panel._editar, tecla="intro"),
        Accion("renombrar", _("Cambiar p&alabra"), panel._renombrar,
               tecla="f2"),
        Accion("duplicar", _("&Duplicar"), panel._duplicar, tecla="ctrl+d",
               motivo_indices=panel._motivo_lista),
        Accion("pausar", _("&Pausar o reanudar"), panel._pausar),
        Accion("escuchar", _("Escuc&har"), panel._escuchar),
        Accion("eliminar", _("E&liminar"), panel._eliminar,
               tecla="suprimir", motivo_indices=panel._motivo_lista),
        Accion("exportar", _("Expo&rtar"), panel._exportar,
               necesita_elemento=False),
        Accion("importar", _("&Importar"), panel._importar,
               necesita_elemento=False),
    )


class PanelComandos(wx.Panel):
    """La lista de comandos, sus botones y sus acciones."""

    def __init__(self, padre):
        super().__init__(padre, name="PanelComandos")
        self._ruta = paths.comandos()
        self._comandos = comandos_guardados.cargar(self._ruta)
        self._crear_controles()

    def _crear_controles(self):
        vs = wx.BoxSizer(wx.VERTICAL)
        rotulo = fila_label(self, _("Lista de c&omandos:"))
        self.lista = wx.ListBox(
            self, style=wx.LB_SINGLE | wx.LB_HSCROLL, name="ListaComandos")
        nombre_accesible(self.lista, _("Comandos del chat guardados"))
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
        return [descripcion_comando.fila(comandos_guardados.a_comando(comando))
                for comando in self._comandos]

    def _fijar(self, indice=-1):
        self._lista.fijar(self._textos(), indice)
        self.lista.SetFocus()

    def _guardar(self):
        comandos_guardados.guardar(self._ruta, self._comandos)

    def _elegido(self):
        return self._lista.indice()

    def _motivo_lista(self, indices):
        if any(0 <= indice < len(self._comandos)
               and self._comandos[indice].get("lista") for indice in indices):
            return _(MOTIVO_LISTA)
        return ""

    def _agregar(self):
        datos = comando_cuadro.abrir(self, otros=self._comandos)
        if datos is None:
            return
        self._comandos.append(datos)
        self._guardar()
        self._fijar(len(self._comandos) - 1)
        anunciar(_("Comando agregado"))

    def _editar(self):
        indice = self._elegido()
        if indice is None:
            return
        actual = self._comandos[indice]
        otros = [comando for posicion, comando in enumerate(self._comandos)
                 if posicion != indice]
        datos = comando_cuadro.abrir(self, actual, otros)
        if datos is None:
            return
        self._comandos[indice] = datos
        self._guardar()
        self._fijar(indice)
        anunciar(_("Comando guardado"))

    def _renombrar(self):
        indice = self._elegido()
        if indice is None:
            return
        actual = self._comandos[indice]
        otros = [comando for posicion, comando in enumerate(self._comandos)
                 if posicion != indice]
        palabra = self._pedir_palabra(actual, otros)
        if palabra is None:
            return
        self._comandos[indice]["nombre"] = palabra
        self._guardar()
        self._fijar(indice)
        anunciar(_("Palabra cambiada"))

    def _pedir_palabra(self, actual, otros):
        while True:
            palabra = comando_cuadro.pedir_palabra(self, actual["nombre"])
            if palabra is None:
                return None
            prueba = comandos_guardados.a_comando(
                {**actual, "nombre": palabra})
            error = comandos.validar(
                prueba, [comandos_guardados.a_comando(otro)
                         for otro in otros])
            if not error:
                return prueba.nombre
            anunciar(error)

    def _duplicar(self):
        indice = self._elegido()
        if indice is None:
            return
        copia = dict(self._comandos[indice])
        copia["nombre"] = coleccion.nombre_de_copia(
            copia.get("nombre", ""), self._comandos)
        self._comandos.insert(indice + 1, copia)
        self._guardar()
        self._fijar(indice + 1)
        anunciar(_("Comando duplicado"))

    def _pausar(self):
        indice = self._elegido()
        if indice is None:
            return
        comando = self._comandos[indice]
        comando["activo"] = not comando.get("activo", False)
        self._guardar()
        self._fijar(indice)
        anunciar(_("Activo") if comando["activo"] else _("Pausado"))

    def _escuchar(self):
        indice = self._elegido()
        if indice is None:
            return
        comando = comandos_guardados.a_comando(self._comandos[indice])
        estilo = ""
        if comando.destino in ("video", "ambos"):
            estilos = estilos_aviso.cargar_estilos(paths.estilos_avisos())
            por_tipo = estilos_aviso.cargar_por_tipo(paths.estilos_avisos())
            elegido = estilos_aviso.buscar_para(
                comando.estilo, "comando", estilos, por_tipo)
            estilo = _(elegido.get("nombre", ""))
        anunciar(descripcion_comando.escuchar(comando, estilo))

    def _eliminar(self):
        indice = self._elegido()
        if indice is None:
            return
        comando = self._comandos[indice]
        nombre = "!" + str(comando.get("nombre", ""))
        if not confirmar.preguntar(
                self,
                _("¿Quieres eliminar el comando «{nombre}»?").format(
                    nombre=nombre),
                _("Eliminar comando"), _("&Eliminar"), _("&Cancelar"),
                predeterminado_si=False):
            return
        self._comandos.pop(indice)
        self._guardar()
        self._fijar(min(indice, len(self._comandos) - 1))
        anunciar(_("Comando eliminado"))

    def _exportar(self):
        if not self._comandos:
            anunciar(_("No hay comandos para exportar."))
            return
        ruta = self._pedir_ruta(guardar=True)
        if not ruta:
            return
        paquetes_ventana.escribir(
            self, ruta, "comandos", self._comandos, _("Exportar comandos"))

    def _importar(self):
        ruta = self._pedir_ruta(guardar=False)
        if not ruta:
            return
        paquete = paquetes_ventana.leer(
            self, ruta, "comandos", _("Importar comandos"))
        if paquete is None:
            return
        self._incorporar(paquete.elementos)

    def _incorporar(self, elementos):
        nuevos = [comandos_guardados.normalizar(elemento)
                  for elemento in elementos]
        for comando in nuevos:
            comando["activo"] = False
            comando["lista"] = False
        repetidos = paquetes.repetidos(nuevos, self._comandos)
        reemplazar = bool(repetidos) and self._preguntar_reemplazo(repetidos)
        anteriores = {id(comando) for comando in self._comandos}
        self._comandos = coleccion.combinar(
            self._comandos, nuevos, reemplazar)
        self._guardar()
        indice = coleccion.primero_nuevo(self._comandos, anteriores)
        self._fijar(indice)
        anunciar(ngettext("Se importó un comando.",
                          "Se importaron {n} comandos.",
                          len(nuevos)).format(n=len(nuevos)))

    def _preguntar_reemplazo(self, repetidos):
        return confirmar.preguntar(
            self,
            _("Ya hay comandos llamados {nombres}. "
              "¿Quieres reemplazarlos?").format(nombres=", ".join(repetidos)),
            _("Importar comandos"), _("&Sí"), _("&No"),
            predeterminado_si=False)

    def _pedir_ruta(self, guardar):
        return paquetes_ventana.pedir_ruta(
            self, _("Exportar comandos") if guardar
            else _("Importar comandos"), guardar)
