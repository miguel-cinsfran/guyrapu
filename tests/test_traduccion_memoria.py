# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""La memoria en memoria de lo ya traducido, por texto e idioma destino."""

import unittest

from guyrapu.translation.memoria import Memoria
from guyrapu.translation.proveedores.base import Traduccion


class TestMemoria(unittest.TestCase):

    def test_guarda_y_devuelve_por_texto_e_idioma_destino(self):
        memoria = Memoria()
        traduccion = Traduccion("good morning", "en")
        memoria.guardar("buenos días", "en", traduccion)
        self.assertEqual(memoria.obtener("buenos días", "en"), traduccion)
        self.assertIsNone(memoria.obtener("buenos días", "pt"))
        self.assertIsNone(memoria.obtener("otra cosa", "en"))

    def test_la_clave_ignora_los_bordes_y_las_mayusculas(self):
        memoria = Memoria()
        traduccion = Traduccion("hello", "es")
        memoria.guardar("  Hola  ", "en", traduccion)
        self.assertEqual(memoria.obtener("hola", "en"), traduccion)
        self.assertEqual(memoria.obtener("HOLA", "en"), traduccion)

    def test_guarda_solo_las_quinientas_mas_recientes(self):
        memoria = Memoria()
        for numero in range(500):
            memoria.guardar(f"texto {numero}", "en",
                             Traduccion(f"text {numero}", "es"))
        memoria.guardar("texto 500", "en", Traduccion("text 500", "es"))
        self.assertIsNone(memoria.obtener("texto 0", "en"))
        self.assertIsNotNone(memoria.obtener("texto 1", "en"))
        self.assertIsNotNone(memoria.obtener("texto 500", "en"))


if __name__ == "__main__":
    unittest.main()
