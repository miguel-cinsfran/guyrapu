# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Cuadro de un medio: volumen propio, orden de Tab y letras de acceso.

Abre ventanas.
"""

import unittest

import wx

from guyrapu.ui import medio_cuadro
from tests.letras_acceso import letras_repetidas
from tests.ventanas_prueba import app_de_prueba, destruir


def _datos(**cambios):
    datos = {
        "nombre": "Risa",
        "descripcion": "Una risa",
        "tipo": "sonido",
        "archivo": "risa.wav",
        "duracion": 3,
    }
    datos.update(cambios)
    return datos


class TestVolumen(unittest.TestCase):

    def setUp(self):
        app_de_prueba()

    def _cuadro(self, **cambios):
        cuadro = medio_cuadro.DialogoMedio(None, _datos(**cambios))
        self.addCleanup(destruir, cuadro)
        return cuadro

    def test_el_deslizador_va_de_cero_a_doscientos_y_nace_en_cien(self):
        for tipo, archivo in (("sonido", "risa.wav"), ("video", "risa.mp4")):
            with self.subTest(tipo=tipo):
                cuadro = self._cuadro(tipo=tipo, archivo=archivo)
                self.assertIsInstance(cuadro.sp_volumen, wx.Slider)
                self.assertEqual((cuadro.sp_volumen.GetMin(),
                                  cuadro.sp_volumen.GetMax(),
                                  cuadro.sp_volumen.GetValue()), (0, 200, 100))
                self.assertEqual(cuadro.sp_volumen.GetLineSize(), 1)
                self.assertEqual(cuadro.sp_volumen.GetName(), "Volumen")
                self.assertEqual(letras_repetidas(cuadro), {})

    def test_el_rotulo_va_tras_la_duracion_y_antes_de_la_nota_y_el_pie(self):
        cuadro = self._cuadro(duracion=20)
        hermanos = cuadro.txt_duracion.GetParent().GetChildren()
        posicion = hermanos.index(cuadro.sp_volumen)
        rotulo = hermanos[posicion - 1]
        self.assertIsInstance(rotulo, wx.StaticText)
        self.assertEqual(rotulo.GetLabel(), "&Volumen:")
        self.assertLess(hermanos.index(cuadro.txt_duracion), posicion)
        self.assertLess(posicion, hermanos.index(cuadro.aviso))
        self.assertLess(posicion, hermanos.index(cuadro.btn_aceptar))
        etiquetas = [hijo.GetLabel() for hijo in hermanos
                     if isinstance(hijo, wx.StaticText)]
        self.assertIn("&Volumen:", etiquetas)

    def test_el_volumen_elegido_vuelve_en_los_datos(self):
        cuadro = self._cuadro(volumen=50)
        self.assertEqual(cuadro.sp_volumen.GetValue(), 50)
        cuadro.sp_volumen.SetValue(150)
        self.assertEqual(cuadro.datos()["volumen"], 150)
        self.assertEqual(cuadro.datos()["nombre"], "Risa")

    def test_imagen_y_gif_no_tienen_deslizador(self):
        for archivo in ("logo.png", "baile.gif"):
            with self.subTest(archivo=archivo):
                cuadro = self._cuadro(tipo="imagen", archivo=archivo,
                                      duracion=0)
                self.assertIsNone(cuadro.sp_volumen)
                hermanos = cuadro.txt_duracion.GetParent().GetChildren()
                self.assertFalse([hijo for hijo in hermanos
                                  if isinstance(hijo, wx.Slider)])
                self.assertEqual(cuadro.datos()["volumen"], 100)


if __name__ == "__main__":
    unittest.main()
