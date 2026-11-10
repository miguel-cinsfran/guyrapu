# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de la pieza común que reconoce y atiende Escape."""

import unittest
from unittest import mock

import wx

from guyrapu.ui import tecla_escape


class TestEsEscape(unittest.TestCase):

    def test_escape_es_escape(self):
        self.assertTrue(tecla_escape.es_escape(wx.WXK_ESCAPE))

    def test_otra_tecla_no_es_escape(self):
        self.assertFalse(tecla_escape.es_escape(wx.WXK_F11))


class TestCancelarSiEscape(unittest.TestCase):

    def test_escape_cierra_con_cancelar_sin_pasar_la_tecla(self):
        dialogo = mock.Mock()
        evento = mock.Mock()
        evento.GetKeyCode.return_value = wx.WXK_ESCAPE
        tecla_escape.cancelar_si_escape(dialogo, evento)
        dialogo.EndModal.assert_called_once_with(wx.ID_CANCEL)
        evento.Skip.assert_not_called()

    def test_otra_tecla_pasa_sin_cerrar(self):
        dialogo = mock.Mock()
        evento = mock.Mock()
        evento.GetKeyCode.return_value = wx.WXK_RETURN
        tecla_escape.cancelar_si_escape(dialogo, evento)
        dialogo.EndModal.assert_not_called()
        evento.Skip.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
