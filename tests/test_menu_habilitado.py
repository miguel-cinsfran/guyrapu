# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de cómo se prende y apaga un elemento de menú."""

import unittest
from unittest import mock

import wx

from guyrapu.ui import menu_habilitado
from tests.ventanas_prueba import app_de_prueba


class TestHabilitarConMenuItemReal(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = app_de_prueba()

    @classmethod
    def tearDownClass(cls):
        del cls.app

    def setUp(self):
        self.menu = wx.Menu()
        self.addCleanup(self.menu.Destroy)

    def _item(self):
        item = self.menu.Append(wx.ID_ANY, "&Conectar")
        item.Enable(True)
        return item

    def test_habilitar_deja_el_elemento_en_el_estado_pedido(self):
        item = self._item()
        menu_habilitado.habilitar(item, False)
        self.assertFalse(item.IsEnabled())
        menu_habilitado.habilitar(item, True)
        self.assertTrue(item.IsEnabled())

    def test_habilitar_varios_deja_cada_elemento_en_el_estado_pedido(self):
        items = [self._item() for _ in range(3)]
        menu_habilitado.habilitar_varios(items, False)
        self.assertEqual([False, False, False],
                         [item.IsEnabled() for item in items])
        menu_habilitado.habilitar_varios(items, True)
        self.assertEqual([True, True, True],
                         [item.IsEnabled() for item in items])

    def test_un_elemento_destruido_no_rompe_y_queda_en_el_registro(self):
        item = mock.Mock()
        item.Enable.side_effect = RuntimeError("elemento destruido")
        with self.assertLogs(menu_habilitado.logger, level="DEBUG"):
            menu_habilitado.habilitar(item, False)


if __name__ == "__main__":
    unittest.main()
