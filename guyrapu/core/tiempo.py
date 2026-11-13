# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Cómo se mide y se espera el tiempo.

El reloj es monotónico y el sueño respeta una parada durante la espera. El
doble de prueba avanza su propio reloj al dormir, así ninguna prueba espera
de verdad.
"""

from __future__ import annotations

import time


class TiempoReal:
    """Reloj monotónico y sueño que se corta con una parada."""

    def ahora(self) -> float:
        return time.monotonic()

    def dormir(self, segundos: float, parada=None) -> bool:
        """Duerme y devuelve si la parada cortó el sueño."""
        if parada is None:
            time.sleep(segundos)
            return False
        return parada.wait(segundos)


TIEMPO_REAL = TiempoReal()


class TiempoDeFunciones:
    """Arma un objeto de tiempo con un reloj y un dormir ya resueltos."""

    def __init__(self, reloj, dormir):
        self._reloj = reloj
        self._dormir = dormir

    def ahora(self) -> float:
        return self._reloj()

    def dormir(self, segundos: float, parada=None) -> bool:
        """Duerme con el dormir recibido y dice si la parada quedó puesta."""
        self._dormir(segundos)
        return parada is not None and parada.is_set()


def resolver_tiempo(reloj=None, dormir=None):
    """Devuelve el tiempo real si no se inyectaron reloj ni dormir."""
    if reloj is None and dormir is None:
        return TIEMPO_REAL
    return TiempoDeFunciones(reloj or time.monotonic, dormir or time.sleep)


class TiempoDoble:
    """Reloj de prueba que avanza al dormir y no espera de verdad."""

    def __init__(self, inicio: float = 0.0):
        self._ahora = float(inicio)
        self._programadas: list[tuple[float, object]] = []
        self.dormidas: list[float] = []

    def ahora(self) -> float:
        return self._ahora

    def avanzar(self, segundos: float) -> None:
        """Mueve el reloj sin dormir, para preparar una lectura."""
        self._ahora += segundos

    def programar_parada(self, instante: float, parada) -> None:
        """Hace que `parada` se dispare cuando el reloj llegue al instante."""
        self._programadas.append((instante, parada))

    def dormir(self, segundos: float, parada=None) -> bool:
        """Avanza el reloj, o hasta la parada programada más próxima."""
        if parada is not None and parada.is_set():
            return True
        inicio = self._ahora
        fin = inicio + max(0.0, segundos)
        proximas = sorted(((instante, evento)
                           for instante, evento in self._programadas
                           if inicio <= instante <= fin),
                          key=lambda programada: programada[0])
        if proximas:
            instante, evento = proximas[0]
            self._programadas.remove((instante, evento))
            self._ahora = instante
            self.dormidas.append(instante - inicio)
            evento.set()
            return True
        self._ahora = fin
        self.dormidas.append(fin - inicio)
        return False
