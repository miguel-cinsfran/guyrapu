# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas del envoltorio de `wx.ListCtrl` de la pieza de listas."""

import unittest

import wx

from tests.ventanas_prueba import app_de_prueba, destruir
from guyrapu.ui.lista_ctrl import ListaCtrlEnvuelta


class PruebaSelecciones(unittest.TestCase):

    def setUp(self):
        self.app = app_de_prueba()
        self.marco = wx.Frame(None)
        self.addCleanup(destruir, self.marco)
        self.control = wx.ListCtrl(self.marco, style=wx.LC_REPORT)
        self.control.InsertColumn(0, "Nombre", width=150)
        self.lista = ListaCtrlEnvuelta(self.control)
        for texto in ("a", "b", "c", "d", "e"):
            self.lista.Append(texto)

    def test_p4_get_selections_da_todas_las_elegidas_en_orden(self):
        self.assertEqual(self.lista.GetSelections(), [])
        for indice in (4, 0, 2):
            self.control.Select(indice)
        self.assertEqual(self.lista.GetSelections(), [0, 2, 4])
        self.control.Select(2, False)
        self.assertEqual(self.lista.GetSelections(), [0, 4])

    def test_p4_una_sola_elegida_y_ninguna(self):
        self.control.Select(3)
        self.assertEqual(self.lista.GetSelections(), [3])
        self.control.Select(3, False)
        self.assertEqual(self.lista.GetSelections(), [])


if __name__ == "__main__":
    unittest.main()
