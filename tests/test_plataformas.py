# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas del registro de plataformas de chat."""

import unittest
from unittest import mock

from guyrapu.core import plataformas


class TestRegistroDePlataformas(unittest.TestCase):

    def test_las_plataformas_conocidas_tienen_su_presentacion(self):
        youtube = plataformas.obtener("youtube")
        tiktok = plataformas.obtener("tiktok")
        self.assertEqual((youtube.nombre, youtube.sonido, youtube.moderable),
                         ("YouTube", "mensaje_nuevo", True))
        self.assertEqual((tiktok.nombre, tiktok.sonido, tiktok.moderable),
                         ("TikTok", "mensaje_tiktok", False))

    def test_lo_desconocido_no_inventa_nombre_y_suena_como_siempre(self):
        self.assertIsNone(plataformas.obtener("twitch"))
        self.assertEqual(plataformas.nombre("twitch"), "")
        self.assertEqual(plataformas.sufijo("twitch"), "")
        self.assertEqual(plataformas.sonido("twitch"), "mensaje_nuevo")
        self.assertFalse(plataformas.moderable("twitch"))

    def test_agregar_una_plataforma_alcanza_para_que_aparezca(self):
        nueva = plataformas.Plataforma("twitch", "Twitch", "mensaje_nuevo", False)
        with mock.patch.dict(plataformas.PLATAFORMAS, {"twitch": nueva}):
            self.assertEqual(plataformas.nombre("twitch"), "Twitch")
            self.assertEqual(plataformas.sufijo("twitch"), " - Twitch")
            self.assertEqual(plataformas.sonido("twitch"), "mensaje_nuevo")
            self.assertFalse(plataformas.moderable("twitch"))

    def test_el_nombre_en_la_voz_solo_con_varios_chats_y_la_casilla(self):
        config = {"decir_plataforma": True}
        self.assertEqual(
            plataformas.texto_con_nombre("hola", "tiktok", config, True),
            "hola - TikTok")
        self.assertEqual(
            plataformas.texto_con_nombre("hola", "tiktok", config, False),
            "hola")
        self.assertEqual(
            plataformas.texto_con_nombre("hola", "tiktok", {}, True),
            "hola")


if __name__ == "__main__":
    unittest.main()
