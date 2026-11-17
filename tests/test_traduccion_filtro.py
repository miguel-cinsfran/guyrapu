# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Qué mensaje del chat vale la pena traducir.

Puro: no toca la captura ni la interfaz.
"""

import unittest

from guyrapu.translation.filtro import traducible


class TestFiltro(unittest.TestCase):

    def test_los_mensajes_propios_no_se_traducen(self):
        self.assertFalse(traducible("hola amigo", propio=True))
        self.assertTrue(traducible("hola amigo"))

    def test_solo_emojis_numeros_enlaces_o_signos_no_se_traducen(self):
        for texto in ("😀👋🔥", "12345", "1.000", "https://example.com/video",
                      "http://youtu.be/abc", "www.example.com", "!!! ???",
                      "+1 555 0100"):
            with self.subTest(texto=texto):
                self.assertFalse(traducible(texto))

    def test_las_palabras_con_emoji_se_traducen(self):
        self.assertTrue(traducible("hola 😀"))
        self.assertTrue(traducible("mirá https://example.com/video"))

    def test_menos_de_tres_letras_no_se_traduce(self):
        for texto in ("ok", "sí", "a1", "", "   "):
            with self.subTest(texto=texto):
                self.assertFalse(traducible(texto))
        self.assertTrue(traducible("abc"))

    def test_las_expresiones_de_chat_no_se_traducen(self):
        for texto in ("gg", "GGG", "ggg!", "xd", "xDD", "lol", "LOLLL",
                      "lol!!", "jaja", "jajaj", "jajajaja", "JAJAJA"):
            with self.subTest(texto=texto):
                self.assertFalse(traducible(texto))

    def test_lo_que_queda_se_traduce(self):
        for texto in ("buen día", "good morning", "bom dia", "lolita",
                      "gg wp", "qué bueno"):
            with self.subTest(texto=texto):
                self.assertTrue(traducible(texto))


if __name__ == "__main__":
    unittest.main()
