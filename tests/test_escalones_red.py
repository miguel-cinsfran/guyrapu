# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de los escalones de la prueba de conexión, sin OBS ni ventanas."""

import unittest

from guyrapu.obs import escalones_red


class TestHaciaAbajo(unittest.TestCase):

    def test_desde_2500_baja_al_setenta_y_al_cincuenta(self):
        self.assertEqual(escalones_red.hacia_abajo(2500), (1800, 1300))

    def test_desde_6000_baja_al_setenta_y_al_cincuenta(self):
        self.assertEqual(escalones_red.hacia_abajo(6000), (4200, 3000))

    def test_desde_1200_no_baja_de_mil(self):
        self.assertEqual(escalones_red.hacia_abajo(1200), ())


class TestHaciaArriba(unittest.TestCase):

    def test_desde_2500_sube_al_ciento_cincuenta_y_al_doscientos(self):
        self.assertEqual(escalones_red.hacia_arriba(2500), (3800, 5000))

    def test_desde_6000_sube_hasta_el_tope_de_12000(self):
        self.assertEqual(escalones_red.hacia_arriba(6000), (9000, 12000))

    def test_desde_1200_sube_al_ciento_cincuenta_y_al_doscientos(self):
        self.assertEqual(escalones_red.hacia_arriba(1200), (1800, 2400))

    def test_desde_12000_no_pasa_el_tope(self):
        self.assertEqual(escalones_red.hacia_arriba(12000), ())


class TestAguanta(unittest.TestCase):

    def test_el_limite_de_uno_por_ciento_aguanta(self):
        self.assertTrue(escalones_red.aguanta(1, 100))
        self.assertTrue(escalones_red.aguanta(0, 100))

    def test_pasarse_del_uno_por_ciento_no_aguanta(self):
        self.assertFalse(escalones_red.aguanta(2, 100))

    def test_sin_cuadros_no_aguanta(self):
        self.assertFalse(escalones_red.aguanta(0, 0))
        self.assertFalse(escalones_red.aguanta(5, 0))


if __name__ == "__main__":
    unittest.main()
