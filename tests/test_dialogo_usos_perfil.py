# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas del cuadro que asigna los tres usos de un perfil de OBS."""

import unittest
from unittest import mock

import wx

from tests.ventanas_prueba import app_de_prueba, destruir
from guyrapu.ui import formulario, tema
from guyrapu.ui.dialogo_usos_perfil import DialogoUsosPerfil


class BaseDialogo(unittest.TestCase):

    def setUp(self):
        self.app = app_de_prueba()
        self.config = {"perfil_horizontal": "Uno",
                       "perfil_vertical": "Otro",
                       "perfil_grabar": ""}

    def _dialogo(self):
        dialogo = DialogoUsosPerfil(None, "Uno", self.config)
        self.addCleanup(destruir, dialogo)
        return dialogo


class TestCasillas(BaseDialogo):

    def test_titulo(self):
        self.assertEqual(self._dialogo().GetTitle(), "Usar Uno para")

    def test_marcadas_segun_lo_asignado(self):
        dialogo = self._dialogo()
        self.assertTrue(dialogo.casillas["perfil_horizontal"].GetValue())
        self.assertFalse(dialogo.casillas["perfil_vertical"].GetValue())
        self.assertFalse(dialogo.casillas["perfil_grabar"].GetValue())

    def test_la_casilla_de_otro_perfil_dice_cual(self):
        dialogo = self._dialogo()
        vertical = dialogo.casillas["perfil_vertical"]
        self.assertEqual(
            vertical.GetName(), "Transmitir en vertical (ahora: Otro)")
        self.assertIn("ahora: Otro", vertical.GetLabel())

    def test_nombres_accesibles_sin_la_letra_de_acceso(self):
        dialogo = self._dialogo()
        self.assertEqual(
            dialogo.casillas["perfil_horizontal"].GetName(),
            "Transmitir en horizontal")
        self.assertEqual(dialogo.casillas["perfil_grabar"].GetName(), "Grabar")

    def test_el_foco_empieza_en_la_primera(self):
        dialogo = self._dialogo()
        self.assertIs(wx.Window.FindFocus(),
                      dialogo.casillas["perfil_horizontal"])

    def test_inicial_marcados_reflejan_lo_asignado(self):
        dialogo = self._dialogo()
        self.assertEqual(
            dialogo.marcados(),
            {"perfil_horizontal": True, "perfil_vertical": False,
             "perfil_grabar": False})


class TestEscape(BaseDialogo):

    def test_escape_cancela(self):
        dialogo = self._dialogo()
        evento = mock.Mock()
        evento.GetKeyCode.return_value = wx.WXK_ESCAPE
        with mock.patch.object(dialogo, "EndModal") as fin:
            dialogo._al_tecla(evento)
        fin.assert_called_once_with(wx.ID_CANCEL)


class TestGeometria(BaseDialogo):

    def test_el_cuadro_usa_las_medidas_comunes(self):
        dialogo = self._dialogo()
        dialogo.Show()
        wx.Yield()
        ancho, alto = dialogo.GetClientSize()
        self.assertGreaterEqual(ancho, formulario.ANCHO_MINIMO,
                                f"tamaño {ancho} x {alto}")
        self.assertLessEqual(alto, formulario.ALTO_MAXIMO,
                             f"tamaño {ancho} x {alto}")
        self.assertEqual(dialogo.btn_aceptar.GetSize().width,
                         dialogo.btn_cancelar.GetSize().width)
        self.assertEqual(dialogo.btn_cancelar.GetPosition().x - (
            dialogo.btn_aceptar.GetPosition().x
            + dialogo.btn_aceptar.GetSize().width),
            formulario.ENTRE_BOTONES)
        panel = dialogo.btn_aceptar.GetParent()
        self.assertEqual(panel.GetClientSize().width - (
            dialogo.btn_cancelar.GetPosition().x
            + dialogo.btn_cancelar.GetSize().width), formulario.MARGEN)
        self.assertGreater(dialogo.btn_aceptar.GetPosition().y,
                           next(iter(dialogo.casillas.values())
                                ).GetPosition().y)
        if not tema.ALTO_CONTRASTE:
            self.assertEqual(dialogo.btn_aceptar.GetBackgroundColour(),
                             tema._T.primary)


if __name__ == "__main__":
    unittest.main()
