# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Cuadro Filtros del micrófono: abre con el estado y devuelve lo elegido.

Abre ventanas: se corre en la PC de pruebas, no en la del dueño.
"""

import unittest
from unittest import mock

import wx

from guyrapu.obs.filtros_microfono import Estado
from guyrapu.ui import escena_filtros, formulario, tema
from tests.ventanas_prueba import app_de_prueba, destruir


class TestEscenaFiltros(unittest.TestCase):

    def setUp(self):
        self.app = app_de_prueba()
        self.dialogo = escena_filtros.FiltrosMicrofonoDialog(
            None, "Mic/Aux", Estado(True, False, 6))
        self.addCleanup(destruir, self.dialogo)

    def test_abre_con_el_estado_recibido(self):
        self.assertEqual(self.dialogo.GetTitle(),
                         "Filtros del micrófono: Mic/Aux")
        self.assertTrue(self.dialogo.chk_ruido.GetValue())
        self.assertFalse(self.dialogo.chk_puerta.GetValue())
        self.assertEqual(self.dialogo.cho_ganancia.GetStringSelection(),
                         "Subir 6 dB")
        self.assertIs(self.dialogo.GetDefaultItem(),
                      self.dialogo.btn_aceptar)

    def test_devuelve_lo_marcado(self):
        self.dialogo.chk_puerta.SetValue(True)
        self.dialogo.cho_ganancia.SetStringSelection("Bajar 3 dB")
        self.dialogo.EndModal = mock.Mock()
        self.dialogo._al_aceptar(None)
        self.dialogo.EndModal.assert_called_once_with(wx.ID_OK)
        self.assertEqual(self.dialogo.estado_elegido(),
                         Estado(True, True, -3))

    def test_cancelar_no_devuelve_estado(self):
        self.dialogo.EndModal = mock.Mock()
        self.dialogo._al_cancelar(None)
        self.dialogo.EndModal.assert_called_once_with(wx.ID_CANCEL)
        self.assertIsNone(self.dialogo.estado_elegido())

    def test_escape_cancela_sin_estado(self):
        self.dialogo.EndModal = mock.Mock()
        evento = wx.KeyEvent(wx.wxEVT_CHAR_HOOK)
        evento.KeyCode = wx.WXK_ESCAPE
        self.dialogo.ProcessEvent(evento)
        self.dialogo.EndModal.assert_called_once_with(wx.ID_CANCEL)
        self.assertIsNone(self.dialogo.estado_elegido())

    def test_geometria_del_cuadro(self):
        self.dialogo.Layout()
        ancho, alto = self.dialogo.GetSize()
        mensaje = f"Tamaño {ancho} x {alto}"
        self.assertGreaterEqual(ancho, formulario.ANCHO_MINIMO, mensaje)
        self.assertLessEqual(alto, formulario.ALTO_MAXIMO, mensaje)
        rotulo = self.dialogo.rotulo_ganancia
        control = self.dialogo.cho_ganancia
        self.assertLessEqual(
            rotulo.GetPosition().y + rotulo.GetSize().height,
            control.GetPosition().y)
        botones = [self.dialogo.btn_aceptar, self.dialogo.btn_cancelar]
        self.assertEqual(botones[0].GetSize().width,
                         botones[1].GetSize().width)
        panel = botones[-1].GetParent()
        self.assertEqual(
            panel.GetClientSize().width - botones[-1].GetPosition().x
            - botones[-1].GetSize().width, formulario.MARGEN)
        self.assertEqual(
            panel.GetClientSize().height - botones[-1].GetPosition().y
            - botones[-1].GetSize().height, formulario.MARGEN)
        self.assertGreaterEqual(
            botones[-1].GetPosition().y,
            control.GetPosition().y + control.GetSize().height)
        if not tema.ALTO_CONTRASTE:
            self.assertEqual(self.dialogo.btn_aceptar.GetBackgroundColour(),
                             tema._T.primary)


if __name__ == "__main__":
    unittest.main()
