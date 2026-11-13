# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Cuándo se avisa que algo en vivo se cayó, volvió o dejó de intentarse.

La vigilancia no tiene bucle propio: recibe el resultado de cada lectura y
decide si hay que anunciar. El filtro de avisos repetidos guarda el momento
del último aviso de cada tipo.
"""

from __future__ import annotations

from dataclasses import dataclass

from guyrapu.core.tiempo import TIEMPO_REAL

PLAZO_REPETICION = 60.0
PLAZO_SOBRECARGA = 300.0


@dataclass(frozen=True)
class Aviso:
    """Frase y sonido de un anuncio de la vigilancia."""

    frase: str
    sonido: str


class Vigilancia:
    """Sigue un enlace en vivo a partir de las lecturas de quien lo vigila."""

    def __init__(self, anunciar, *, caida, vuelta, rendicion,
                 tiempo=TIEMPO_REAL, max_caidas=None,
                 duracion_estable=60.0):
        self._anunciar = anunciar
        self._caida = caida
        self._vuelta = vuelta
        self._rendicion = rendicion
        self._tiempo = tiempo
        self._max_caidas = max_caidas
        self._duracion_estable = duracion_estable
        self._caido = False
        self._desde = None
        self._rendido = False
        self._caidas_seguidas = 0
        self._inicio_buena = None

    @property
    def caido(self) -> bool:
        return self._caido

    @property
    def desde(self) -> float | None:
        return self._desde

    @property
    def rendido(self) -> bool:
        return self._rendido

    def leida(self, ok: bool) -> None:
        """Recibe el resultado de una lectura del enlace."""
        if self._rendido:
            return
        ahora = self._tiempo.ahora()
        if ok:
            self._buena(ahora)
        else:
            self._mala(ahora)

    def _buena(self, ahora):
        if self._inicio_buena is None:
            self._inicio_buena = ahora
        if self._caido:
            self._caido = False
            self._desde = None
            self._anunciar(self._vuelta.frase, self._vuelta.sonido)

    def _mala(self, ahora):
        if self._caido:
            return
        if (self._inicio_buena is not None
                and ahora - self._inicio_buena >= self._duracion_estable):
            self._caidas_seguidas = 0
        self._inicio_buena = None
        self._caidas_seguidas += 1
        self._caido = True
        self._desde = ahora
        self._anunciar(self._caida.frase, self._caida.sonido)
        if (self._max_caidas is not None
                and self._caidas_seguidas >= self._max_caidas):
            self._rendido = True
            self._anunciar(self._rendicion.frase, self._rendicion.sonido)


class AvisosRepetidos:
    """Decide si un aviso de la vigilancia ya se dijo hace poco."""

    def __init__(self, reloj, plazo=PLAZO_REPETICION,
                 plazo_sobrecarga=PLAZO_SOBRECARGA, plazos=None):
        self._reloj = reloj
        self._plazo = plazo
        self._plazos = {"sobrecarga": plazo_sobrecarga, **(plazos or {})}
        self._ultimos = {}

    def toca(self, tipo) -> bool:
        """Verdadero si el aviso toca ahora, y anota el momento."""
        if tipo == "vuelta":
            return True
        ahora = self._reloj()
        ultimo = self._ultimos.get(tipo)
        plazo = self._plazos.get(tipo, self._plazo)
        if ultimo is not None and ahora - ultimo < plazo:
            return False
        self._ultimos[tipo] = ahora
        return True
