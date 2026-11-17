# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Dibuja el fondo PNG de una tarjeta de aviso, sin OBS y sin escribir.

Recibe los valores ya resueltos del estilo y devuelve el PNG RGBA junto con
dónde empieza la tarjeta dentro de la imagen. No conoce estilos ni archivos.
"""

from dataclasses import dataclass
import struct
import zlib

_RADIO = 16.0
_DESPLAZAMIENTO = 4.0
_DIFUMINADO = 12.0
_ALFA_SOMBRA = 0.35


@dataclass(frozen=True)
class Fondo:
    png: bytes
    ancho: int
    alto: int
    x_tarjeta: int
    y_tarjeta: int


def _distancia(px, py, izquierda, arriba, derecha, abajo, radio) -> float:
    """Distancia con signo al rectángulo redondeado: negativa por dentro."""
    qx = abs(px - (izquierda + derecha) / 2) - (
        (derecha - izquierda) / 2 - radio)
    qy = abs(py - (arriba + abajo) / 2) - ((abajo - arriba) / 2 - radio)
    fuera = (max(qx, 0.0) ** 2 + max(qy, 0.0) ** 2) ** 0.5
    return fuera + min(max(qx, qy), 0.0) - radio


def _cobertura(distancia) -> float:
    return max(0.0, min(1.0, 0.5 - distancia))


def _caida(distancia, difuminado) -> float:
    """De 1 en el borde de la sombra a 0 al final del difuminado, suave."""
    if distancia <= 0:
        return 1.0
    if distancia >= difuminado:
        return 0.0
    proporcion = 1.0 - distancia / difuminado
    return proporcion * proporcion * (3.0 - 2.0 * proporcion)


def _pixel(x, y, forma) -> bytes:
    (rojo, verde, azul, alfa, izquierda, arriba, derecha, abajo,
     s_izquierda, s_arriba, s_derecha, s_abajo, radio, radio_sdf,
     difuminado, redondeadas, sombra) = forma
    px, py = x + 0.5, y + 0.5
    if redondeadas:
        cobertura = _cobertura(_distancia(
            px, py, izquierda, arriba, derecha, abajo, radio))
    else:
        cobertura = (1.0 if izquierda <= x < derecha
                     and arriba <= y < abajo else 0.0)
    alpha = alfa * cobertura
    if sombra:
        distancia = _distancia(px, py, s_izquierda, s_arriba, s_derecha,
                               s_abajo, radio_sdf)
        # La sombra solo se ve donde la tarjeta no cubre.
        alpha += (255.0 * _ALFA_SOMBRA * _caida(distancia, difuminado)
                  * (1.0 - cobertura))
    if alpha <= 0:
        return b"\x00\x00\x00\x00"
    porcion = alfa * cobertura
    return bytes((
        round(rojo * porcion / alpha),
        round(verde * porcion / alpha),
        round(azul * porcion / alpha),
        round(alpha),
    ))


def _fila(y, ancho_imagen, forma, zona) -> bytes:
    """Una fila, calculando solo los tramos del borde y repitiendo el centro."""
    if ancho_imagen <= 2 * zona:
        return b"".join(_pixel(x, y, forma) for x in range(ancho_imagen))
    izquierda = b"".join(_pixel(x, y, forma) for x in range(zona))
    medio = _pixel(ancho_imagen // 2, y, forma) * (ancho_imagen - 2 * zona)
    derecha = b"".join(_pixel(x, y, forma)
                       for x in range(ancho_imagen - zona, ancho_imagen))
    return izquierda + medio + derecha


def _qy(py, arriba, abajo, radio) -> float:
    return abs(py - (arriba + abajo) / 2) - ((abajo - arriba) / 2 - radio)


def _es_recta(y, forma) -> bool:
    """Si la fila repite el perfil horizontal de la zona recta de la forma."""
    arriba, abajo = forma[5], forma[7]
    s_arriba, s_abajo = forma[9], forma[11]
    radio_sdf, sombra = forma[13], forma[16]
    py = y + 0.5
    if _qy(py, arriba, abajo, radio_sdf) > 0:
        return False
    return not sombra or _qy(py, s_arriba, s_abajo, radio_sdf) <= 0


def _trozo(tipo, cuerpo) -> bytes:
    return (struct.pack(">I", len(cuerpo)) + tipo + cuerpo
            + struct.pack(">I", zlib.crc32(tipo + cuerpo) & 0xffffffff))


def _png(ancho, alto, crudo) -> bytes:
    return (b"\x89PNG\r\n\x1a\n"
            + _trozo(b"IHDR", struct.pack(">IIBBBBB", ancho, alto, 8, 6,
                                          0, 0, 0))
            + _trozo(b"IDAT", zlib.compress(crudo))
            + _trozo(b"IEND", b""))


def fondo(ancho, alto, color, opacidad, redondeadas, sombra,
          escala) -> Fondo:
    """El PNG de una tarjeta de `ancho` por `alto`, con sombra opcional.

    `color` es #RRGGBB y `opacidad` va de 0 a 100. `escala` es el lado menor
    del lienzo dividido por 1080: el radio, el desplazamiento y el difuminado
    crecen con ella. Con sombra, el margen es lo que ocupa la sombra hacia
    afuera y la tarjeta queda corrida ese margen.
    """
    margen = (int(round((_DESPLAZAMIENTO + _DIFUMINADO) * escala))
              if sombra else 0)
    ancho_imagen = ancho + 2 * margen
    alto_imagen = alto + 2 * margen
    izquierda, arriba = margen, margen
    derecha, abajo = margen + ancho, margen + alto
    radio = _RADIO * escala
    radio_sdf = radio if redondeadas else 0.0
    desplazamiento = _DESPLAZAMIENTO * escala
    difuminado = _DIFUMINADO * escala
    alfa = int(round(255 * opacidad / 100))
    rojo, verde, azul = (int(color[1:3], 16), int(color[3:5], 16),
                         int(color[5:7], 16))
    forma = (rojo, verde, azul, alfa, izquierda, arriba, derecha, abajo,
             izquierda, arriba + desplazamiento, derecha,
             abajo + desplazamiento, radio, radio_sdf, difuminado,
             redondeadas, sombra)
    zona = margen + int(round(radio + difuminado)) + 2
    filas = []
    fila_recta = None
    for y in range(alto_imagen):
        if _es_recta(y, forma):
            if fila_recta is None:
                fila_recta = _fila(y, ancho_imagen, forma, zona)
            fila = fila_recta
        else:
            fila = _fila(y, ancho_imagen, forma, zona)
        filas.append(b"\x00" + fila)
    return Fondo(_png(ancho_imagen, alto_imagen, b"".join(filas)),
                 ancho_imagen, alto_imagen, margen, margen)
