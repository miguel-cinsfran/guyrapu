# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Las órdenes que el animador recibe para una tarjeta del vídeo.

Puro y sin wx. Su única razón para cambiar es cómo se traduce una tarjeta
mostrada y su estilo a los cuadros que mueven el elemento en OBS.
"""

from __future__ import annotations

from guyrapu.interaction import animacion
from guyrapu.obs import escena_guyrapu


def _orden(elemento, cuadros) -> dict:
    return {
        "tipo": "animar",
        "escena": escena_guyrapu.ESCENA,
        "elemento": elemento,
        "fuente_filtro": escena_guyrapu.TARJETA,
        "filtro": escena_guyrapu.OPACIDAD,
        "x": 0,
        "y": 0,
        "cuadros": [[cuadro.ms, cuadro.dx, cuadro.dy, cuadro.opacidad]
                    for cuadro in cuadros],
    }


def ocultar_antes(elemento, ancho_lienzo) -> dict:
    """Deja el elemento fuera del lienzo y opaco a cero en un solo cuadro.

    El elemento abarca el lienzo entero; la tarjeta ocupa su lugar adentro.
    Por eso el corrimiento se mide contra el lienzo y no contra la tarjeta.
    """
    cuadro = animacion.Cuadro(0, ancho_lienzo * 10, 0.0, 0.0)
    return _orden(elemento, [cuadro])


def _movimiento(elemento, estilo, clave, milisegundos, ancho, alto) -> dict:
    movimiento = str(estilo.get(clave, "fundido"))
    dx, dy = animacion.desplazamiento(
        movimiento, 0, 0, ancho, alto, ancho, alto)
    duracion = int(estilo.get(milisegundos, 350))
    cuadros = (animacion.cuadros_entrada(movimiento, duracion, dx, dy)
               if clave == "entrada"
               else animacion.cuadros_salida(movimiento, duracion, dx, dy))
    return _orden(elemento, cuadros)


def entrada(elemento, estilo, ancho_lienzo, alto_lienzo) -> dict:
    """Los cuadros de la entrada con el movimiento y la duración del estilo."""
    return _movimiento(elemento, estilo, "entrada", "ms_entrada",
                       ancho_lienzo, alto_lienzo)


def salida(elemento, estilo, ancho_lienzo, alto_lienzo) -> dict:
    """Los cuadros de la salida con el movimiento y la duración del estilo."""
    return _movimiento(elemento, estilo, "salida", "ms_salida",
                       ancho_lienzo, alto_lienzo)
