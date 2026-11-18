# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Acciones de las listas de la ventana de música y sus diálogos.

La mezcla no guarda estado propio: usa la fuente y los controles que arma
`VentanaMusica`. Cada operación la hace `ControlMusica`, que es quien
anuncia; acá solo se pide, se elige y se refresca lo que se ve.
"""

from __future__ import annotations

import wx

from guyrapu.core import diagnostico
from guyrapu.core.idioma import N_, _
from guyrapu.music import anuncios, listas, vista
from guyrapu.ui import confirmar, musica_dialogo_enlace, musica_menus
from guyrapu.ui.lista_acciones import Accion, ListaConAcciones

logger = diagnostico.obtener_logger(__name__)

# Traductores: título del diálogo que confirma el borrado; una sola palabra.
TITULO = N_("Música")
TITULO_NUEVA = N_("Nueva lista")
TITULO_RENOMBRAR = N_("Cambiar nombre de la lista")
TEXTO_NOMBRE = N_("Nombre de la lista:")
TEXTO_COLA_VACIA = N_(
    "La cola está vacía. Elige un tema y pulsa Ctrl+Intro para agregarlo.")
MOTIVO_NO_SUENA = N_("No suena ningún tema")
MOTIVO_COLA_VACIA = N_("La cola está vacía")


def _validar_nombre(nombre):
    """El nombre limpio, o None si no sirve y el control dirá por qué."""
    try:
        return listas.validar_nombre(nombre)
    except listas.ErrorListas:
        return None


def _pedir_nombre(parent, titulo, valor=""):
    with wx.TextEntryDialog(parent, _(TEXTO_NOMBRE), titulo, valor) as dialogo:
        if dialogo.ShowModal() != wx.ID_OK:
            return None
        return dialogo.GetValue()


def _confirmar_borrar(parent, nombre):
    pregunta = _(anuncios.TEXTO_CONFIRMAR_BORRAR_LISTA).format(nombre=nombre)
    return confirmar.preguntar(
        parent, pregunta, _(TITULO), _("&Eliminar"), _("&Cancelar"),
        predeterminado_si=False)


class AccionesVentanaMusica:
    """Acciones de la Biblioteca, la Cola y las listas propias."""

    def _accion_biblioteca(self, accion):
        tema, indice = self._con_tema()
        if tema is None:
            return
        if isinstance(accion, tuple):
            self._control.agregar_a_lista(accion[1], [tema])
            self._refrescar_cantidades_colecciones()
            return
        funcion = self._acciones_biblioteca(tema, indice).get(accion)
        if funcion is not None:
            funcion()

    def _acciones_biblioteca(self, tema, indice):
        control = self._control
        return {
            musica_menus.ACCION_AHORA:
                lambda: control.reproducir_ahora([tema]),
            musica_menus.ACCION_CONTINUACION:
                lambda: control.poner_a_continuacion([tema]),
            musica_menus.ACCION_AGREGAR:
                lambda: control.agregar_al_final([tema]),
            musica_menus.ACCION_TODO_DESDE_AQUI:
                lambda: control.reproducir_desde_aqui(
                    self._temas_filtrados, indice),
            musica_menus.ACCION_NUEVA_LISTA_CON_TEMA:
                lambda: self._nueva_lista(tema),
            musica_menus.ACCION_QUITAR_DE_LISTA:
                lambda: self._quitar_lista(tema),
            musica_menus.ACCION_RENOMBRAR_LISTA: self._renombrar_lista,
            musica_menus.ACCION_BORRAR_LISTA: self._borrar_lista,
        }

    def _leer_nombres(self):
        try:
            return list(listas.nombres(self._control.carpeta_listas()))
        except Exception as exc:
            logger.debug("No se pudieron leer las listas de música: %s", exc)
            return []

    def _quitar_lista(self, tema):
        if self._fuente is None:
            return
        origen = self._indice_en_fuente(tema)
        if origen is not None:
            self._control.quitar_de_lista(self._fuente, origen)
            self._cargar_lista()
            self._refrescar_cantidades_colecciones()

    def _indice_en_fuente(self, tema):
        for indice, candidato in enumerate(self._temas_fuente):
            if candidato is tema:
                return indice
        for indice, candidato in enumerate(self._temas_fuente):
            if candidato == tema:
                return indice
        return None

    def _armar_cola(self):
        """Ata la Cola a la pieza común, con sus acciones y su caso vacío."""
        self._cola = ListaConAcciones(
            self.lb_cola, self._acciones_de_la_cola(), _(TEXTO_COLA_VACIA))

    def _acciones_de_la_cola(self):
        """Las acciones de la Cola, con sus teclas y sus motivos."""
        etiquetas = {accion: etiqueta
                     for etiqueta, accion in musica_menus.entradas_cola()}
        control = self._control
        return (self._acciones_con_fila(control, etiquetas)
                + self._acciones_sin_fila(control, etiquetas))

    def _acciones_con_fila(self, control, etiquetas):
        """Las cuatro que actúan sobre la fila elegida."""
        return (
            Accion(musica_menus.ACCION_REPRODUCIR,
                   etiquetas[musica_menus.ACCION_REPRODUCIR],
                   lambda: control.reproducir_desde(self._indice_cola()),
                   tecla="intro"),
            Accion(musica_menus.ACCION_QUITAR,
                   etiquetas[musica_menus.ACCION_QUITAR],
                   lambda: control.quitar_de_cola(self._indice_cola()),
                   tecla="suprimir"),
            Accion(musica_menus.ACCION_SUBIR,
                   etiquetas[musica_menus.ACCION_SUBIR],
                   lambda: self._mover_cola(self._indice_cola(), -1),
                   tecla="alt+flecha_arriba"),
            Accion(musica_menus.ACCION_BAJAR,
                   etiquetas[musica_menus.ACCION_BAJAR],
                   lambda: self._mover_cola(self._indice_cola(), 1),
                   tecla="alt+flecha_abajo"),
        )

    def _acciones_sin_fila(self, control, etiquetas):
        """Las que no necesitan una fila elegida."""
        return (
            Accion(musica_menus.ACCION_IR_AL_QUE_SUENA,
                   etiquetas[musica_menus.ACCION_IR_AL_QUE_SUENA],
                   self._ir_al_que_suena, necesita_elemento=False,
                   motivo=self._motivo_ir_al_que_suena),
            Accion(musica_menus.ACCION_MEZCLAR,
                   etiquetas[musica_menus.ACCION_MEZCLAR],
                   lambda: control.mezclar_cola(), necesita_elemento=False,
                   motivo=self._motivo_cola_vacia),
            Accion(musica_menus.ACCION_VACIAR,
                   etiquetas[musica_menus.ACCION_VACIAR],
                   lambda: control.vaciar_cola(), necesita_elemento=False,
                   motivo=self._motivo_cola_vacia),
            Accion(musica_menus.ACCION_GUARDAR_COLA,
                   etiquetas[musica_menus.ACCION_GUARDAR_COLA],
                   self._guardar_cola, necesita_elemento=False),
        )

    def _motivo_ir_al_que_suena(self):
        estado = self._control.estado()
        if (estado is None or estado.terminado
                or estado.posicion is None):
            return _(MOTIVO_NO_SUENA)
        return ""

    def _motivo_cola_vacia(self):
        if self._control.cola_actual() or ():
            return ""
        return _(MOTIVO_COLA_VACIA)

    def _mover_cola(self, indice, paso):
        self._control.mover_en_cola(indice, paso)
        estado = self._control.estado()
        total = len(estado.cola) if estado is not None else 0
        destino = max(0, min(total - 1, indice + paso)) if total else -1
        self.refrescar_cola(seleccion=destino)

    def _ir_al_que_suena(self):
        estado = self._control.estado()
        if estado is None or estado.terminado or estado.posicion is None:
            return
        self.lb_cola.SetSelection(estado.posicion)
        self.lb_cola.SetFocus()

    def refrescar_cola(self, seleccion=None):
        if not self:
            return
        anterior = self._indice_cola() if seleccion is None else seleccion
        estado = self._control.estado()
        filas = (vista.filas_cola(estado)
                 if estado is not None else [])
        indice = vista.indice_seleccion_tras_refrescar(anterior, len(filas))
        self._cola.poner_al_dia(
            list(range(len(filas))), filas,
            indice if indice >= 0 else None)

    def _indice_cola(self):
        return self._cola.indice()

    def actualizar_nombres(self, mapa):
        if not self or not mapa:
            return
        self._temas_fuente = tuple(
            mapa.get(tema.origen, tema) for tema in self._temas_fuente)
        self._temas_filtrados = tuple(
            mapa.get(tema.origen, tema) for tema in self._temas_filtrados)
        filas = vista.filas_temas(self._temas_filtrados)
        for indice, tema in enumerate(self._temas_filtrados):
            if tema.origen in mapa:
                try:
                    self.lb_temas.SetString(indice, filas[indice])
                except Exception:
                    logger.debug("No se pudo actualizar la fila de un tema")
        if self._control.estado() is None:
            return
        self.refrescar_cola()

    def _menu_temas(self):
        if self._con_tema()[0] is not None:
            musica_menus.mostrar_menu(
                self.lb_temas,
                musica_menus.entradas_biblioteca(
                    self._fuente is not None, self._leer_nombres()),
                self._accion_biblioteca)

    def _guardar_cola(self):
        if not (self._control.cola_actual() or ()):
            self._control.guardar_cola_como_lista("")
            return
        nombre = _pedir_nombre(self, _(TITULO_NUEVA))
        if nombre is None:
            return
        limpio = _validar_nombre(nombre)
        if limpio is None:
            self._control.guardar_cola_como_lista(nombre)
            return
        self._control.guardar_cola_como_lista(limpio)
        self._reload_colecciones(preferir=self._fuente)

    def _abrir_enlace(self):
        datos = musica_dialogo_enlace.pedir_enlace(self)
        if datos is not None:
            self._control.abrir_enlace(*datos)

    def _cambiar_carpeta(self, cargando=False):
        if cargando:
            from guyrapu.ui.musica_colecciones import (
                MOTIVO_CARGANDO, _anunciar_ventana)
            _anunciar_ventana(f"{_(MOTIVO_CARGANDO)}.")
            return
        with wx.DirDialog(
                self, _("Elige la carpeta de música"),
                defaultPath=self._control._carpeta()) as dialogo:
            if dialogo.ShowModal() != wx.ID_OK:
                return
            ruta = dialogo.GetPath()
        self._control.cambiar_carpeta(ruta)
        self._reload_colecciones()
        self._cargar_fuente()

    def _cerrar(self):
        self._cancelar_temporizador()
        self.EndModal(wx.ID_CANCEL)
