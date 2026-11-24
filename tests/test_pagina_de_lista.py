# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""El armado común de las páginas de lista de Interacción.

Abre controles de wx.
"""

import unittest

import wx

from guyrapu.ui import pagina_de_lista
from tests.ventanas_prueba import app_de_prueba, destruir


class PaginaDeListaTest(unittest.TestCase):
    """Los bordes y proporciones de hoy, medidos en el sizer armado."""

    def setUp(self):
        app_de_prueba()
        self.marco = wx.Frame(None)
        self.addCleanup(destruir, self.marco)

    def _armar(self, **cambios):
        sizer = wx.BoxSizer(wx.VERTICAL)
        rotulo = wx.StaticText(self.marco, label="Lista:")
        lista = wx.ListBox(self.marco)
        fila = wx.BoxSizer(wx.HORIZONTAL)
        fila.Add(wx.Button(self.marco, label="Agregar"), 0)
        pagina_de_lista.agregar_lista(sizer, rotulo, lista, **cambios)
        pagina_de_lista.agregar_botones(sizer, fila)
        return sizer, rotulo, lista, fila

    def test_cada_control_va_con_sus_bordes_y_proporcion_de_hoy(self):
        sizer, rotulo, lista, fila = self._armar()
        items = sizer.GetChildren()
        self.assertEqual(len(items), 3)
        self.assertIs(items[0].GetWindow(), rotulo)
        self.assertIs(items[1].GetWindow(), lista)
        self.assertIs(items[2].GetSizer(), fila)
        self.assertEqual(
            (items[0].GetProportion(), items[0].GetFlag(),
             items[0].GetBorder()),
            (0, wx.LEFT | wx.RIGHT | wx.TOP, 10))
        self.assertEqual(
            (items[1].GetProportion(), items[1].GetFlag(),
             items[1].GetBorder()),
            (1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10))
        self.assertEqual(
            (items[2].GetProportion(), items[2].GetFlag(),
             items[2].GetBorder()),
            (0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10))

    def test_el_rotulo_puede_irse_sin_borde_superior(self):
        sizer, _rotulo, _lista, _fila = self._armar(borde_superior=False)
        items = sizer.GetChildren()
        self.assertEqual(
            (items[0].GetFlag(), items[0].GetBorder()),
            (wx.LEFT | wx.RIGHT, 10))
        self.assertEqual(items[1].GetFlag(),
                         wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM)


if __name__ == "__main__":
    unittest.main()
