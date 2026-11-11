# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de cómo se dicen los espectadores de las dos plataformas."""

import unittest

from guyrapu.capture.estado_sesion import SnapshotSesion, formatear_estado


class TestDosPlataformas(unittest.TestCase):

    def test_corto_nombra_las_dos_con_varios_espectadores(self):
        s = SnapshotSesion(conectado=True, tipo="live_youtube",
                           espectadores=12, espectadores_adicional=30,
                           espectadores_adicional_total=120)
        self.assertEqual(
            formatear_estado(s, {"espectadores"}),
            "En YouTube, 12 espectadores; en TikTok, 30 espectadores ahora, "
            "120 en total.")

    def test_largo_nombra_las_dos_con_varios_espectadores(self):
        s = SnapshotSesion(conectado=True, tipo="live_youtube",
                           espectadores=12, espectadores_adicional=30,
                           espectadores_adicional_total=120)
        self.assertEqual(
            formatear_estado(s, {"espectadores"}, "largo"),
            "Espectadores en YouTube: 12\n"
            "Espectadores en TikTok: 30 ahora, 120 en total")

    def test_corto_usa_el_singular_en_cada_plataforma(self):
        s = SnapshotSesion(conectado=True, tipo="live_youtube",
                           espectadores=1, espectadores_adicional=1,
                           espectadores_adicional_total=120)
        self.assertEqual(
            formatear_estado(s, {"espectadores"}),
            "En YouTube, 1 espectador; en TikTok, 1 espectador ahora, "
            "120 en total.")

    def test_largo_usa_el_singular_en_cada_plataforma(self):
        s = SnapshotSesion(conectado=True, tipo="live_youtube",
                           espectadores=1, espectadores_adicional=1,
                           espectadores_adicional_total=120)
        self.assertEqual(
            formatear_estado(s, {"espectadores"}, "largo"),
            "Espectador en YouTube: 1\n"
            "Espectador en TikTok: 1 ahora, 120 en total")

    def test_corto_con_el_adicional_sin_total(self):
        s = SnapshotSesion(conectado=True, tipo="live_youtube",
                           espectadores=12, espectadores_adicional=30)
        self.assertEqual(
            formatear_estado(s, {"espectadores"}),
            "En YouTube, 12 espectadores; en TikTok, 30 espectadores.")

    def test_largo_con_el_adicional_sin_total(self):
        s = SnapshotSesion(conectado=True, tipo="live_youtube",
                           espectadores=12, espectadores_adicional=30)
        self.assertEqual(
            formatear_estado(s, {"espectadores"}, "largo"),
            "Espectadores en YouTube: 12\nEspectadores en TikTok: 30")


class TestSinAdicional(unittest.TestCase):

    def test_sin_adicional_o_sin_sus_espectadores_queda_como_hoy(self):
        hoy = SnapshotSesion(conectado=True, tipo="live_youtube",
                             espectadores=12)
        self.assertEqual(formatear_estado(hoy, {"espectadores"}),
                         "12 espectadores.")
        self.assertEqual(formatear_estado(hoy, {"espectadores"}, "largo"),
                         "Espectadores: 12")
        sin_espectadores = SnapshotSesion(
            conectado=True, tipo="live_youtube", espectadores=12,
            espectadores_adicional_total=120)
        self.assertEqual(formatear_estado(sin_espectadores, {"espectadores"}),
                         "12 espectadores.")


if __name__ == "__main__":
    unittest.main()
