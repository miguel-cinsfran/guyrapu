# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pieza común de los deslizadores accesibles de la app.

Abre ventanas.
"""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import wx

from guyrapu.ui import gui_preferencias
from guyrapu.ui.deslizador import deslizador_accesible
from guyrapu.voice import motores
from tests.rutas_temporales import redirigir_rutas
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

    def test_mide_al_menos_como_el_cuadro_de_salida_de_audio(self):
        control = deslizador_accesible(
            self.ventana, minimo=0, maximo=100, inicial=40, paso=5,
            nombre="Volumen de la voz")

        self.assertGreaterEqual(control.GetMinSize().GetWidth(), 280)

    def test_muestra_el_valor_junto_al_cursor(self):
        control = deslizador_accesible(
            self.ventana, minimo=0, maximo=100, inicial=40, paso=5,
            nombre="Volumen de la música")

        self.assertTrue(control.GetWindowStyle() & wx.SL_VALUE_LABEL)


class TestNivelesDePreferencias(unittest.TestCase):
    def setUp(self):
        self.app = app_de_prueba()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        parche = redirigir_rutas(Path(self.tmp.name))
        parche.__enter__()
        self.addCleanup(parche.__exit__, None, None, None)
        with mock.patch.object(motores, "listar_voces",
                               return_value=["Voz de prueba"]):
            self.dialogo = gui_preferencias.PreferenciasDialog(None, {})
        self.addCleanup(destruir, self.dialogo)

    def test_ningun_nivel_de_voz_o_musica_es_un_contador(self):
        contadores = []
        for pagina in self.dialogo._paginas():
            for control in pagina.GetChildren():
                if (control.GetName().startswith(
                        ("Velocidad", "Volumen", "Tono"))
                        and isinstance(control, wx.SpinCtrl)):
                    contadores.append(control.GetName())
        self.assertEqual([], contadores)


if __name__ == "__main__":
    unittest.main()
