# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Qué sale en el vídeo y cuándo se oculta.

Puro, sin OBS y sin ventanas. Su única razón para cambiar es el orden y los
tiempos de lo que se pone en el vídeo: la cola de piezas, la encuesta fija y
las órdenes que ejecuta la capa que muestra. El instante llega como
argumento en segundos.
"""

from __future__ import annotations

from dataclasses import dataclass

from guyrapu.core.idioma import _, ngettext


@dataclass(frozen=True)
class Pieza:
    """Lo que se puede poner en el vídeo y lo que F2 dice de ella."""

    tipo: str
    texto: str
    segundos: float
    datos: dict


@dataclass(frozen=True)
class Orden:
    """Una acción que la capa que muestra en el vídeo tiene que ejecutar."""

    accion: str
    pieza: Pieza
    con_sonido: bool


class ColaPantalla:
    """Una sola pieza en el vídeo, de a una y en el orden en que llegó."""

    TOPE = 20
    PAUSA_ENTRE = 1.0
    REINTENTO = 5.0

    def __init__(self):
        self._pendientes = []
        self._visible = None
        self._inicio = None
        self._ultima_oculta = None
        self._encuesta = None
        self._encuesta_visible = None
        self._encuesta_al_dia = None
        self._reintento_encuesta = 0.0
        self._esperando = None
        self._esperando_encuesta = False
        self._reintentos = {}
        self._pausado = False
        self._saltar = False
        self._silenciado = False
        self._panico = False

    def agregar(self, pieza):
        """Suma una pieza, salvo con la cola llena o el pánico.

        Las respuestas de los comandos y las tarjetas de los disparadores y
        las metas pasan delante de los mensajes automáticos que esperan, pero
        detrás de otras respuestas.
        """
        if self._panico or len(self._pendientes) >= self.TOPE:
            return False
        if pieza.tipo in ("comando", "disparador", "meta"):
            indice = next(
                (posicion for posicion, actual
                 in enumerate(self._pendientes) if actual.tipo == "mensaje"),
                len(self._pendientes))
            self._pendientes.insert(indice, pieza)
        else:
            self._pendientes.append(pieza)
        return True

    def ordenes(self, ahora):
        """La orden que toca dar ahora, o nada si espera una confirmación."""
        if self._esperando is not None:
            return []
        resultado = self._orden_de_actualizar(ahora)
        if resultado is None:
            resultado = self._orden_de_ocultar(ahora)
        if resultado is None:
            resultado = self._orden_de_mostrar(ahora)
        if resultado is None:
            return []
        orden, es_encuesta = resultado
        self._esperando = orden
        self._esperando_encuesta = es_encuesta
        return [orden]

    def _orden_de_actualizar(self, ahora):
        if (self._panico or self._encuesta_al_dia is None
                or self._encuesta_visible is None
                or ahora < self._reintento_encuesta):
            return None
        return Orden("actualizar", self._encuesta_al_dia, False), True

    def _orden_de_ocultar(self, ahora):
        if self._visible is not None and (
                self._panico or self._saltar
                or ahora - self._inicio >= self._visible.segundos):
            return Orden("ocultar", self._visible, False), False
        if (self._encuesta_visible is not None
                and (self._panico
                     or self._encuesta_visible is not self._encuesta)):
            return Orden("ocultar", self._encuesta_visible, False), True
        return None

    def _orden_de_mostrar(self, ahora):
        if self._panico:
            return None
        if (self._encuesta is not None
                and self._encuesta_visible is not self._encuesta
                and ahora >= self._reintento_de(self._encuesta)):
            return (Orden("mostrar", self._encuesta,
                          not self._silenciado), True)
        if (self._pausado or self._visible is not None
                or not self._pendientes):
            return None
        pieza = self._pendientes[0]
        if ahora < self._reintento_de(pieza):
            return None
        if (self._ultima_oculta is not None
                and ahora - self._ultima_oculta < self.PAUSA_ENTRE):
            return None
        self._pendientes.pop(0)
        return Orden("mostrar", pieza, not self._silenciado), False

    def _reintento_de(self, pieza):
        return self._reintentos.get(id(pieza), 0.0)

    def _espera(self, accion, pieza):
        return (self._esperando is not None
                and self._esperando.accion == accion
                and self._esperando.pieza is pieza)

    def mostrada(self, pieza, ahora):
        """Confirma que la pieza ya se ve y arranca sus segundos."""
        if not self._espera("mostrar", pieza):
            return
        self._esperando = None
        self._reintentos.pop(id(pieza), None)
        if self._esperando_encuesta:
            self._encuesta_visible = pieza
        else:
            self._visible = pieza
            self._inicio = ahora

    def actualizada(self, pieza, ahora):
        """Confirma que el texto de la encuesta visible ya cambió."""
        if not self._espera("actualizar", pieza):
            return
        self._esperando = None
        self._encuesta_visible = pieza
        self._encuesta_al_dia = None
        self._reintento_encuesta = 0.0

    def oculta(self, pieza, ahora):
        """Confirma que la pieza ya no se ve."""
        if not self._espera("ocultar", pieza):
            return
        self._esperando = None
        self._aplicar_oculta(pieza, ahora, self._esperando_encuesta)

    def fallo(self, pieza, ahora):
        """Anota que la orden no se pudo ejecutar."""
        if self._esperando is None or self._esperando.pieza is not pieza:
            return
        accion = self._esperando.accion
        es_encuesta = self._esperando_encuesta
        self._esperando = None
        if accion == "ocultar":
            self._aplicar_oculta(pieza, ahora, es_encuesta)
            return
        if accion == "actualizar":
            self._reintento_encuesta = ahora + self.REINTENTO
            return
        if self._panico:
            return
        self._reintentos[id(pieza)] = ahora + self.REINTENTO
        if not es_encuesta:
            self._pendientes.insert(0, pieza)

    def _aplicar_oculta(self, pieza, ahora, es_encuesta):
        self._reintentos.pop(id(pieza), None)
        if es_encuesta:
            self._encuesta_visible = None
            return
        self._visible = None
        self._inicio = None
        self._ultima_oculta = ahora
        self._saltar = False

    def pausar(self):
        """Deja terminar la pieza que se ve y frena la siguiente."""
        self._pausado = True

    def reanudar(self):
        self._pausado = False

    def saltar(self):
        """Pide ocultar ya la que se ve o la que está por confirmarse."""
        if self._visible is not None or (
                self._esperando is not None
                and self._esperando.accion == "mostrar"
                and not self._esperando_encuesta):
            self._saltar = True

    def vaciar(self):
        """Descarta lo pendiente sin tocar la pieza que se ve."""
        self._pendientes.clear()

    def silenciar(self, activo):
        self._silenciado = bool(activo)

    def panico(self, activo):
        """Corta la cola y la encuesta mientras esté activado."""
        if activo:
            self._panico = True
            self._pendientes.clear()
        else:
            self._panico = False

    def fijar_encuesta(self, pieza):
        """Deja la encuesta en el vídeo hasta fijar otra o quitarla."""
        self._encuesta = pieza
        self._encuesta_al_dia = None
        self._reintento_encuesta = 0.0

    def poner_al_dia_encuesta(self, pieza):
        """Cambia el texto de la encuesta que ya se ve, sin ocultarla."""
        if self._encuesta is None:
            return False
        self._encuesta = pieza
        if self._encuesta_visible is None:
            return False
        self._encuesta_al_dia = pieza
        return True

    def libre(self) -> bool:
        """Si no hay nada en el vídeo, ni tarjeta ni encuesta visibles."""
        return self._visible is None and self._encuesta_visible is None

    def _frase_fija(self) -> str:
        """La frase de F2 para la pieza fija, según lo que sea."""
        if self._encuesta_visible.tipo == "metas":
            # Traductores: estado de F2; {texto} es el de las metas.
            return _("Metas en el vídeo: {texto}.").format(
                texto=self._encuesta_visible.texto)
        # Traductores: estado de F2; {texto} es el de la encuesta.
        return _("Encuesta en el vídeo: {texto}.").format(
            texto=self._encuesta_visible.texto)

    def describir(self):
        """La frase que F2 dice del estado del vídeo."""
        partes = []
        if self._panico:
            # Traductores: estado de F2 con el pánico activado.
            partes.append(_("Pánico activado: no se muestra nada en el vídeo."))
        else:
            if self._encuesta_visible is not None:
                partes.append(self._frase_fija())
            if self._visible is not None:
                # Traductores: estado de F2; {texto} es lo que se está viendo.
                partes.append(_("En el vídeo: {texto}.").format(
                    texto=self._visible.texto))
            elif self._encuesta_visible is None:
                # Traductores: estado de F2 sin piezas en el vídeo.
                partes.append(_("Nada en el vídeo."))
        if self._pendientes:
            cantidad = len(self._pendientes)
            partes.append(
                # Traductores: estado de F2; {n} son las piezas en cola.
                ngettext("{n} en cola.", "{n} en cola.",
                         cantidad).format(n=cantidad))
        if self._pausado:
            # Traductores: estado de F2 con la cola en pausa.
            partes.append(_("La cola está en pausa."))
        if self._silenciado:
            # Traductores: estado de F2 con el sonido de los medios apagado.
            partes.append(_("Sonido de los medios silenciado."))
        return " ".join(partes)
