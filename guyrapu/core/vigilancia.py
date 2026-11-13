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


class _Gracia:
    """La espera de arranque y el comienzo de la racha buena."""

    def __init__(self, plazo):
        self.plazo = plazo
        self.inicio_buena = None
        self.inicio_mala = None

    def reiniciar(self):
        if self.plazo is None:
            return
        self.inicio_buena = None
        self.inicio_mala = None

    def buena(self, ahora):
        if self.inicio_buena is None:
            self.inicio_buena = ahora
        self.inicio_mala = None

    def en_gracia(self, ahora):
        if self.plazo is None or self.inicio_buena is not None:
            return False
        if self.inicio_mala is None:
            self.inicio_mala = ahora
        if ahora - self.inicio_mala < self.plazo:
            return True
        self.inicio_mala = None
        return False


class Vigilancia:
    """Sigue un enlace en vivo a partir de las lecturas de quien lo vigila."""

    def __init__(self, anunciar, *, caida, vuelta, rendicion,
                 tiempo=TIEMPO_REAL, max_caidas=None,
                 duracion_estable=60.0, gracia=None):
        self._anunciar = anunciar
        self._caida = caida
        self._vuelta = vuelta
        self._rendicion = rendicion
        self._tiempo = tiempo
        self._max_caidas = max_caidas
        self._duracion_estable = duracion_estable
        self._gracia = _Gracia(gracia)
        self._caido = False
        self._desde = None
        self._rendido = False
        self._caidas_seguidas = 0

    @property
    def caido(self) -> bool:
        return self._caido

    @property
    def desde(self) -> float | None:
        return self._desde

    @property
    def rendido(self) -> bool:
        return self._rendido

    def reiniciar_gracia(self) -> None:
        """Vuelve a esperar la primera respuesta sin tocar la caída."""
        self._gracia.reiniciar()

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
        self._gracia.buena(ahora)
        if self._caido:
            self._caido = False
            self._desde = None
            self._anunciar(self._vuelta.frase, self._vuelta.sonido)

    def _mala(self, ahora):
        if self._caido or self._gracia.en_gracia(ahora):
            return
        if (self._gracia.inicio_buena is not None
                and ahora - self._gracia.inicio_buena >= self._duracion_estable):
            self._caidas_seguidas = 0
        self._gracia.inicio_buena = None
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
