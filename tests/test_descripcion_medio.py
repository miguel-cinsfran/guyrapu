# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Limpieza de la descripción que propone la IA para un medio."""

import unittest

from guyrapu.ai import descripcion_medio


class TestLimpiar(unittest.TestCase):

    def test_quita_comillas_y_espacios_de_los_bordes(self):
        casos = (
            ('  "Una risa"  ', "Una risa"),
            ("'Un gato'", "Un gato"),
            ("«Un perro»", "Un perro"),
            ("“Un sol”", "Un sol"),
        )
        for crudo, esperado in casos:
            with self.subTest(crudo=crudo):
                self.assertEqual(descripcion_medio.limpiar(crudo), esperado)

    def test_deja_una_sola_linea_con_espacios_normales(self):
        self.assertEqual(
            descripcion_medio.limpiar("  Una\n risa \t feliz  "),
            "Una risa feliz")

    def test_corta_en_el_ultimo_espacio_antes_del_tope(self):
        esperado = " ".join(["palabra"] * 25)
        self.assertEqual(descripcion_medio.limpiar("palabra " * 50), esperado)
        self.assertLessEqual(len(esperado), 200)

    def test_trescientos_caracteres_sin_espacios_quedan_en_doscientos(self):
        limpio = descripcion_medio.limpiar("a" * 300)
        self.assertEqual(len(limpio), 200)
        self.assertEqual(limpio, "a" * 200)

    def test_nunca_pasa_de_doscientos_ni_tiene_saltos_de_linea(self):
        casos = (
            "b " * 200,
            "c\n" * 250,
            '"' + "d" * 250 + '"',
            "palabra " * 60,
        )
        for crudo in casos:
            with self.subTest(crudo=crudo[:20]):
                limpio = descripcion_medio.limpiar(crudo)
                self.assertLessEqual(len(limpio), 200)
                self.assertNotIn("\n", limpio)
                self.assertNotIn("\r", limpio)
                self.assertEqual(limpio, limpio.strip())


if __name__ == "__main__":
    unittest.main()
