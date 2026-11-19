# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Lista de colecciones de la ventana de música.

La mezcla guarda la fuente elegida (la carpeta o una lista propia) y carga
sus temas en la lista que arma `VentanaMusica`. «Biblioteca» es la carpeta;
debajo va una fila por lista propia. Intro reproduce la colección entera y
Supr elimina la lista, previa confirmación.
"""

from __future__ import annotations

from guyrapu.core import diagnostico
from guyrapu.core.idioma import N_, _
from guyrapu.music import anuncios, listas, vista
from guyrapu.ui import musica_editor_lista, musica_menus
from guyrapu.ui import musica_ventana_acciones as _acciones
from guyrapu.ui.espera_sonora import EsperaSonora
from guyrapu.ui.lista_acciones import Accion, ListaConAcciones

logger = diagnostico.obtener_logger(__name__)

# La clave de «Biblioteca» no puede chocar con el nombre de una lista.
CLAVE_BIBLIOTECA = object()
TEXTO_CARGANDO = N_("Cargando la carpeta…")
# Traductores: motivo del botón «Cambiar carpeta» mientras se carga la carpeta.
MOTIVO_CARGANDO = N_("Cargando la carpeta")
TEXTO_SIN_CARPETA = N_("No hay carpeta de música")


def _anunciar_ventana(texto) -> None:
    """Anuncia por la ventana, no por este módulo.

    El import es perezoso porque musica_ventana importa este módulo.
    """
    from guyrapu.ui import musica_ventana
    musica_ventana.anunciar(texto)


class ColeccionesVentanaMusica:
    """La lista «Colecciones» y la fuente que muestra la lista de temas."""

    def _armar_colecciones(self):
        """Ata «Colecciones» a la pieza común, con sus acciones y su caso vacío."""
        self._colecciones = ListaConAcciones(
            self.lb_colecciones, self._acciones_de_colecciones(),
            _(TEXTO_CARGANDO))

    def _acciones_de_colecciones(self):
        """Las acciones de «Colecciones», con sus teclas y sus motivos."""
        etiquetas = {accion: _(etiqueta)
                     for etiqueta, accion in musica_menus.entradas_colecciones()}
        return (self._acciones_de_reproducir_coleccion(etiquetas)
                + self._acciones_de_lista(etiquetas))

    def _acciones_de_reproducir_coleccion(self, etiquetas):
        """Las que empiezan a sonar o agregan a la cola la colección."""
        return (
            Accion(musica_menus.ACCION_REPRODUCIR_COLECCION,
                   etiquetas[musica_menus.ACCION_REPRODUCIR_COLECCION],
                   self._reproducir_coleccion, tecla="intro"),
            Accion(musica_menus.ACCION_AGREGAR_COLECCION,
                   etiquetas[musica_menus.ACCION_AGREGAR_COLECCION],
                   self._agregar_coleccion_a_cola, tecla="ctrl+intro"),
        )

    def _acciones_de_lista(self, etiquetas):
        """Las que actúan sobre una lista propia o crean una."""
        return (
            self._accion_de_lista(
                etiquetas, musica_menus.ACCION_EDITAR_LISTA,
                self._editar_lista),
            self._accion_de_lista(
                etiquetas, musica_menus.ACCION_RENOMBRAR_LISTA,
                self._renombrar_lista, tecla="f2"),
            self._accion_de_lista(
                etiquetas, musica_menus.ACCION_BORRAR_LISTA,
                self._borrar_lista, tecla="suprimir"),
            Accion(musica_menus.ACCION_NUEVA_LISTA,
                   etiquetas[musica_menus.ACCION_NUEVA_LISTA],
                   self._nueva_lista, necesita_elemento=False),
        )

    def _accion_de_lista(self, etiquetas, clave, manejador, tecla=None):
        """Una acción que solo vale en una lista propia."""
        return Accion(clave, etiquetas[clave], manejador, tecla=tecla,
                      necesita_elemento=False, motivo=self._motivo_solo_lista)

    def _motivo_solo_lista(self):
        if self._coleccion_elegida() is None:
            return _(_acciones.MOTIVO_SOLO_EN_LISTA_PROPIA)
        return ""

    def _inicio(self):
        estado = self._control.estado()
        posicion = None
        if estado is not None and not estado.terminado:
            posicion = estado.posicion
        self.refrescar_cola(seleccion=posicion)
        if self._abrir_listas and self._nombres_listas:
            self.lb_colecciones.SetSelection(1)
            self._fuente = self._nombres_listas[0]
            self._cargar_lista()
        else:
            self.lb_colecciones.SetSelection(0)
            self._fuente = None
            self._cargar_carpeta()
        self.enfocar_primer_control()

    def enfocar_primer_control(self):
        if self._abrir_listas and self._nombres_listas:
            self.lb_colecciones.SetFocus()
        else:
            self.txt_buscar.SetFocus()

    def _reload_colecciones(self, preferir=None):
        nombres = self._leer_nombres()
        self._nombres_listas = nombres
        self._refrescar_cantidades_colecciones(
            elegida=preferir or CLAVE_BIBLIOTECA)
        self._fuente = self._coleccion_elegida()

    def _refrescar_cantidades_colecciones(self, elegida=None):
        nombres = self._nombres_listas or []
        cantidad = getattr(self, "_cantidad_biblioteca", None)
        try:
            carpeta = self._control.carpeta_listas()
        except Exception as exc:
            logger.debug("No se pudieron leer las listas de música: %s", exc)
            carpeta = None
        if carpeta is None:
            cantidades = {}
        else:
            cantidades = {n: listas.cantidad(carpeta, n) for n in nombres}
        filas = vista.filas_colecciones(nombres, cantidad, cantidades)
        claves = [CLAVE_BIBLIOTECA] + [str(n) for n in nombres]
        self._colecciones.poner_al_dia(claves, filas, elegida)

    def _coleccion_elegida(self):
        indice = self._colecciones.indice()
        if indice is None or indice <= 0 or indice > len(self._nombres_listas):
            return None
        return self._nombres_listas[indice - 1]

    def _cambiar_coleccion(self, evento):
        self._cargar_fuente()
        evento.Skip()

    def _detener_espera_carga(self):
        espera = getattr(self, "_espera_carga", None)
        if espera is not None:
            espera.detener()

    def _cargar_fuente(self):
        self._detener_espera_carga()
        self._generacion += 1
        self.txt_buscar.ChangeValue("")
        self._cancelar_temporizador()
        self._fuente = self._coleccion_elegida()
        if self._fuente is None:
            self._cargar_carpeta()
        else:
            self._biblioteca = None
            self._cargar_lista()

    def _empezar_espera_carga(self):
        if not hasattr(self, "_espera_carga"):
            self._espera_carga = EsperaSonora(self)
        if self._control._carpeta():
            self._espera_carga.empezar()
        else:
            self._espera_carga.detener()

    def _cargar_carpeta(self):
        self._biblioteca = None
        self._primera_carga = True
        self.txt_buscar.ChangeValue("")
        self._cambiar_estado(_(TEXTO_CARGANDO))
        self._empezar_espera_carga()
        generacion = self._generacion
        self._control.biblioteca(
            lambda biblioteca: self._al_biblioteca(biblioteca, generacion))

    def _cargar_lista(self, seleccion=None):
        nombre = self._fuente
        generacion = self._generacion
        if seleccion is None:
            seleccion = self.lb_temas.GetSelection()
        self._cambiar_estado(_(TEXTO_CARGANDO))
        temas = tuple(self._control.temas_de_lista(nombre) or ())
        if generacion != self._generacion or self._fuente != nombre:
            return
        self._temas_fuente = temas
        self._cargando = False
        self.filtros.refrescar_artistas(self._temas_fuente)
        self._aplicar_filtro()
        self._estado_listo()
        indice = vista.indice_seleccion_tras_refrescar(
            seleccion, len(self._temas_filtrados))
        if indice >= 0:
            self.lb_temas.SetSelection(indice)

    def _sin_biblioteca(self):
        self._cantidad_biblioteca = None
        self._temas_fuente = self._temas_filtrados = ()
        if self._control._carpeta():
            self._espera_carga.terminar("error")
        else:
            self._espera_carga.detener()
        self._cambiar_estado(_(TEXTO_SIN_CARPETA))

    def _al_biblioteca(self, biblioteca, generacion):
        if not self or generacion != self._generacion or self._fuente is not None:
            return
        if biblioteca is None:
            self._sin_biblioteca()
            return
        self._biblioteca = biblioteca
        self._cantidad_biblioteca = len(biblioteca.temas())
        self._temas_fuente = tuple(biblioteca.temas())
        self._cargando = False
        self.filtros.refrescar_artistas(self._temas_fuente)
        self._aplicar_filtro()
        self._estado_listo()
        self._espera_carga.terminar("listo")
        self._resumir_y_preguntar(biblioteca)

    def _resumir_y_preguntar(self, biblioteca):
        """Resume la carpeta al abrirla y pregunta por igualar el volumen."""
        if self._primera_carga:
            self._primera_carga = False
            _anunciar_ventana(vista.texto_resumen(
                len(self._temas_fuente), len(self._temas_filtrados), False))
        self._refrescar_cantidades_colecciones()
        self.preguntar_igualacion(biblioteca)

    def refrescar_por_vigia(self):
        """Pone al día la lista con lo que vio el vigía, si muestra la carpeta.

        Vuelve a tomar los temas de la biblioteca y reaplica el filtro de
        Buscar, conservando el tema elegido si sigue estando (si no, el
        índice más cercano). Actualiza la cantidad de «Colecciones». No
        mueve el foco. Con una lista propia, no hace nada.
        """
        if (not self or self._fuente is not None
                or self._biblioteca is None):
            return
        elegido = self._origen_elegido()
        self._temas_fuente = tuple(self._biblioteca.temas())
        self._cantidad_biblioteca = len(self._temas_fuente)
        self.filtros.refrescar_artistas(self._temas_fuente)
        self._aplicar_filtro()
        self._seleccionar_origen(elegido)
        self._refrescar_cantidades_colecciones()

    def _seleccionar_origen(self, elegido):
        """Deja elegido el tema con ese origen, si sigue estando."""
        if elegido is None:
            return
        for indice, candidato in enumerate(self._temas_filtrados):
            if candidato.origen == elegido:
                self.lb_temas.SetSelection(indice)
                return

    def _origen_elegido(self):
        """El origen del tema elegido, o None sin selección."""
        seleccion = self.lb_temas.GetSelection()
        if 0 <= seleccion < len(self._temas_filtrados):
            return self._temas_filtrados[seleccion].origen
        return None

    def examinar_carpeta(self) -> None:
        """Vuelve a examinar la carpeta en un hilo y anuncia el resultado.

        Mientras examina, otra pulsación no lanza otro hilo.
        """
        if getattr(self, "_examinando", False):
            return
        if not self._control._carpeta():
            _anunciar_ventana(_(anuncios.TEXTO_SIN_CARPETA))
            return
        self._examinando = True
        self._control.reexaminar_carpeta(self._al_examinar)

    def _al_examinar(self, biblioteca, nuevas, quitadas) -> None:
        """Refresca la lista y anuncia lo que encontró el examen."""
        if not self:
            return
        self._examinando = False
        if biblioteca is None:
            _anunciar_ventana(_(anuncios.TEXTO_SIN_CARPETA))
            return
        if biblioteca is not self._biblioteca:
            return
        if self._fuente is None:
            self.refrescar_por_vigia()
        _anunciar_ventana(vista.texto_carpeta_examinada(nuevas, quitadas))

    def _reproducir_coleccion(self):
        nombre = self._coleccion_elegida()
        if nombre is not None:
            self._control.reproducir_lista_guardada(nombre)
            return
        if self._cargando or not self._temas_fuente:
            return
        self._control.reproducir_desde_aqui(self._temas_fuente, 0)

    def _agregar_coleccion_a_cola(self):
        nombre = self._coleccion_elegida()
        if nombre is not None:
            temas = tuple(self._control.temas_de_lista(nombre) or ())
        else:
            temas = tuple(self._temas_fuente)
        if temas:
            self._control.agregar_al_final(list(temas))

    def _nueva_lista(self, temas_marcados=()):
        self._editar_lista_guardada(None, temas_marcados)

    def _editar_lista(self):
        nombre = self._coleccion_elegida()
        if nombre is not None:
            self._editar_lista_guardada(nombre)

    def _editar_lista_guardada(self, viejo, temas_marcados=()):
        if viejo is None:
            temas_lista = tuple(temas_marcados)
        else:
            temas_lista = tuple(self._control.temas_de_lista(viejo) or ())
        biblioteca = self._control.biblioteca_actual()
        if biblioteca is not None:
            self._abrir_editor_lista(viejo, temas_lista, biblioteca.temas())
            return
        self._control.biblioteca(
            lambda actual: self._abrir_editor_lista(
                viejo, temas_lista,
                actual.temas() if actual is not None else ()))

    def _abrir_editor_lista(self, viejo, temas_lista, temas_carpeta):
        datos = musica_editor_lista.pedir_lista(
            self, viejo or "", tuple(temas_carpeta or ()), temas_lista,
            reproducir=lambda tema: self._control.reproducir_ahora([tema]))
        if datos is None:
            return
        nombre, temas = datos
        self._control.guardar_lista(nombre, list(temas), viejo)
        self._reload_colecciones(preferir=nombre)
        self._cargar_fuente()

    def _renombrar_lista(self):
        viejo = self._coleccion_elegida()
        if viejo is None:
            return
        nombre = _acciones._pedir_nombre(
            self, _(_acciones.TITULO_RENOMBRAR), viejo)
        if nombre is None:
            return
        limpio = _acciones._validar_nombre(nombre)
        if limpio is None:
            self._control.renombrar_lista(viejo, nombre)
            return
        self._control.renombrar_lista(viejo, limpio)
        self._reload_colecciones(preferir=limpio)
        self._fuente = self._coleccion_elegida()

    def _borrar_lista(self):
        nombre = self._coleccion_elegida()
        if nombre is None or not _acciones._confirmar_borrar(self, nombre):
            return
        self._control.borrar_lista(nombre)
        self._reload_colecciones()
        self._cargar_fuente()
