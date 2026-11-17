# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
import unittest

from guyrapu.interaction import zonas


class TestAreaSegura(unittest.TestCase):
    def test_vertical_excluye_lo_que_tapa_tiktok(self):
        self.assertEqual(zonas.area_segura(1080, 1920), (140, 240, 800, 1020))

    def test_vertical_escala_en_proporcion_al_lienzo(self):
        self.assertEqual(zonas.area_segura(720, 1280), (93, 160, 533, 680))

    def test_horizontal_deja_el_ochenta_por_ciento_central(self):
        self.assertEqual(zonas.area_segura(1920, 1080), (192, 108, 1536, 864))

    def test_cuadrado_usa_el_ochenta_por_ciento_central(self):
        self.assertEqual(zonas.area_segura(1000, 1000), (100, 100, 800, 800))


class TestPosicion(unittest.TestCase):
    def test_abajo_centro_en_vertical_apoya_el_borde_inferior(self):
        x, y = zonas.posicion("abajo_centro", 1080, 1920, 400, 100)
        self.assertEqual(y + 100, 1260)
        self.assertEqual(x, 340)

    def test_la_misma_zona_escala_con_el_lienzo(self):
        _x, y = zonas.posicion("abajo_centro", 720, 1280, 300, 80)
        self.assertEqual(y + 80, 840)

    def test_arriba_izquierda_en_horizontal_usa_el_margen(self):
        self.assertEqual(
            zonas.posicion("arriba_izquierda", 1920, 1080, 200, 50), (192, 108))

    def test_centro_centra_la_tarjeta_en_el_area_segura(self):
        self.assertEqual(
            zonas.posicion("medio_centro", 1920, 1080, 400, 100), (760, 490))

    def test_una_tarjeta_mas_ancha_que_el_area_se_centra_en_el_lienzo(self):
        x, y = zonas.posicion("arriba_izquierda", 1920, 1080, 2000, 50)
        self.assertEqual((x, y), (-40, 108))


class TestResolver(unittest.TestCase):
    def test_automatica_segun_la_orientacion(self):
        self.assertEqual(
            zonas.resolver("automatica", 1080, 1920), "arriba_centro")
        self.assertEqual(
            zonas.resolver("automatica", 1920, 1080), "abajo_centro")
        self.assertEqual(
            zonas.resolver("automatica", 1000, 1000), "abajo_centro")

    def test_una_zona_desconocida_queda_como_automatica(self):
        self.assertEqual(
            zonas.resolver("inventada", 1080, 1920), "arriba_centro")
        self.assertEqual(
            zonas.resolver("inventada", 1920, 1080), "abajo_centro")

    def test_una_zona_conocida_se_devuelve_tal_cual(self):
        self.assertEqual(
            zonas.resolver("medio_derecha", 1080, 1920), "medio_derecha")

    def test_es_vertical_solo_si_es_mas_alto_que_ancho(self):
        self.assertTrue(zonas.es_vertical(1080, 1920))
        self.assertFalse(zonas.es_vertical(1920, 1080))
        self.assertFalse(zonas.es_vertical(1000, 1000))


if __name__ == "__main__":
    unittest.main()
