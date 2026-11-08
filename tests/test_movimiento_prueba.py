# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de la página con movimiento de la prueba del equipo."""

import base64
import unittest

from guyrapu.obs import movimiento_prueba


class TestPagina(unittest.TestCase):

    def test_el_canvas_ocupa_toda_la_ventana_y_se_mueve(self):
        self.assertIn("<canvas", movimiento_prueba.HTML)
        self.assertIn("window.innerWidth", movimiento_prueba.HTML)
        self.assertIn("window.innerHeight", movimiento_prueba.HTML)
        self.assertIn("requestAnimationFrame", movimiento_prueba.HTML)

    def test_la_pagina_densa_no_usa_ruido_por_pixel(self):
        self.assertIn("CIRCULOS = 1500", movimiento_prueba.HTML)
        self.assertIn("lado = 40", movimiento_prueba.HTML)
        self.assertNotIn("getImageData", movimiento_prueba.HTML)
        self.assertNotIn("putImageData", movimiento_prueba.HTML)

    def test_la_url_decodificada_es_la_pagina_html(self):
        prefijo = "data:text/html;base64,"
        url = movimiento_prueba.url()
        self.assertTrue(url.startswith(prefijo))
        html = base64.b64decode(url[len(prefijo):]).decode("utf-8")
        self.assertEqual(html, movimiento_prueba.HTML)
        self.assertTrue(html.startswith("<!DOCTYPE html>"))
        self.assertIn("<canvas", html)


if __name__ == "__main__":
    unittest.main()
