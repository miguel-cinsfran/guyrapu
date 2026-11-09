# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Qué bitrate aguanta la red en la prueba de conexión y cuál se prueba después.

Su única razón para cambiar es qué se considera aguantar y cuánto se sube o se
baja. Sin wx y sin OBS: las listas las usa `prueba_conexion` y las pruebas.
"""

from __future__ import annotations

UMBRAL = 0.01
MINIMO = 1000
MAXIMO = 12000
ABAJO = (0.70, 0.50)
ARRIBA = (1.50, 2.00)


def aguanta(perdidos, totales) -> bool:
    """Verdadero si hubo cuadros y se perdió el 1 % o menos."""
    try:
        perdidos = max(0, int(perdidos))
        totales = int(totales)
    except (TypeError, ValueError):
        return False
    if totales <= 0:
        return False
    return perdidos * 100 <= totales


def _redondear(bitrate) -> int:
    return int(bitrate / 100.0 + 0.5) * 100


def _lista(actual, factores, tope, al_alza) -> tuple:
    try:
        base = int(actual)
    except (TypeError, ValueError):
        return ()
    salida = []
    for factor in factores:
        bitrate = _redondear(base * factor)
        if al_alza:
            if bitrate > tope or bitrate <= base:
                continue
        elif bitrate < tope or bitrate >= base:
            continue
        if bitrate not in salida:
            salida.append(bitrate)
    return tuple(salida)


def hacia_abajo(actual) -> tuple:
    """Los bitrates de los intentos descendentes: 70 % y 50 %, de 1000 en adelante."""
    return _lista(actual, ABAJO, MINIMO, al_alza=False)


def hacia_arriba(actual) -> tuple:
    """Los bitrates de los intentos ascendentes: 150 % y 200 %, hasta 12000."""
    return _lista(actual, ARRIBA, MAXIMO, al_alza=True)
