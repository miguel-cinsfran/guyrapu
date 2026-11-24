# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""El último total de me gusta del directo, de la captura a la interfaz."""

import unittest

from guyrapu.capture import contador_me_gusta


class TestContadorMeGusta(unittest.TestCase):
    def setUp(self):
        contador_me_gusta.reiniciar()

    def test_total_menor_no_baja_el_guardado(self):
        contador_me_gusta.anotar(1001)
        contador_me_gusta.anotar(950)
        self.assertEqual(contador_me_gusta.total(), 1001)

    def test_total_ausente_o_no_entero_no_se_guarda(self):
        contador_me_gusta.anotar(None)
        contador_me_gusta.anotar("hola")
        self.assertIsNone(contador_me_gusta.total())

    def test_reiniciar_olvida_el_total(self):
        contador_me_gusta.anotar(1001)
        contador_me_gusta.reiniciar()
        self.assertIsNone(contador_me_gusta.total())


if __name__ == "__main__":
    unittest.main()
