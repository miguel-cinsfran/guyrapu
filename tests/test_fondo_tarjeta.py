# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas del generador del fondo PNG de una tarjeta de aviso."""

import struct
import unittest
import zlib

from guyrapu.obs.fondo_tarjeta import Fondo, fondo


def _pixel(filas, x, y):
    base = x * 4
    return tuple(filas[y][base:base + 4])


class FondoTarjetaTest(unittest.TestCase):
    def _decodificar(self, png):
        self.assertEqual(png[:8], b"\x89PNG\r\n\x1a\n")
        posicion = 8
        ancho = alto = None
        idat = b""
        visto_iend = False
        while posicion + 12 <= len(png):
            largo, tipo = struct.unpack(">I4s", png[posicion:posicion + 8])
            cuerpo = png[posicion + 8:posicion + 8 + largo]
            crc = struct.unpack(
                ">I", png[posicion + 8 + largo:posicion + 12 + largo])[0]
            self.assertEqual(crc, zlib.crc32(tipo + cuerpo) & 0xffffffff)
            if tipo == b"IHDR":
                ancho, alto, profundidad, color, compresion, filtro, \
                    entrelazado = struct.unpack(">IIBBBBB", cuerpo)
                self.assertEqual((profundidad, color, compresion, filtro,
                                  entrelazado), (8, 6, 0, 0, 0))
            elif tipo == b"IDAT":
                idat += cuerpo
            elif tipo == b"IEND":
                visto_iend = True
            posicion += 12 + largo
        self.assertTrue(visto_iend)
        self.assertIsNotNone(ancho)
        self.assertTrue(idat)
        crudo = zlib.decompress(idat)
        paso = ancho * 4
        self.assertEqual(len(crudo), alto * (1 + paso))
        filas = []
        for y in range(alto):
            inicio = y * (1 + paso)
            self.assertEqual(crudo[inicio], 0)
            filas.append(crudo[inicio + 1:inicio + 1 + paso])
        return ancho, alto, filas

    def test_p1_png_rgba_con_color_y_origen(self):
        resultado = fondo(40, 20, "#3366CC", 100, False, False, 1)
        self.assertIsInstance(resultado, Fondo)
        ancho, alto, filas = self._decodificar(resultado.png)
        self.assertEqual((ancho, alto), (40, 20))
        self.assertEqual((resultado.ancho, resultado.alto), (40, 20))
        self.assertEqual((resultado.x_tarjeta, resultado.y_tarjeta), (0, 0))
        self.assertEqual(_pixel(filas, 20, 10), (0x33, 0x66, 0xCC, 255))

    def test_p1_opacidad_cero_es_transparente(self):
        resultado = fondo(10, 5, "#FFFFFF", 0, False, False, 1)
        ancho, alto, filas = self._decodificar(resultado.png)
        self.assertEqual((ancho, alto), (10, 5))
        for y in range(alto):
            for x in range(ancho):
                self.assertEqual(_pixel(filas, x, y), (0, 0, 0, 0))

    def test_p2_esquina_redondeada_suaviza_el_borde(self):
        resultado = fondo(80, 40, "#FFFFFF", 100, True, False, 1)
        _, _, filas = self._decodificar(resultado.png)
        self.assertEqual(_pixel(filas, 0, 0)[3], 0)
        alpha = _pixel(filas, 4, 4)[3]
        self.assertTrue(0 < alpha < 255)

    def test_p2_el_radio_crece_con_la_escala(self):
        mitad = fondo(80, 40, "#FFFFFF", 100, True, False, 0.5)
        entera = fondo(80, 40, "#FFFFFF", 100, True, False, 1)
        _, _, filas_mitad = self._decodificar(mitad.png)
        _, _, filas_entera = self._decodificar(entera.png)
        self.assertGreater(_pixel(filas_mitad, 2, 2)[3], 0)
        self.assertEqual(_pixel(filas_entera, 2, 2)[3], 0)

    def test_p2_tarjeta_recta_es_exacta(self):
        resultado = fondo(30, 20, "#FFFFFF", 100, False, False, 1)
        _, _, filas = self._decodificar(resultado.png)
        self.assertEqual(_pixel(filas, 0, 0), (255, 255, 255, 255))
        self.assertEqual(_pixel(filas, 29, 19), (255, 255, 255, 255))

    def test_p3_sin_sombra_la_imagen_es_la_tarjeta(self):
        resultado = fondo(60, 30, "#000000", 100, False, False, 1)
        self.assertEqual((resultado.ancho, resultado.alto), (60, 30))
        self.assertEqual((resultado.x_tarjeta, resultado.y_tarjeta), (0, 0))

    def test_p3_con_sombra_agrega_margen_y_corre_la_tarjeta(self):
        resultado = fondo(60, 30, "#000000", 100, False, True, 1)
        self.assertEqual((resultado.ancho, resultado.alto), (92, 62))
        self.assertEqual((resultado.x_tarjeta, resultado.y_tarjeta), (16, 16))

    def test_p4_sombra_negra_semiopaca_debajo_y_nada_mas_alla(self):
        resultado = fondo(200, 100, "#FFFFFF", 100, False, True, 1)
        _, alto, filas = self._decodificar(resultado.png)
        rojo, verde, azul, alpha = _pixel(filas, 100, 116)
        self.assertEqual((rojo, verde, azul), (0, 0, 0))
        self.assertTrue(0 < alpha < 255)
        self.assertEqual(_pixel(filas, 8, alto - 1)[3], 0)

    def test_p4_no_oscurece_el_fondo_semitransparente(self):
        resultado = fondo(200, 100, "#FFFFFF", 50, False, True, 1)
        _, _, filas = self._decodificar(resultado.png)
        self.assertEqual(_pixel(filas, 116, 66), (255, 255, 255, 128))

    def test_p5_interior_con_color_y_opacidad_exactos(self):
        resultado = fondo(100, 60, "#FFFFFF", 90, True, True, 1)
        _, _, filas = self._decodificar(resultado.png)
        self.assertEqual(_pixel(filas, 66, 46), (255, 255, 255, 230))


if __name__ == "__main__":
    unittest.main()
