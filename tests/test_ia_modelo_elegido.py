# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas del aviso del modelo elegido al terminar el sondeo de la clave."""

import unittest

from guyrapu.ai import opciones_ia
from guyrapu.ai import sondeo_gratis


class TestAvisoModeloElegido(unittest.TestCase):

    def test_de_pago_avisa_que_no_es_gratuito(self):
        resultados = {"elegido": sondeo_gratis.DE_PAGO}
        self.assertEqual(
            opciones_ia.aviso_modelo_elegido(resultados, "elegido"),
            "El modelo elegido, elegido, no está en el nivel gratuito de tu "
            "clave. Elige uno de los gratis.")

    def test_sin_saber_avisa_que_no_respondio(self):
        resultados = {"elegido": sondeo_gratis.SIN_SABER}
        self.assertEqual(
            opciones_ia.aviso_modelo_elegido(resultados, "elegido"),
            "El modelo elegido, elegido, no respondió con tu clave. "
            "Elige otro.")

    def test_respondio_no_avisa(self):
        resultados = {"elegido": sondeo_gratis.RESPONDE}
        self.assertEqual(
            opciones_ia.aviso_modelo_elegido(resultados, "elegido"), "")

    def test_no_probado_no_avisa(self):
        resultados = {"otro": sondeo_gratis.DE_PAGO}
        self.assertEqual(
            opciones_ia.aviso_modelo_elegido(resultados, "elegido"), "")

    def test_sin_modelo_elegido_no_avisa(self):
        resultados = {"elegido": sondeo_gratis.SIN_SABER}
        self.assertEqual(
            opciones_ia.aviso_modelo_elegido(resultados, ""), "")


if __name__ == "__main__":
    unittest.main()
