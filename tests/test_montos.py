# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Tests del parseo de importes de Super Chat (montos.parsear_monto)."""

import unittest
from types import SimpleNamespace

from guyrapu.capture.montos import (
    monto_y_nivel, nivel_de_color, parsear_monto, sumar_monto,
    texto_importes,
)
from guyrapu.core.config import TIPO_SUPERCHAT, TIPO_STICKER, TIPO_TEXTO


class TestNivelDeColor(unittest.TestCase):

    def test_los_siete_colores_de_youtube(self):
        casos = {
            4280191205: 1,
            4278248959: 2,
            4280150454: 3,
            4294953512: 4,
            4294278144: 5,
            4293467747: 6,
            4293271831: 7,
        }
        for color, nivel in casos.items():
            with self.subTest(color=color):
                self.assertEqual(nivel_de_color(color), nivel)

    def test_desconocido_y_cero_no_tienen_nivel(self):
        self.assertEqual(nivel_de_color(0), 0)
        self.assertEqual(nivel_de_color(123456), 0)
        self.assertEqual(nivel_de_color(None), 0)


class TestMontoYNivel(unittest.TestCase):

    def test_superchat_trae_su_monto_y_su_nivel(self):
        item = SimpleNamespace(amountString="$10.00", bgColor=4294953512)
        self.assertEqual(monto_y_nivel(item, TIPO_SUPERCHAT), ("$10.00", 4))

    def test_sticker_trae_su_monto_y_su_nivel(self):
        item = SimpleNamespace(amountString="$100.00", bgColor=4293271831)
        self.assertEqual(monto_y_nivel(item, TIPO_STICKER), ("$100.00", 7))

    def test_un_mensaje_de_texto_no_trae_nada(self):
        item = SimpleNamespace(amountString="$5.00", bgColor=4280191205)
        self.assertEqual(monto_y_nivel(item, TIPO_TEXTO), ("", 0))


class TestParsearMonto(unittest.TestCase):

    def test_vacio_o_none(self):
        self.assertIsNone(parsear_monto(""))
        self.assertIsNone(parsear_monto(None))

    def test_sin_numero(self):
        self.assertIsNone(parsear_monto("gracias"))

    def test_anglosajon_simple(self):
        self.assertEqual(parsear_monto("$10.00"), ("$", 10.0))

    def test_euro_prefijo_punto_decimal(self):
        self.assertEqual(parsear_monto("€15.50"), ("€", 15.5))

    def test_euro_sufijo_coma_decimal(self):
        self.assertEqual(parsear_monto("5,00 €"), ("€", 5.0))

    def test_europeo_millar_y_decimal(self):
        # 1.234,56 -> 1234.56
        self.assertEqual(parsear_monto("1.234,56 €"), ("€", 1234.56))

    def test_anglosajon_millar_y_decimal(self):
        # 1,234.56 -> 1234.56
        self.assertEqual(parsear_monto("$1,234.56"), ("$", 1234.56))

    def test_sin_decimales_grandes(self):
        self.assertEqual(parsear_monto("¥500"), ("¥", 500.0))

    def test_codigo_divisa_multiletra(self):
        divisa, valor = parsear_monto("PYG 50000")
        self.assertEqual(divisa, "PYG")
        self.assertEqual(valor, 50000.0)

    def test_divisa_desconocida(self):
        # Solo número, sin símbolo reconocible.
        self.assertEqual(parsear_monto("42.00"), ("?", 42.0))

    def test_us_dollar_prefijo_compuesto(self):
        divisa, valor = parsear_monto("US$ 3.50")
        self.assertEqual(divisa, "US$")
        self.assertEqual(valor, 3.5)

    def test_millar_con_coma_sin_decimales(self):
        # Divisas sin decimales: YouTube separa los millares con coma.
        self.assertEqual(parsear_monto("¥1,000"), ("¥", 1000.0))
        self.assertEqual(parsear_monto("₩10,000"), ("₩", 10000.0))
        self.assertEqual(parsear_monto("CA$1,000"), ("CA$", 1000.0))
        self.assertEqual(parsear_monto("¥1,234,567"), ("¥", 1234567.0))

    def test_millar_con_punto_sin_decimales(self):
        self.assertEqual(parsear_monto("Rp 15.000"), ("Rp", 15000.0))
        self.assertEqual(parsear_monto("1.000 €"), ("€", 1000.0))

    def test_una_o_dos_cifras_tras_el_separador_es_decimal(self):
        self.assertEqual(parsear_monto("1,5 €"), ("€", 1.5))
        self.assertEqual(parsear_monto("$1.50"), ("$", 1.5))


class TestSumarMonto(unittest.TestCase):

    def test_acumula_en_el_dict_recibido(self):
        totales = {}
        sumar_monto(totales, "$10.00")
        sumar_monto(totales, "$5.50")
        self.assertEqual(totales, {"$": 15.5})

    def test_ignora_lo_que_no_entiende(self):
        totales = {"€": 1.0}
        sumar_monto(totales, "gracias")
        self.assertEqual(totales, {"€": 1.0})


class TestTextoImportes(unittest.TestCase):

    def test_vacio(self):
        self.assertEqual(texto_importes({}), "")

    def test_una_divisa_con_dos_decimales(self):
        self.assertEqual(texto_importes({"€": 15.5}), "€15.50")

    def test_varias_divisas_sin_decimales(self):
        self.assertEqual(texto_importes({"€": 15.0, "$": 10.0}), "€15, $10")


if __name__ == "__main__":
    unittest.main()
