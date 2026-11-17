# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""La cortina de pantalla de NVDA se reconoce por la matriz de ampliación."""

import unittest
from unittest import mock

from guyrapu.core import cortina_nvda

# Medida el 16/11/2026 con la cortina puesta: todo en cero salvo las
# posiciones 18 y 24 en 1,0.
MATRIZ_CON_CORTINA = [0.0] * 25
MATRIZ_CON_CORTINA[18] = 1.0
MATRIZ_CON_CORTINA[24] = 1.0

# Sin la cortina la matriz es la identidad.
MATRIZ_SIN_CORTINA = [0.0] * 25
for _posicion in (0, 6, 12, 18, 24):
    MATRIZ_SIN_CORTINA[_posicion] = 1.0


class EsCortinaTest(unittest.TestCase):
    def test_la_matriz_medida_es_cortina(self):
        self.assertTrue(cortina_nvda.es_cortina(MATRIZ_CON_CORTINA))

    def test_la_identidad_no_es_cortina(self):
        self.assertFalse(cortina_nvda.es_cortina(MATRIZ_SIN_CORTINA))


class CortinaPuestaTest(unittest.TestCase):
    def test_la_biblioteca_real_responde_sin_lanzar(self):
        self.assertIn(cortina_nvda.cortina_puesta(), (True, False, None))

    def test_si_no_se_puede_saber_devuelve_none_y_lo_anota(self):
        with mock.patch.object(cortina_nvda.ctypes, "WinDLL",
                               side_effect=OSError("sin DLL")):
            with self.assertLogs("guyrapu.cortina_nvda",
                                 level="DEBUG") as registro:
                self.assertIsNone(cortina_nvda.cortina_puesta())
        self.assertTrue(registro.output)


if __name__ == "__main__":
    unittest.main()
