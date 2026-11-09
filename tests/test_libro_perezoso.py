# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Libro de wx que construye sus páginas recién al elegirlas."""

import unittest

import wx

from guyrapu.ui.libro_perezoso import LibroPerezoso
from tests.ventanas_prueba import app_de_prueba, destruir


class TestLibroPerezoso(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = app_de_prueba()
        cls.frame = wx.Frame(None)

    @classmethod
    def tearDownClass(cls):
        destruir(cls.frame)
        del cls.frame
        del cls.app

    def _libro(self):
        libro = wx.Listbook(self.frame)
        self.addCleanup(destruir, libro)
        return libro

    def _entradas(self, llamadas, creados=None):
        def fabrica(indice):
            def armar(parent):
                llamadas[indice] += 1
                panel = wx.Panel(parent, name=f"Pag{indice}")
                panel.SetSizer(wx.BoxSizer(wx.VERTICAL))
                wx.StaticText(panel, label=f"Contenido {indice}")
                if creados is not None:
                    creados[indice] = panel
                return panel
            return armar
        return [(f"Categoría {i}", fabrica(i)) for i in range(3)]

    def _titulos(self, libro):
        return [libro.GetPageText(i) for i in range(libro.GetPageCount())]

    def test_sin_pereza_construye_todas_al_crear(self):
        libro = self._libro()
        llamadas = [0, 0, 0]
        creados = {}
        LibroPerezoso(libro, self._entradas(llamadas, creados), False)
        self.assertEqual(llamadas, [1, 1, 1])
        self.assertEqual(self._titulos(libro),
                         ["Categoría 0", "Categoría 1", "Categoría 2"])
        for indice in range(3):
            self.assertIs(libro.GetPage(indice), creados[indice])

    def test_con_pereza_solo_construye_la_elegida(self):
        libro = self._libro()
        llamadas = [0, 0, 0]
        creados = {}
        libro_perezoso = LibroPerezoso(
            libro, self._entradas(llamadas, creados), True)
        self.assertEqual(llamadas, [1, 0, 0])
        self.assertTrue(libro_perezoso.construida(0))
        self.assertFalse(libro_perezoso.construida(1))
        self.assertIsNot(libro.GetPage(0), creados[0])
        self.assertIs(libro.GetPage(0).GetSizer().GetItem(0).GetWindow(),
                      creados[0])

        libro.SetSelection(1)
        self.assertEqual(llamadas, [1, 1, 0])
        self.assertTrue(libro_perezoso.construida(1))
        self.assertIs(libro.GetPage(1).GetSizer().GetItem(0).GetWindow(),
                      creados[1])

        libro.SetSelection(2)
        libro.SetSelection(1)
        self.assertEqual(llamadas, [1, 1, 1])

    def test_construir_dos_veces_no_repite_la_pagina(self):
        libro = self._libro()
        llamadas = [0, 0, 0]
        libro_perezoso = LibroPerezoso(libro, self._entradas(llamadas), True)
        libro_perezoso.construir(1)
        libro_perezoso.construir(1)
        self.assertEqual(llamadas[1], 1)

    def test_los_titulos_y_el_orden_no_cambian_con_pereza(self):
        sin_pereza = self._libro()
        con_pereza = self._libro()
        LibroPerezoso(sin_pereza, self._entradas([0, 0, 0]), False)
        LibroPerezoso(con_pereza, self._entradas([0, 0, 0]), True)
        self.assertEqual(self._titulos(sin_pereza), self._titulos(con_pereza))


if __name__ == "__main__":
    unittest.main()
