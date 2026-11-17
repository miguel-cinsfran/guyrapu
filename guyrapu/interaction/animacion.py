# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Cómo entra y sale una tarjeta, cuadro por cuadro.

Puro y sin wx. Su única razón para cambiar son las curvas y los
movimientos: dónde arranca cada animación y con qué ritmo llega a su
estado final.
"""

from __future__ import annotations

from dataclasses import dataclass

from guyrapu.core.idioma import N_

# Traductores: animaciones de entrada de un aviso en el vídeo.
ENTRADAS = (
    ("suave", N_("Fundido al subir")),
    ("fundido", N_("Fundido")),
    ("derecha", N_("Desde la derecha")),
    ("izquierda", N_("Desde la izquierda")),
    ("arriba", N_("Desde arriba")),
    ("abajo", N_("Desde abajo")),
    ("ninguna", N_("Ninguna")),
)

# Traductores: animaciones de salida de un aviso en el vídeo.
SALIDAS = (
    ("fundido", N_("Fundido")),
    ("suave", N_("Fundido al bajar")),
    ("derecha", N_("Hacia la derecha")),
    ("izquierda", N_("Hacia la izquierda")),
    ("arriba", N_("Hacia arriba")),
    ("abajo", N_("Hacia abajo")),
    ("ninguna", N_("Ninguna")),
)

DESVANECEN = ("fundido", "suave")


@dataclass(frozen=True)
class Cuadro:
    """Un cuadro de la animación, con su instante y su estado."""

    ms: int
    dx: float
    dy: float
    opacidad: float


def desplazamiento(movimiento, x, y, ancho_tarjeta, alto_tarjeta,
                   ancho_lienzo, alto_lienzo) -> tuple[float, float]:
    """El corrimiento desde la posición final para esa animación."""
    if movimiento == "derecha":
        return (ancho_lienzo - x, 0.0)
    if movimiento == "izquierda":
        return (-x - ancho_tarjeta, 0.0)
    if movimiento == "arriba":
        return (0.0, -y - alto_tarjeta)
    if movimiento == "abajo":
        return (0.0, alto_lienzo - y)
    if movimiento == "suave":
        return (0.0, 0.04 * min(ancho_lienzo, alto_lienzo))
    return (0.0, 0.0)


def _instantes(duracion_ms) -> list[int]:
    paso = 1000 / 60
    instantes = []
    k = 0
    while k * paso < duracion_ms:
        instantes.append(round(k * paso))
        k += 1
    if len(instantes) > 1 and instantes[-1] == duracion_ms:
        instantes.pop()
    instantes.append(duracion_ms)
    return instantes


def _cuadros(movimiento, duracion_ms, dx, dy, entrada):
    if movimiento == "ninguna":
        return [Cuadro(0, 0.0, 0.0, 1.0)]
    desvanece = movimiento in DESVANECEN
    cuadros = []
    for ms in _instantes(duracion_ms):
        t = ms / duracion_ms
        avance = (1 - (1 - t) ** 3) if entrada else t ** 3
        if entrada:
            factor = 1 - avance
            opacidad = avance if desvanece else 1.0
        else:
            factor = avance
            opacidad = 1 - avance if desvanece else 1.0
        cuadros.append(Cuadro(ms, dx * factor, dy * factor, opacidad))
    return cuadros


def cuadros_entrada(movimiento, duracion_ms, dx, dy) -> list[Cuadro]:
    """La lista de cuadros de la entrada, del inicial al final."""
    return _cuadros(movimiento, duracion_ms, dx, dy, True)


def cuadros_salida(movimiento, duracion_ms, dx, dy) -> list[Cuadro]:
    """La lista de cuadros de la salida, del inicial al final."""
    return _cuadros(movimiento, duracion_ms, dx, dy, False)
