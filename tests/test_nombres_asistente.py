# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de los nombres de perfil que crea el asistente, sin interfaz."""

import unittest

from guyrapu.obs import nombres_asistente


class TestLibre(unittest.TestCase):

    def test_el_nombre_libre_se_usa_tal_cual(self):
        self.assertEqual(
            nombres_asistente.libre("Guyrapu horizontal", ()),
            "Guyrapu horizontal")

    def test_si_el_nombre_esta_ocupado_se_agrega_el_dos(self):
        self.assertEqual(
            nombres_asistente.libre(
                "Guyrapu horizontal", ["Guyrapu horizontal"]),
            "Guyrapu horizontal 2")

    def test_si_el_dos_tambien_esta_ocupado_se_agrega_el_tres(self):
        self.assertEqual(
            nombres_asistente.libre(
                "Guyrapu horizontal",
                ["Guyrapu horizontal", "Guyrapu horizontal 2"]),
            "Guyrapu horizontal 3")


class TestNombresBase(unittest.TestCase):

    def test_los_tres_nombres_base_son_los_pedidos(self):
        self.assertEqual(nombres_asistente.NOMBRE_HORIZONTAL,
                         "Guyrapu horizontal")
        self.assertEqual(nombres_asistente.NOMBRE_VERTICAL,
                         "Guyrapu vertical")
        self.assertEqual(nombres_asistente.NOMBRE_GRABACION,
                         "Guyrapu grabación")


if __name__ == "__main__":
    unittest.main()
