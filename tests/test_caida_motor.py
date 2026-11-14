# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Racha de fallos de un motor de voz local: cuándo avisa y cuándo calla."""

import unittest

from guyrapu.voice.caida_motor import CaidaMotor


class TestCaidaMotor(unittest.TestCase):

    def test_primera_avisa_segunda_no_y_exito_reinicia(self):
        caida = CaidaMotor()
        self.assertEqual(
            caida.fallo("Phonon"),
            "Phonon no responde: se usa la voz de Windows.")
        self.assertIsNone(caida.fallo("Phonon"))
        caida.exito()
        self.assertEqual(
            caida.fallo("Phonon"),
            "Phonon no responde: se usa la voz de Windows.")


if __name__ == "__main__":
    unittest.main()
