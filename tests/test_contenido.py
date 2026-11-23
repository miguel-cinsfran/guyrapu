# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""La regla común de lo que sale de un comando, una alerta o un mensaje."""

import unittest

from guyrapu.interaction import contenido

_LARGO = "La respuesta tiene {actual} caracteres y el máximo para el chat es {maximo}."


class TestValidar(unittest.TestCase):

    def _validar(self, texto="Hola", medio="", destino="video",
                 nombre="El comando"):
        return contenido.validar(
            texto, medio, destino, nombre=nombre, error_largo=_LARGO)

    def test_con_texto_solo_es_valido(self):
        self.assertEqual(self._validar(), "")

    def test_con_medio_solo_es_valido_en_el_video(self):
        self.assertEqual(self._validar(texto="", medio="fuegos"), "")

    def test_sin_texto_ni_medio_da_el_error_de_quien_lo_saca(self):
        self.assertEqual(self._validar(texto="", medio=""),
                         "El comando necesita un texto o un medio.")
        self.assertEqual(self._validar(
            texto="", medio="", nombre="El mensaje automático"),
            "El mensaje automático necesita un texto o un medio.")

    def test_solo_chat_sin_texto_pide_un_texto(self):
        for destino in ("chat", "ambos"):
            with self.subTest(destino=destino):
                esperado = ("Para mostrarlo en el chat, escribe un texto."
                            if destino == "chat" else "")
                self.assertEqual(
                    self._validar(texto="", medio="fuegos", destino=destino),
                    esperado)

    def test_mas_de_doscientos_caracteres_con_el_chat_da_el_error(self):
        texto = "a" * 201
        self.assertEqual(
            self._validar(texto=texto, destino="chat"),
            "La respuesta tiene 201 caracteres y el máximo para el chat es 200.")
        self.assertEqual(
            self._validar(texto=texto, destino="ambos"),
            "La respuesta tiene 201 caracteres y el máximo para el chat es 200.")

    def test_mas_de_doscientos_caracteres_solo_en_el_video_es_valido(self):
        self.assertEqual(self._validar(texto="a" * 201), "")


if __name__ == "__main__":
    unittest.main()
