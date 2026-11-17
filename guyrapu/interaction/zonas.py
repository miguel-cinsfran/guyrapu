# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Dónde cae una tarjeta en el lienzo según su zona.

Puro y sin wx. Su única razón para cambiar es la geometría del área segura
y de las zonas: lo que tapa TikTok en un vídeo vertical y el margen del
resto de los lienzos.
"""

from __future__ import annotations

from guyrapu.obs.estilos_aviso import ZONAS

_CLAVES = {clave for clave, _nombre in ZONAS}


def es_vertical(ancho, alto) -> bool:
    """Si el lienzo es más alto que ancho."""
    return alto > ancho


def area_segura(ancho, alto) -> tuple[int, int, int, int]:
    """El área del lienzo que no tapa TikTok, como x, y, ancho y alto."""
    if es_vertical(ancho, alto):
        escala_x = ancho / 1080
        escala_y = alto / 1920
        x = round(140 * escala_x)
        y = round(240 * escala_y)
        return (x, y, round(ancho - 280 * escala_x),
                round(alto - 900 * escala_y))
    x = round(ancho * 0.1)
    y = round(alto * 0.1)
    return (x, y, round(ancho * 0.8), round(alto * 0.8))


def resolver(zona, ancho, alto) -> str:
    """La zona concreta de una zona, traduciendo `automatica` y las raras."""
    if zona not in _CLAVES:
        zona = "automatica"
    if zona == "automatica":
        return "arriba_centro" if es_vertical(ancho, alto) else "abajo_centro"
    return zona


def _alinear(alineacion, inicio, tamano_area, tamano_tarjeta, lienzo,
             primero, ultimo):
    if tamano_tarjeta > tamano_area:
        return (lienzo - tamano_tarjeta) / 2
    if alineacion == primero:
        return inicio
    if alineacion == ultimo:
        return inicio + tamano_area - tamano_tarjeta
    return inicio + (tamano_area - tamano_tarjeta) / 2


def posicion(zona, ancho_lienzo, alto_lienzo, ancho_tarjeta,
             alto_tarjeta) -> tuple[int, int]:
    """La esquina superior izquierda de la tarjeta dentro del área segura."""
    vertical, horizontal = resolver(
        zona, ancho_lienzo, alto_lienzo).split("_")
    x_area, y_area, ancho_area, alto_area = area_segura(
        ancho_lienzo, alto_lienzo)
    x = _alinear(horizontal, x_area, ancho_area, ancho_tarjeta, ancho_lienzo,
                 "izquierda", "derecha")
    y = _alinear(vertical, y_area, alto_area, alto_tarjeta, alto_lienzo,
                 "arriba", "abajo")
    return (round(x), round(y))
