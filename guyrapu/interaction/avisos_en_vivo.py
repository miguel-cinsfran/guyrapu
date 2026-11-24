# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Cuándo y con qué frase se avisa del avance de algo en vivo.

Puro, sin wx y sin reloj propio: recibe el momento. Única razón para cambiar:
cuándo se dice cada aviso del avance de una encuesta o una meta.
"""

from __future__ import annotations

from typing import NamedTuple

from guyrapu.core.idioma import _, ngettext

SEGUNDOS_AVISO = 10
ESPERA_GANADOR = 15
MITAD = 0.5
CERCA = 0.9


class Aviso(NamedTuple):
    """La frase a decir y la clave de su sonido."""

    frase: str
    clave: str


def _ganador(votos):
    """El índice de la única opción con más votos, o None si hay empate."""
    if not votos or not any(votos):
        return None
    maximo = max(votos)
    ganadores = [indice for indice, cantidad in enumerate(votos)
                 if cantidad == maximo]
    return ganadores[0] if len(ganadores) == 1 else None


class EstadoEncuesta:
    """Lo que ya se dijo de la encuesta abierta en una sesión."""

    def __init__(self):
        self.dijo_diez = False
        self.ultimo_ganador: int | None = None
        self.cuando_ganador: float | None = None

    def aviso(self, votos, opciones, restante, ahora) -> Aviso | None:
        """El aviso que toca en este voto o latido, o nada."""
        if (restante is not None and 0 < restante <= SEGUNDOS_AVISO
                and not self.dijo_diez):
            self.dijo_diez = True
            return Aviso(
                # Traductores: encuesta con tiempo que está por terminar.
                _("Quedan 10 segundos de la encuesta."),
                "encuesta_por_terminar")
        if restante is not None and restante <= SEGUNDOS_AVISO:
            return None
        ganador = _ganador(votos)
        if ganador is None or ganador == self.ultimo_ganador:
            return None
        if (self.cuando_ganador is not None
                and ahora - self.cuando_ganador < ESPERA_GANADOR):
            return None
        self.ultimo_ganador = ganador
        self.cuando_ganador = ahora
        cantidad = votos[ganador]
        return Aviso(
            # Traductores: opción que va ganando una encuesta; {opcion} es su texto y {n} sus votos.
            ngettext("Va ganando {opcion}, con {n} voto.",
                     "Va ganando {opcion}, con {n} votos.",
                     cantidad).format(opcion=opciones[ganador], n=cantidad),
            "encuesta_ganadora")


def _cantidad(valor) -> str:
    numero = float(valor)
    return str(int(numero)) if numero.is_integer() else f"{numero:.2f}"


def aviso_meta(nombre, anterior, nuevo, objetivo, dichos) -> str | None:
    """El umbral que acaba de cruzar la meta, o nada.

    `dichos` se actualiza acá: guarda los umbrales ya anunciados en esta
    conexión para que la sesión no tenga que saber qué frase se eligió.
    """
    if nuevo >= objetivo:
        dichos.update((MITAD, CERCA))
        return None
    if CERCA not in dichos and anterior < objetivo * CERCA <= nuevo:
        dichos.update((MITAD, CERCA))
        # Traductores: meta cerca de su objetivo; {nombre} es la meta, {actual} lo logrado y {objetivo} lo que hay que lograr.
        return _("Meta {nombre}: cerca del objetivo, {actual} de {objetivo}.").format(
            nombre=nombre, actual=_cantidad(nuevo), objetivo=objetivo)
    if MITAD not in dichos and anterior < objetivo * MITAD <= nuevo:
        dichos.add(MITAD)
        # Traductores: meta a la mitad; {nombre} es la meta, {actual} lo logrado y {objetivo} lo que hay que lograr.
        return _("Meta {nombre}: a la mitad, {actual} de {objetivo}.").format(
            nombre=nombre, actual=_cantidad(nuevo), objetivo=objetivo)
    return None
