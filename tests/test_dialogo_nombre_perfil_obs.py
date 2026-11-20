# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas del cuadro del nombre de un perfil de OBS. Abre ventanas con wx."""

import unittest

import wx

from guyrapu.ui import formulario, tema
from guyrapu.ui.dialogo_nombre_perfil_obs import DialogoNombrePerfil
from tests.ventanas_prueba import app_de_prueba, destruir


class TestGeometria(unittest.TestCase):

    def setUp(self):
        self.app = app_de_prueba()

    def test_el_cuadro_usa_las_medidas_comunes(self):
        cuadro = DialogoNombrePerfil(
            None, existentes=(), con_orientacion=True, accion="C&rear")
        self.addCleanup(destruir, cuadro)
        cuadro.Show()
        wx.Yield()
        ancho, alto = cuadro.GetClientSize()
        self.assertGreaterEqual(ancho, formulario.ANCHO_MINIMO,
                                f"tamaño {ancho} x {alto}")
        self.assertLessEqual(alto, formulario.ALTO_MAXIMO,
                             f"tamaño {ancho} x {alto}")
        panel = cuadro.txt_nombre.GetParent()
        hermanos = panel.GetChildren()
        rotulo = hermanos[hermanos.index(cuadro.txt_nombre) - 1]
        self.assertIsInstance(rotulo, wx.StaticText,
                              f"tamaño {ancho} x {alto}")
        self.assertLess(rotulo.GetPosition().y + rotulo.GetSize().height,
                        cuadro.txt_nombre.GetPosition().y)
        self.assertEqual(cuadro.btn_aceptar.GetSize().width,
                         cuadro.btn_cancelar.GetSize().width)
        self.assertEqual(cuadro.btn_cancelar.GetPosition().x - (
            cuadro.btn_aceptar.GetPosition().x
            + cuadro.btn_aceptar.GetSize().width),
            formulario.ENTRE_BOTONES)
        self.assertEqual(panel.GetClientSize().width - (
            cuadro.btn_cancelar.GetPosition().x
            + cuadro.btn_cancelar.GetSize().width), formulario.MARGEN)
        if not tema.ALTO_CONTRASTE:
            self.assertEqual(cuadro.btn_aceptar.GetBackgroundColour(),
                             tema._T.primary)


if __name__ == "__main__":
    unittest.main()
