# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Frase que describe un estilo de aviso para Escuchar, sin ventanas."""

import unittest

from guyrapu.obs import descripcion_estilo, estilos_aviso


class TestDescripcion(unittest.TestCase):

    def test_p6_nombra_todo_lo_pedido(self):
        texto = descripcion_estilo.describir(estilos_aviso.FABRICA[0])
        for fragmento in ("Clásico", "Segoe UI",
                          "5 % del lado menor del vídeo", "Blanco", "Negro",
                          "opacidad de 0 %", "Según la orientación del vídeo",
                          "Fundido al subir", "350 milisegundos", "Fundido",
                          "250 milisegundos"):
            with self.subTest(fragmento=fragmento):
                self.assertIn(fragmento, texto)

    def test_p6_un_color_personalizado_se_dice_por_su_codigo(self):
        estilo = dict(estilos_aviso.FABRICA[0], color_texto="#123456")
        self.assertIn("#123456", descripcion_estilo.describir(estilo))

    def test_p6_los_decimales_van_con_coma(self):
        estilo = dict(estilos_aviso.FABRICA[0], tamano=4.5)
        self.assertIn("4,5 %", descripcion_estilo.describir(estilo))

    def test_p6_agrega_el_aviso_de_contraste_cuando_lo_hay(self):
        estilo = dict(estilos_aviso.FABRICA[0], color_texto="#FFFF00",
                      color_fondo="#FFFFFF", opacidad_fondo=100,
                      ancho_contorno=0)
        aviso = estilos_aviso.aviso_contraste(estilo)
        self.assertTrue(aviso)
        self.assertIn(aviso, descripcion_estilo.describir(estilo))

    def test_p6_sin_contraste_bajo_no_agrega_aviso(self):
        texto = descripcion_estilo.describir(estilos_aviso.FABRICA[0])
        self.assertNotIn("contraste", texto.lower())


if __name__ == "__main__":
    unittest.main()
