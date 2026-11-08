# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Rectángulo del lienzo que ocupa de verdad la imagen de una fuente de OBS.

Sigue la cuenta de `update_item_transform` y `calculate_bounds_data` de
`obs-scene.c`: tamaño de origen menos recorte, escala, marco con su
alineación, alineación de la fuente, giro y espejo. Es lógica pura: recibe
el diccionario `sceneItemTransform` que entrega el WebSocket.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

_IZQUIERDA = 1
_DERECHA = 2
_ARRIBA = 4
_ABAJO = 8

_NINGUNO = "NONE"
_INNER = "SCALE_INNER"
_OUTER = "SCALE_OUTER"
_A_ANCHO = "SCALE_TO_WIDTH"
_A_ALTO = "SCALE_TO_HEIGHT"
_ESTIRAR = "STRETCH"
_MAXIMO = "MAX_ONLY"


@dataclass(frozen=True, slots=True)
class Medida:
    """Lo que dibuja OBS de una fuente en el lienzo.

    Los cuatro números encierran la imagen girada (con giro, la caja
    alineada a los ejes que la contiene). `deformacion` es la proporción
    dibujada sobre la de origen: 1,0 sin deformar, mayor a lo ancho y menor
    a lo alto.
    """

    izquierda: float
    arriba: float
    ancho: float
    alto: float
    tiene_imagen: bool
    deformacion: float = 1.0

    @property
    def rectangulo(self) -> tuple:
        return self.izquierda, self.arriba, self.ancho, self.alto


def _numero(valor) -> float:
    try:
        return float(valor or 0)
    except (TypeError, ValueError):
        return 0.0


def _escala(valor) -> float:
    if valor is None:
        return 1.0
    try:
        return float(valor)
    except (TypeError, ValueError):
        return 1.0


def _ancla(valor, tamano) -> float:
    if valor & _DERECHA:
        return tamano
    if valor & _IZQUIERDA:
        return 0.0
    return tamano / 2


def _ancla_vertical(valor, tamano) -> float:
    if valor & _ABAJO:
        return tamano
    if valor & _ARRIBA:
        return 0.0
    return tamano / 2


def _tipo(valor) -> str:
    texto = str(valor or "").upper()
    if texto.startswith("OBS_BOUNDS_"):
        texto = texto[len("OBS_BOUNDS_"):]
    return texto


def _colocar(inicio, tamano_marco, tamano_contenido, alineacion, vertical=False):
    ancla = (_ancla_vertical(alineacion, tamano_marco) if vertical
             else _ancla(alineacion, tamano_marco))
    if alineacion & (_ABAJO if vertical else _DERECHA):
        return inicio + tamano_marco - tamano_contenido
    if alineacion & (_ARRIBA if vertical else _IZQUIERDA):
        return inicio
    return inicio + ancla - tamano_contenido / 2


def _sin_marco(posicion, alineacion, escala_x, escala_y,
               ancho_origen, alto_origen):
    firmado_x = ancho_origen * escala_x
    firmado_y = alto_origen * escala_y
    izquierda = (posicion[0] - _ancla(alineacion, firmado_x)
                 + min(0.0, firmado_x))
    arriba = (posicion[1] - _ancla_vertical(alineacion, firmado_y)
              + min(0.0, firmado_y))
    return izquierda, arriba, abs(firmado_x), abs(firmado_y)


def _escala_de_marco(tipo, escala_x, escala_y, ancho_origen, alto_origen,
                     ancho_marco, alto_marco):
    """Escala que aplica el marco, y el tipo que termina mandando."""
    dibujado_x = ancho_origen * abs(escala_x)
    dibujado_y = alto_origen * abs(escala_y)
    aspecto_item = dibujado_x / dibujado_y if dibujado_y else math.inf
    aspecto_marco = ancho_marco / alto_marco if alto_marco else math.inf
    efectivo = tipo
    if tipo == _MAXIMO and (dibujado_x > ancho_marco
                            or dibujado_y > alto_marco):
        efectivo = _INNER
    if efectivo in (_INNER, _OUTER):
        use_ancho = aspecto_marco < aspecto_item
        if efectivo == _OUTER:
            use_ancho = not use_ancho
        factor = ((ancho_marco / dibujado_x if dibujado_x else 1.0)
                  if use_ancho else
                  (alto_marco / dibujado_y if dibujado_y else 1.0))
        escala_x *= factor
        escala_y *= factor
    elif efectivo == _A_ANCHO:
        factor = ancho_marco / dibujado_x if dibujado_x else 1.0
        escala_x *= factor
        escala_y *= factor
    elif efectivo == _A_ALTO:
        factor = alto_marco / dibujado_y if dibujado_y else 1.0
        escala_x *= factor
        escala_y *= factor
    elif efectivo == _ESTIRAR:
        escala_x = math.copysign(
            ancho_marco / ancho_origen if ancho_origen else 0.0,
            escala_x if escala_x else 1.0)
        escala_y = math.copysign(
            alto_marco / alto_origen if alto_origen else 0.0,
            escala_y if escala_y else 1.0)
    return escala_x, escala_y, efectivo


