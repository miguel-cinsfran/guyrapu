# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Cuadro de tipos de un estilo predeterminado: casillas, foco y Escape.

Abre ventanas.
"""

import unittest
from unittest import mock

import wx

from guyrapu.ui import estilo_tipos_cuadro
from tests.ventanas_prueba import app_de_prueba, destruir


class TestCuadro(unittest.TestCase):

    def setUp(self):
        self.app = app_de_prueba()

    def _cuadro(self, marcados=()):
        cuadro = estilo_tipos_cuadro.DialogoTipos(None, set(marcados))
        self.addCleanup(destruir, cuadro)
        return cuadro

    def test_tiene_las_cuatro_casillas_en_su_orden(self):
        cuadro = self._cuadro()
        self.assertEqual(
            [casilla.GetLabel() for casilla in cuadro._casillas.values()],
            ["Mensajes automáticos", "Comandos", "Disparadores", "Encuestas"])

    def test_cada_casilla_tiene_su_rotulo_como_nombre_accesible(self):
        cuadro = self._cuadro()
        for casilla in cuadro._casillas.values():
            self.assertEqual(casilla.GetName(), casilla.GetLabel())

    def test_abre_marcadas_las_que_ya_usan_el_estilo(self):
        cuadro = self._cuadro({"comando", "encuesta"})
        marcadas = {tipo for tipo, casilla in cuadro._casillas.items()
                    if casilla.GetValue()}
        self.assertEqual(marcadas, {"comando", "encuesta"})

    def test_marcados_devuelve_lo_que_quedo_marcado(self):
        cuadro = self._cuadro()
        self.assertEqual(cuadro.marcados(), set())
        cuadro._casillas["disparador"].SetValue(True)
        self.assertEqual(cuadro.marcados(), {"disparador"})

    def test_al_abrir_el_foco_queda_en_la_primera_casilla(self):
        cuadro = self._cuadro()
        cuadro.Show()
        try:
            self.assertIs(wx.Window.FindFocus(),
                          cuadro._casillas["mensaje"])
        finally:
            cuadro.Hide()

    def test_escape_cancela(self):
        evento = mock.Mock()
        evento.GetKeyCode.return_value = wx.WXK_ESCAPE
        cuadro = self._cuadro()
        with mock.patch.object(cuadro, "EndModal") as cerrar:
            cuadro._al_tecla(evento)
        cerrar.assert_called_once_with(wx.ID_CANCEL)

    def test_aceptar_cierra_con_ok(self):
        cuadro = self._cuadro()
        with mock.patch.object(cuadro, "EndModal") as cerrar:
            cuadro._aceptar(None)
        cerrar.assert_called_once_with(wx.ID_OK)


if __name__ == "__main__":
    unittest.main()
