# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Nombres y siglas de los idiomas de la traducción del chat."""

import unittest

from guyrapu.translation import idiomas
from scripts import generar_nombres_idiomas


class TestNombres(unittest.TestCase):

    def test_ja_tiene_nombre_en_los_dos_idiomas(self):
        self.assertEqual(idiomas.nombre("ja", "es"), "japonés")
        self.assertEqual(idiomas.nombre("ja", "en"), "Japanese")

    def test_un_codigo_con_region_usa_su_parte_de_idioma(self):
        self.assertEqual(idiomas.nombre("zh-CN", "es"), "chino")
        self.assertEqual(idiomas.nombre("zh_CN", "en"), "Chinese")
        self.assertEqual(idiomas.sigla("zh-CN"), "ZH")

    def test_un_codigo_desconocido_no_tiene_nombre_y_se_dice_abreviado(self):
        self.assertIsNone(idiomas.nombre("xx", "es"))
        self.assertEqual(idiomas.sigla("xx"), "XX")
        self.assertEqual(idiomas.mencion("xx", "completo", voz=True), " (XX)")
        self.assertEqual(idiomas.mencion("xx", "completo"), " (XX)")

    def test_el_sufijo_cambia_con_el_idioma_de_la_interfaz(self):
        self.assertEqual(idiomas.sufijo("en", "es"), "del inglés")
        self.assertEqual(idiomas.sufijo("en", "en"), "from English")

    def test_la_tabla_publicada_coincide_con_el_generador(self):
        self.assertEqual(idiomas._tabla(), generar_nombres_idiomas.tabla())


if __name__ == "__main__":
    unittest.main()
