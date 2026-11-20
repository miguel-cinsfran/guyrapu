# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pieza común de los deslizadores accesibles de la app.

Abre ventanas.
"""

import unittest
from unittest import mock

import wx

from guyrapu.ui.deslizador import deslizador_accesible
from tests.ventanas_prueba import app_de_prueba, destruir


class TestDeslizador(unittest.TestCase):
    def setUp(self):
        self.app = app_de_prueba()
        self.ventana = wx.Dialog(None, name="PruebaDeslizador")
        self.addCleanup(destruir, self.ventana)

    def test_arma_un_deslizador_con_rango_valor_paso_y_nombre(self):
        with mock.patch("guyrapu.ui.deslizador.nombre_accesible") as poner:
            control = deslizador_accesible(
                self.ventana, minimo=0, maximo=100, inicial=40, paso=5,
                nombre="Velocidad de la voz")

        self.assertIsInstance(control, wx.Slider)
        self.assertTrue(control.GetWindowStyle() & wx.SL_HORIZONTAL)
        self.assertEqual((control.GetMin(), control.GetMax(),
                          control.GetValue()), (0, 100, 40))
        self.assertEqual(control.GetLineSize(), 5)
        poner.assert_called_once_with(control, "Velocidad de la voz")


if __name__ == "__main__":
    unittest.main()