def _con_marco(posicion, alineacion, escala_x, escala_y, ancho_origen,
               alto_origen, tipo, ancho_marco, alto_marco, alineacion_marco,
               crop_to_bounds):
    escala_x, escala_y, efectivo = _escala_de_marco(
        tipo, escala_x, escala_y, ancho_origen, alto_origen,
        ancho_marco, alto_marco)
    contenido_x = ancho_origen * abs(escala_x)
    contenido_y = alto_origen * abs(escala_y)
    caja_x = posicion[0] - _ancla(alineacion, ancho_marco)
    caja_y = posicion[1] - _ancla_vertical(alineacion, alto_marco)
    izquierda = _colocar(caja_x, ancho_marco, contenido_x, alineacion_marco)
    arriba = _colocar(caja_y, alto_marco, contenido_y, alineacion_marco,
                      vertical=True)
    if crop_to_bounds and efectivo in (_OUTER, _A_ANCHO, _A_ALTO):
        derecha = min(izquierda + contenido_x, caja_x + ancho_marco)
        abajo = min(arriba + contenido_y, caja_y + alto_marco)
        izquierda = max(izquierda, caja_x)
        arriba = max(arriba, caja_y)
        contenido_x = max(0.0, derecha - izquierda)
        contenido_y = max(0.0, abajo - arriba)
    return izquierda, arriba, contenido_x, contenido_y


def _caja_girada(posicion, izquierda, arriba, ancho, alto, giro):
    if not giro:
        return izquierda, arriba, ancho, alto
    radianes = math.radians(giro)
    coseno, seno = math.cos(radianes), math.sin(radianes)
    puntos = []
    for x, y in ((izquierda, arriba), (izquierda + ancho, arriba),
                 (izquierda + ancho, arriba + alto),
                 (izquierda, arriba + alto)):
        dx, dy = x - posicion[0], y - posicion[1]
        puntos.append((posicion[0] + dx * coseno - dy * seno,
                       posicion[1] + dx * seno + dy * coseno))
    izquierda = min(punto[0] for punto in puntos)
    arriba = min(punto[1] for punto in puntos)
    derecha = max(punto[0] for punto in puntos)
    abajo = max(punto[1] for punto in puntos)
    return izquierda, arriba, derecha - izquierda, abajo - arriba


def medir(transformacion) -> Medida | None:
    """La medida de la fuente, o None si la transformación no sirve."""
    if not isinstance(transformacion, dict):
        return None
    try:
        posicion = (float(transformacion["positionX"]),
                    float(transformacion["positionY"]))
    except (KeyError, TypeError, ValueError):
        return None
    origen_x = _numero(transformacion.get("sourceWidth"))
    origen_y = _numero(transformacion.get("sourceHeight"))
    if origen_x > 0 and origen_y > 0:
        escala_x = _escala(transformacion.get("scaleX"))
        escala_y = _escala(transformacion.get("scaleY"))
    else:
        origen_x = _numero(transformacion.get("width"))
        origen_y = _numero(transformacion.get("height"))
        escala_x = escala_y = 1.0
    ancho_origen = origen_x - _numero(transformacion.get("cropLeft")) \
        - _numero(transformacion.get("cropRight"))
    alto_origen = origen_y - _numero(transformacion.get("cropTop")) \
        - _numero(transformacion.get("cropBottom"))
    tiene_imagen = ancho_origen > 0 and alto_origen > 0
    if not tiene_imagen:
        return Medida(posicion[0], posicion[1], 0.0, 0.0, False)
    alineacion = int(_numero(transformacion.get("alignment")))
    tipo = _tipo(transformacion.get("boundsType"))
    ancho_marco = _numero(transformacion.get("boundsWidth"))
    alto_marco = _numero(transformacion.get("boundsHeight"))
    if tipo not in ("", _NINGUNO) and ancho_marco > 0 and alto_marco > 0:
        izquierda, arriba, ancho, alto = _con_marco(
            posicion, alineacion, escala_x, escala_y, ancho_origen,
            alto_origen, tipo, ancho_marco, alto_marco,
            int(_numero(transformacion.get("boundsAlignment"))),
            bool(transformacion.get("cropToBounds")))
    else:
        izquierda, arriba, ancho, alto = _sin_marco(
            posicion, alineacion, escala_x, escala_y, ancho_origen, alto_origen)
    ancho_dibujado, alto_dibujado = ancho, alto
    izquierda, arriba, ancho, alto = _caja_girada(
        posicion, izquierda, arriba, ancho, alto,
        _numero(transformacion.get("rotation")))
    aspecto_origen = ancho_origen / alto_origen if alto_origen else 1.0
    aspecto_dibujado = (ancho_dibujado / alto_dibujado
                        if alto_dibujado else 1.0)
    deformacion = (aspecto_dibujado / aspecto_origen
                   if aspecto_origen else 1.0)
    return Medida(izquierda, arriba, ancho, alto, True, deformacion)
