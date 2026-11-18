# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de la decisión de reintentar un enlace que falla antes de sonar."""

import unittest

from guyrapu.music.enlace_vlc import debe_reintentar


class TestDecidirReintento(unittest.TestCase):

    def test_reintenta_si_la_direccion_vino_del_cache_y_no_sono(self):
        self.assertTrue(debe_reintentar(True, False, False, True))

    def test_no_reintenta_si_la_direccion_no_vino_del_cache(self):
        self.assertFalse(debe_reintentar(False, False, False, True))

    def test_no_reintenta_mas_de_una_vez(self):
        self.assertFalse(debe_reintentar(True, False, True, True))

    def test_no_reintenta_si_ya_sono(self):
        self.assertFalse(debe_reintentar(True, True, False, True))

    def test_no_reintenta_si_pidieron_otro_tema(self):
        self.assertFalse(debe_reintentar(True, False, False, False))


if __name__ == "__main__":
    unittest.main()
