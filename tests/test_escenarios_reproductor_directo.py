# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de la lógica pura del escenario reproductor_directo, sin ventanas."""

import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "qa"))

import escenarios_reproductor_directo as escenario  # noqa: E402


class TestContinuidad(unittest.TestCase):

    def test_todas_las_lecturas_playing_no_hay_problema(self):
        lecturas = [(0.0, "playing"), (5.0, "playing"), (60.0, "playing")]
        self.assertIsNone(escenario.revisar_continuidad(lecturas))

    def test_una_lectura_que_no_es_playing_dice_cual(self):
        lecturas = [(0.0, "playing"), (5.0, "playing"), (10.0, "buffering")]
        problema = escenario.revisar_continuidad(lecturas)
        self.assertIn("lectura 3", problema)
        self.assertIn("10", problema)
        self.assertIn("buffering", problema)

    def test_un_corte_anunciado_falla_y_dice_que_dijo(self):
        lecturas = [(0.0, "playing"), (5.0, "playing")]
        problema = escenario.revisar_continuidad(
            lecturas, ["El directo se interrumpió"])
        self.assertIn("corte", problema)
        self.assertIn("El directo se interrumpió", problema)


class TestVueltaTrasElCorte(unittest.TestCase):

    def test_vuelve_a_los_20_segundos(self):
        lecturas = [(0.0, "playing"), (2.0, "buffering"), (20.0, "playing")]
        self.assertEqual(escenario.segundos_hasta_volver(lecturas, 45.0),
                         (20.0, True))

    def test_sin_vuelta_no_cuenta(self):
        lecturas = [(0.0, "playing"), (2.0, "buffering"),
                    (44.0, "buffering")]
        self.assertEqual(escenario.segundos_hasta_volver(lecturas, 45.0),
                         (None, False))


if __name__ == "__main__":
    unittest.main()
