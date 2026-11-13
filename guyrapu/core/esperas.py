# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Cuándo volver a preguntar y cuándo rendirse.

La cadencia es un objeto inmutable que dice cuánto esperar antes del
siguiente intento. La espera repite una consulta hasta que está lista, se
agota el plazo, se agota el tope de intentos o llega la parada.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import NamedTuple

from guyrapu.core.tiempo import TIEMPO_REAL

MOTIVO_LISTO = "listo"
MOTIVO_PLAZO = "plazo"
MOTIVO_INTENTOS = "intentos"
MOTIVO_PARADA = "parada"


class Resultado(NamedTuple):
    valor: object
    motivo: str


@dataclass(frozen=True)
class Fija:
    """Espera siempre lo mismo entre consultas."""

    cada: float

    def espera(self, intento: int, transcurrido: float) -> float:
        return self.cada


@dataclass(frozen=True)
class RapidaYLenta:
    """Espera poco durante un tiempo y después afloja."""

    rapida: float
    durante: float
    lenta: float

    def espera(self, intento: int, transcurrido: float) -> float:
        return self.rapida if transcurrido < self.durante else self.lenta


@dataclass(frozen=True)
class Creciente:
    """Multiplica la espera por un factor hasta un techo."""

    inicial: float
    techo: float
    factor: float = 2.0

    def espera(self, intento: int, transcurrido: float) -> float:
        return min(self.inicial * self.factor ** intento, self.techo)


def esperar(consultar, listo, *, cadencia, parada=None, plazo=None,
            intentos=None, tolerar=(), tiempo=TIEMPO_REAL) -> Resultado:
    """Repite `consultar` hasta que `listo` lo acepte o se acabe la espera.

    La primera consulta es inmediata. El plazo se mide en segundos desde el
    comienzo y el último sueño se recorta a lo que falte. Un error de
    `tolerar` cuenta como "no listo"; cualquier otro sale.
    """
    inicio = tiempo.ahora()
    valor = None
    intento = 0
    while True:
        if parada is not None and parada.is_set():
            return Resultado(valor, MOTIVO_PARADA)
        try:
            valor = consultar()
        except tolerar:
            pass
        else:
            if listo(valor):
                return Resultado(valor, MOTIVO_LISTO)
        intento += 1
        if intentos is not None and intento >= intentos:
            return Resultado(valor, MOTIVO_INTENTOS)
        transcurrido = tiempo.ahora() - inicio
        if plazo is not None and transcurrido >= plazo:
            return Resultado(valor, MOTIVO_PLAZO)
        espera = cadencia.espera(intento - 1, transcurrido)
        if plazo is not None:
            espera = min(espera, max(0.0, plazo - transcurrido))
        if tiempo.dormir(espera, parada):
            return Resultado(valor, MOTIVO_PARADA)
