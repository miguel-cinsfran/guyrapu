# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Tipos de medio, cómo se dice una fila y qué se anuncia al escuchar."""

import unittest

from guyrapu.interaction import medios


class TestTipos(unittest.TestCase):

    def test_cada_extension_da_su_tipo(self):
        for clave, _nombre, extensiones in medios.TIPOS:
            for extension in extensiones:
                with self.subTest(extension=extension):
                    self.assertEqual(medios.tipo_de("archivo" + extension),
                                     clave)

    def test_una_extension_en_mayusculas_tambien_cuenta(self):
        self.assertEqual(medios.tipo_de("RISA.WAV"), "sonido")
        self.assertEqual(medios.tipo_de("LOGO.PNG"), "imagen")

    def test_webp_y_apng_no_son_medios(self):
        for nombre in ("x.webp", "x.apng"):
            with self.subTest(nombre=nombre):
                self.assertFalse(medios.es_medio(nombre))
                self.assertIsNone(medios.tipo_de(nombre))

    def test_el_comodin_lleva_todas_las_extensiones(self):
        for extension in medios.EXTENSIONES:
            self.assertIn("*" + extension, medios.comodin())


class TestFila(unittest.TestCase):

    def test_un_sonido_de_tres_segundos(self):
        self.assertEqual(
            medios.fila({"nombre": "Risa", "tipo": "sonido", "duracion": 3}),
            "Risa, sonido, 3 segundos")

    def test_una_imagen_no_lleva_duracion(self):
        self.assertEqual(
            medios.fila({"nombre": "Logo", "tipo": "imagen", "duracion": 0}),
            "Logo, imagen")

    def test_un_medio_sin_duracion_lo_dice(self):
        self.assertEqual(
            medios.fila({"nombre": "Clip", "tipo": "video", "duracion": 0}),
            "Clip, vídeo, duración desconocida")


class TestEscuchar(unittest.TestCase):

    def test_dice_el_nombre_y_la_descripcion(self):
        self.assertEqual(
            medios.escuchar({"nombre": "Risa", "descripcion": "Una risa"}),
            "Risa. Una risa")

    def test_sin_descripcion_dice_solo_el_nombre(self):
        self.assertEqual(
            medios.escuchar({"nombre": "Risa", "descripcion": ""}), "Risa")


if __name__ == "__main__":
    unittest.main()
