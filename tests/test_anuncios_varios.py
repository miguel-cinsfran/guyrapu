# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de los avisos de la música cuando la acción va sobre varias canciones."""

import unittest

from guyrapu.music import anuncios, anuncios_varios


class TestAnunciosDeVariasCanciones(unittest.TestCase):

    def test_eliminadas_de_la_cola_en_singular_y_plural(self):
        uno = anuncios_varios.aviso_eliminados_de_cola(1)
        varios = anuncios_varios.aviso_eliminados_de_cola(3)
        self.assertEqual(uno.texto, "1 canción eliminada de la cola")
        self.assertEqual(varios.texto, "3 canciones eliminadas de la cola")
        self.assertEqual(uno.importante,
                         anuncios.aviso_quitado_de_cola("A").importante)
        self.assertIsNone(varios.sonido)

    def test_eliminadas_de_la_lista_en_singular_y_plural(self):
        uno = anuncios_varios.aviso_eliminados_de_lista(1)
        varios = anuncios_varios.aviso_eliminados_de_lista(3)
        self.assertEqual(uno.texto, "1 canción eliminada de la lista")
        self.assertEqual(varios.texto, "3 canciones eliminadas de la lista")
        self.assertEqual(uno.importante, anuncios.aviso_tema_quitado().importante)
        self.assertIsNone(varios.sonido)

    def test_agregadas_a_la_lista_en_singular_y_plural(self):
        uno = anuncios_varios.aviso_agregados_a_lista(1, "Rock")
        varios = anuncios_varios.aviso_agregados_a_lista(3, "Rock")
        self.assertEqual(uno.texto, "1 canción agregada a la lista Rock")
        self.assertEqual(varios.texto, "3 canciones agregadas a la lista Rock")
        self.assertEqual(uno.importante,
                         anuncios.aviso_agregado_a_lista("Rock").importante)
        self.assertIsNone(varios.sonido)


if __name__ == "__main__":
    unittest.main()
