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
# Traductores: fila de la cola sin temas; Ctrl+Intro agrega el tema elegido.
TEXTO_COLA_VACIA = N_(
    "La cola está vacía. Aquí aparecen las canciones que van a sonar. "
    "Elige un tema y pulsa Ctrl+Intro para agregarlo.")
# Traductores: fila de «Canciones» sin temas que mostrar.
TEXTO_SIN_CANCIONES = N_(
    "No hay canciones. Aquí aparecen los temas de la carpeta de música o de la "
    "lista elegida. Cambia la búsqueda, los filtros o la carpeta.")
MOTIVO_NO_SUENA = N_("No suena ningún tema")
MOTIVO_COLA_VACIA = N_("La cola está vacía")
MOTIVO_SOLO_EN_LISTA_PROPIA = N_("Solo en una lista propia")


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

    def _armar_canciones(self):
        """Ata «Canciones» a la pieza común, con sus acciones y su caso vacío."""
        self._canciones = ListaConAcciones(
            self.lb_temas, self._acciones_de_canciones(),
            _(TEXTO_SIN_CANCIONES))

    def _acciones_de_canciones(self):
        """Las acciones de «Canciones», con sus teclas y sus motivos."""
        etiquetas = {accion: _(etiqueta)
                     for etiqueta, accion in musica_menus.entradas_canciones()}
        return (self._acciones_de_reproducir_cancion(etiquetas)
                + self._acciones_de_lista_de_canciones(etiquetas))

    def _acciones_de_reproducir_cancion(self, etiquetas):
        """Las que empiezan a sonar o agregan a la cola la fila elegida."""
        return (
            Accion(musica_menus.ACCION_AHORA,
                   etiquetas[musica_menus.ACCION_AHORA],
                   self._reproducir_cancion_ahora,
                   tecla="intro", varios=True),
            Accion(musica_menus.ACCION_CONTINUACION,
                   etiquetas[musica_menus.ACCION_CONTINUACION],
                   self._poner_cancion_a_continuacion,
                   tecla="mayus+intro", varios=True),
            Accion(musica_menus.ACCION_AGREGAR,
                   etiquetas[musica_menus.ACCION_AGREGAR],
                   self._agregar_cancion_a_la_cola,
                   tecla="ctrl+intro", varios=True),
        )

    def _acciones_de_lista_de_canciones(self, etiquetas):
        """Las que actúan sobre la lista o sobre las listas guardadas."""
        return (
            Accion(musica_menus.ACCION_TODO_DESDE_AQUI,
                   etiquetas[musica_menus.ACCION_TODO_DESDE_AQUI],
                   self._reproducir_todo_desde_aqui),
            Accion(musica_menus.ACCION_AGREGAR_A_LISTA,
                   etiquetas[musica_menus.ACCION_AGREGAR_A_LISTA],
                   lambda: None,
                   opciones=self._opciones_agregar_a_lista,
                   varios=True),
            Accion(musica_menus.ACCION_QUITAR_DE_LISTA,
                   etiquetas[musica_menus.ACCION_QUITAR_DE_LISTA],
                   self._quitar_cancion_de_la_lista,
                   tecla="suprimir",
                   motivo=self._motivo_quitar_lista,
                   varios=True),
        )

    def _con_temas(self):
        """Las canciones elegidas, en orden de fila."""
        return [self._temas_filtrados[indice]
                for indice in self._canciones.indices()
                if indice < len(self._temas_filtrados)]

    def _reproducir_cancion_ahora(self):
        self._control.reproducir_ahora(self._con_temas())

    def _poner_cancion_a_continuacion(self):
        self._control.poner_a_continuacion(self._con_temas())

    def _agregar_cancion_a_la_cola(self):
        self._control.agregar_al_final(self._con_temas())

    def _reproducir_todo_desde_aqui(self):
        _tema, indice = self._con_tema()
        self._control.reproducir_desde_aqui(self._temas_filtrados, indice)

    def _opciones_agregar_a_lista(self):
        """Una opción por lista guardada, leídas al abrir, y la de crear una."""
        opciones = [
            (str(nombre),
             lambda nombre=nombre: self._agregar_a_una_lista(nombre))
            for nombre in self._leer_nombres()
        ]
        opciones.append((
            _("&Nueva lista…"),
            lambda: self._nueva_lista(self._con_temas())))
        return opciones

    def _agregar_a_una_lista(self, nombre):
        temas = self._con_temas()
        if not temas:
            return
        self._control.agregar_a_lista(nombre, temas)
        self._refrescar_cantidades_colecciones()

    def _quitar_cancion_de_la_lista(self):
        indices = []
        for tema in self._con_temas():
            origen = self._indice_en_fuente(tema)
            if origen is not None:
                indices.append(origen)
        if len(indices) == 1:
            self._quitar_lista(indices[0])
        elif indices:
            self._control.quitar_varios_de_lista(self._fuente, indices)
            self._cargar_lista()
            self._refrescar_cantidades_colecciones()

    def _motivo_quitar_lista(self):
        if self._fuente is None:
            return _(MOTIVO_SOLO_EN_LISTA_PROPIA)
        return ""

    def _leer_nombres(self):
        try:
            return list(listas.nombres(self._control.carpeta_listas()))
        except Exception as exc:
            logger.debug("No se pudieron leer las listas de música: %s", exc)
            return []

    def _quitar_lista(self, indice):
        if self._fuente is None:
            return
        self._control.quitar_de_lista(self._fuente, indice)
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
        etiquetas = {accion: _(etiqueta)
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
                   self._quitar_canciones_de_la_cola,
                   tecla="suprimir", varios=True),
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

    def _quitar_canciones_de_la_cola(self):
        indices = self._cola.indices()
        if len(indices) == 1:
            self._control.quitar_de_cola(indices[0])
        else:
            self._control.quitar_varios_de_cola(indices)

    def actualizar_nombres(self, mapa):
        if not self or not mapa:
            return
        self._temas_fuente = tuple(
            mapa.get(tema.origen, tema) for tema in self._temas_fuente)
        self._temas_filtrados = tuple(
            mapa.get(tema.origen, tema) for tema in self._temas_filtrados)
        self._canciones.poner_al_dia(
            [tema.origen for tema in self._temas_filtrados],
            vista.filas_temas(self._temas_filtrados))
        if self._control.estado() is None:
            return
        self.refrescar_cola()

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
