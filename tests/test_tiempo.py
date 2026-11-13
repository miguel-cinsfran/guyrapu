# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas del reloj y del sueño comunes, con su doble."""

import threading
import unittest

from guyrapu.core.tiempo import TIEMPO_REAL, TiempoDoble


class TestTiempoReal(unittest.TestCase):

    def test_el_reloj_avanza(self):
        antes = TIEMPO_REAL.ahora()
        despues = TIEMPO_REAL.ahora()
        self.assertGreaterEqual(despues, antes)


class TestTiempoDoble(unittest.TestCase):

    def test_dormir_sin_parada_avanza_el_reloj(self):
        tiempo = TiempoDoble()
        self.assertFalse(tiempo.dormir(2.5))
        self.assertEqual(tiempo.ahora(), 2.5)
        self.assertEqual(tiempo.dormidas, [2.5])

    def test_una_parada_programada_corta_el_sueno(self):
        tiempo = TiempoDoble()
        parada = threading.Event()
        tiempo.programar_parada(3.0, parada)
        self.assertTrue(tiempo.dormir(10.0, parada))
        self.assertTrue(parada.is_set())
        self.assertEqual(tiempo.ahora(), 3.0)
        self.assertEqual(tiempo.dormidas, [3.0])

    def test_una_parada_ya_puesta_corta_sin_avanzar(self):
        tiempo = TiempoDoble(inicio=5.0)
        parada = threading.Event()
        parada.set()
        self.assertTrue(tiempo.dormir(10.0, parada))
        self.assertEqual(tiempo.ahora(), 5.0)
        self.assertEqual(tiempo.dormidas, [])

    def test_la_parada_posterior_no_corta_este_sueno(self):
        tiempo = TiempoDoble()
        parada = threading.Event()
        tiempo.programar_parada(20.0, parada)
        self.assertFalse(tiempo.dormir(5.0, parada))
        self.assertFalse(parada.is_set())
        self.assertEqual(tiempo.ahora(), 5.0)

    def test_avanzar_mueve_el_reloj(self):
        tiempo = TiempoDoble()
        tiempo.avanzar(7.0)
        self.assertEqual(tiempo.ahora(), 7.0)


if __name__ == "__main__":
    unittest.main()
