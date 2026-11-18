# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""La página de la biblioteca de medios y sus acciones.

El panel se puede poner dentro de cualquier ventana. Cada cambio se guarda
al momento. La escucha previa suena con libVLC, sin vídeo.
"""

from __future__ import annotations

import threading

import wx

from guyrapu.core import paths
from guyrapu.core.idioma import N_, _, ngettext
from guyrapu.interaction import (
    ajustes_interaccion, coleccion, medios, medios_guardados, paquetes)
from guyrapu.music import consultas_vlc
from guyrapu.ui import confirmar, medio_cuadro, medios_medicion
from guyrapu.ui.accesibilidad import (
    ContadorAccesible, anunciar, nombre_accesible)
from guyrapu.ui.lista_acciones import Accion, ListaConAcciones
from guyrapu.ui.medio_escucha import EscuchaPrevia
from guyrapu.ui.preferencias_comun import fila_label, nombre_de_etiqueta
from guyrapu.voice import sound_player

VACIO = N_("No hay medios. Usa Agregar para crear uno.")
WILDCARD = N_("Paquete de Guyrapu (*.zip)|*.zip")
PLAZO_DURACION = 1.4


def duracion_de(ruta) -> int:
    """Los segundos del archivo, o 0 si no se pudo leer a tiempo.

    libVLC se mide en un hilo y la interfaz espera menos de un segundo y
    medio: si el motor todavía no está listo, el medio queda con duración
    desconocida en vez de congelar la ventana.
    """
    resultado = {}
    listo = threading.Event()

    def medir():
        try:
            datos = consultas_vlc.leer_etiquetas_vlc(str(ruta), plazo_ms=1200)
            resultado["ms"] = datos.get("duracion_ms") or 0
        finally:
            listo.set()

    threading.Thread(target=medir, daemon=True).start()
    if not listo.wait(PLAZO_DURACION):
        return 0
    return max(0, round(resultado.get("ms", 0) / 1000))


def _acciones(panel):
    return (
        Accion("agregar", _("A&gregar"), panel._agregar,
               necesita_elemento=False),
        Accion("editar", _("&Editar"), panel._editar, tecla="intro"),
        Accion("duplicar", _("&Duplicar"), panel._duplicar, tecla="ctrl+d"),
        Accion("escuchar", _("Escuc&har"), panel._escuchar),
        Accion("eliminar", _("E&liminar"), panel._eliminar,
               tecla="suprimir"),
        Accion("exportar", _("Expo&rtar"), panel._exportar,
               necesita_elemento=False),
        Accion("importar", _("&Importar"), panel._importar,
               necesita_elemento=False),
    )


class PanelMedios(wx.Panel):
    """La lista de medios, sus botones y sus acciones."""

    def __init__(self, padre):
        super().__init__(padre, name="PanelMedios")
        self._ruta = paths.medios()
        self._carpeta = paths.carpeta_medios()
        self._medios = medios_guardados.cargar(self._ruta)
        self._escucha = EscuchaPrevia()
        self._crear_controles()

    def _crear_controles(self):
        vs = wx.BoxSizer(wx.VERTICAL)
        vs.Add(fila_label(self, _("Lista de &medios:")), 0,
               wx.LEFT | wx.RIGHT | wx.TOP, 10)
        self.lista = wx.ListBox(
            self, style=wx.LB_SINGLE | wx.LB_HSCROLL, name="ListaMedios")
        nombre_accesible(self.lista, _("Medios guardados"))
        self._acciones = _acciones(self)
        self._lista = ListaConAcciones(self.lista, self._acciones, _(VACIO))
        self._lista.fijar(self._textos())
        vs.Add(self.lista, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        etiqueta_volumen = _("&Volumen de los medios en el vídeo:")
        vs.Add(fila_label(self, etiqueta_volumen), 0,
               wx.LEFT | wx.RIGHT | wx.TOP, 10)
        self.sp_volumen = ContadorAccesible(
            self, min=0, max=100,
            initial=ajustes_interaccion.cargar_volumen(paths.interaccion()),
            name=nombre_de_etiqueta(etiqueta_volumen))
        nombre_accesible(self.sp_volumen, self.sp_volumen.GetName())
        self.sp_volumen.Bind(wx.EVT_SPINCTRL, self._al_cambiar_volumen)
        vs.Add(self.sp_volumen, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        vs.Add(self._fila_de_botones(), 0,
               wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        self.SetSizer(vs)
        self.lista.SetFocus()

    def _fila_de_botones(self):
        fila = wx.WrapSizer(wx.HORIZONTAL, flags=0)
        for accion in self._acciones:
            boton = wx.Button(self, label=accion.etiqueta,
                              name=nombre_de_etiqueta(accion.etiqueta))
            boton.Bind(wx.EVT_BUTTON,
                       lambda _evento, clave=accion.clave:
                       self._lista.ejecutar(clave))
            fila.Add(boton, 0, wx.RIGHT | wx.BOTTOM, 6)
        return fila

    def _textos(self):
        return [medios.fila(medio) for medio in self._medios]

    def _fijar(self, indice=-1):
        self._lista.fijar(self._textos(), indice)
        self.lista.SetFocus()

    def _guardar(self):
        medios_guardados.guardar(self._ruta, self._medios)

    def _al_cambiar_volumen(self, _evento):
        ajustes_interaccion.guardar_volumen(
            paths.interaccion(), self.sp_volumen.GetValue())

    def _elegido(self):
        return self._lista.indice()

    def _agregar(self):
        origen = self._elegir_archivo()
        if not origen:
            return
        tipo = medios.tipo_de(origen)
        duracion = (duracion_de(origen)
                    if tipo in ("sonido", "video") else 0)
        datos = medio_cuadro.abrir(
            self, medios_guardados.provisional(origen, duracion), ruta=origen)
        if datos is None:
            return
        self._medios.append(
            medios_guardados.agregar(self._carpeta, origen, datos))
        self._guardar()
        self._fijar(len(self._medios) - 1)
        self._medir(self._medios[-1])
        anunciar(_("Medio agregado"))

    def _medir(self, medio):
        if medio["tipo"] not in ("sonido", "video"):
            return
        if medio.get("ganancia_db") is not None:
            return
        archivo = medio["archivo"]

        def al_terminar(ganancia):
            if ganancia is None:
                return
            indice = medios_guardados.indice_de_archivo(
                self._medios, archivo)
            if indice is None:
                return
            self._medios[indice]["ganancia_db"] = ganancia
            self._guardar()

        medios_medicion.medir(
            medios_guardados.archivo_de(self._carpeta, medio), al_terminar)

    def _editar(self):
        indice = self._elegido()
        if indice is None:
            return
        datos = medio_cuadro.abrir(
            self, self._medios[indice], editar=True,
            ruta=medios_guardados.archivo_de(
                self._carpeta, self._medios[indice]))
        if datos is None:
            return
        self._medios[indice] = medios_guardados.normalizar(datos)
        self._guardar()
        self._fijar(indice)
        anunciar(_("Medio guardado"))

    def _duplicar(self):
        indice = self._elegido()
        if indice is None:
            return
        medio = self._medios[indice]
        nombre = coleccion.nombre_de_copia(medio["nombre"], self._medios)
        self._medios.insert(
            indice + 1,
            medios_guardados.duplicar(self._carpeta, medio, nombre))
        self._guardar()
        self._fijar(indice + 1)
        anunciar(_("Medio duplicado"))

    def _escuchar(self):
        indice = self._elegido()
        if indice is None:
            return
        if self._escucha.sonando():
            self._escucha.detener()
            return
        medio = self._medios[indice]
        anunciar(medios.escuchar(medio))
        if medio["tipo"] not in ("sonido", "video"):
            return
        ruta = medios_guardados.archivo_de(self._carpeta, medio)
        if self._escucha.reproducir(ruta):
            return
        sound_player.reproducir("error")
        confirmar.avisar(
            self, _("No se pudo reproducir el medio."),
            _("Escuchar medio"), _("Aceptar"),
            icono=confirmar.ICON_ERROR)

    def detener_escucha(self) -> bool:
        """Detiene la escucha previa y dice si había algo sonando."""
        if not self._escucha.sonando():
            return False
        self._escucha.detener()
        return True

    def soltar(self) -> None:
        """Suelta el reproductor de la escucha previa al cerrar la ventana."""
        self._escucha.detener()

    def _eliminar(self):
        indice = self._elegido()
        if indice is None:
            return
        medio = self._medios[indice]
        if not confirmar.preguntar(
                self,
                _("¿Quieres eliminar el medio «{nombre}»?").format(
                    nombre=medio["nombre"]),
                _("Eliminar medio"), _("&Eliminar"), _("&Cancelar"),
                predeterminado_si=False):
            return
        medios_guardados.eliminar(self._carpeta, medio)
        self._medios.pop(indice)
        self._guardar()
        self._fijar(min(indice, len(self._medios) - 1))
        anunciar(_("Medio eliminado"))

    def _exportar(self):
        if not self._medios:
            anunciar(_("No hay medios para exportar."))
            return
        ruta = self._pedir_ruta(guardar=True)
        if not ruta:
            return
        try:
            paquetes.exportar(
                ruta, "medios", self._medios,
                medios_guardados.rutas(self._carpeta, self._medios))
        except Exception as exc:
            confirmar.avisar(
                self, _("No se pudo escribir el paquete:\n\n{exc}").format(
                    exc=exc),
                _("Exportar medios"), _("Aceptar"),
                icono=confirmar.ICON_ERROR)

    def _importar(self):
        ruta = self._pedir_ruta(guardar=False)
        if not ruta:
            return
        try:
            paquete = paquetes.leer(ruta, "medios",
                                    extensiones=medios.EXTENSIONES)
        except paquetes.PaqueteRechazado as exc:
            confirmar.avisar(
                self, str(exc), _("Importar medios"), _("Aceptar"),
                icono=confirmar.ICON_ERROR)
            return
        destinos = paquetes.extraer_archivos(ruta, paquete, self._carpeta)
        self._incorporar(paquete.elementos, destinos)

    def _incorporar(self, elementos, destinos):
        anteriores = {id(medio) for medio in self._medios}
        nuevos = []
        for elemento in elementos:
            copia = dict(elemento)
            copia["archivo"] = destinos.get(copia.get("archivo"),
                                            copia.get("archivo"))
            nuevos.append(medios_guardados.normalizar(copia))
        repetidos = paquetes.repetidos(nuevos, self._medios)
        reemplazar = bool(repetidos) and self._preguntar_reemplazo(repetidos)
        self._medios = coleccion.combinar(
            self._medios, nuevos, reemplazar)
        self._guardar()
        for medio in self._medios:
            if id(medio) not in anteriores:
                self._medir(medio)
        indice = next((posicion for posicion, medio
                       in enumerate(self._medios)
                       if id(medio) not in anteriores), 0)
        self._fijar(indice)
        anunciar(ngettext("Se importó un medio.",
                          "Se importaron {n} medios.",
                          len(nuevos)).format(n=len(nuevos)))

    def _preguntar_reemplazo(self, repetidos):
        return confirmar.preguntar(
            self,
            _("Ya hay medios llamados {nombres}. "
              "¿Quieres reemplazarlos?").format(nombres=", ".join(repetidos)),
            _("Importar medios"), _("&Sí"), _("&No"),
            predeterminado_si=False)

    def _elegir_archivo(self):
        dialogo = wx.FileDialog(
            self, _("Agregar medio"), wildcard=medios.comodin(),
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
        try:
            if dialogo.ShowModal() != wx.ID_OK:
                return None
            return dialogo.GetPath()
        finally:
            dialogo.Destroy()

    def _pedir_ruta(self, guardar):
        estilo = ((wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) if guardar
                  else (wx.FD_OPEN | wx.FD_FILE_MUST_EXIST))
        dialogo = wx.FileDialog(
            self,
            _("Exportar medios") if guardar else _("Importar medios"),
            wildcard=_(WILDCARD), style=estilo)
        try:
            if dialogo.ShowModal() != wx.ID_OK:
                return None
            return dialogo.GetPath()
        finally:
            dialogo.Destroy()
