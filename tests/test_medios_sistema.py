# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Tabla de botones y datos del tema de los controles de medios, puros."""

import unittest

from guyrapu.music import medios_sistema
from guyrapu.music.modelo import Tema


class TestAccionDeBoton(unittest.TestCase):

    def test_cada_boton_da_su_accion(self):
        casos = {
            "PLAY": "musica_play",
            "PAUSE": "musica_play",
            "NEXT": "musica_siguiente",
            "PREVIOUS": "musica_anterior",
            "STOP": "musica_detener",
        }
        for boton, accion in casos.items():
            with self.subTest(boton=boton):
                self.assertEqual(medios_sistema.accion_de_boton(boton), accion)

    def test_uno_desconocido_no_da_accion(self):
        self.assertIsNone(medios_sistema.accion_de_boton("RECORD"))
        self.assertIsNone(medios_sistema.accion_de_boton(None))


class TestTituloYArtista(unittest.TestCase):

    def test_tema_local_da_titulo_y_artista(self):
        tema = Tema("C:/música/tema.mp3", "La canción", "La banda")
        self.assertEqual(medios_sistema.titulo_y_artista(tema),
                         ("La canción", "La banda"))

    def test_tema_de_youtube_da_titulo_y_sin_artista(self):
        tema = Tema("https://www.youtube.com/watch?v=abc123", "Un vídeo")
        self.assertEqual(medios_sistema.titulo_y_artista(tema),
                         ("Un vídeo", ""))

    def test_sin_tema_no_da_nada(self):
        self.assertEqual(medios_sistema.titulo_y_artista(None), ("", ""))


if __name__ == "__main__":
    unittest.main()
