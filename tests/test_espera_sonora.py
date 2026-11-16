# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de la pieza de sonido de una espera pedida. Abren ventanas con wx."""

import unittest
from unittest import mock

try:
    import wx
    _HAY_WX = True
except Exception:
    _HAY_WX = False

from guyrapu.ui import espera_sonora
from guyrapu.ui.espera_sonora import EsperaSonora
from tests.ventanas_prueba import app_de_prueba, destruir


class _Evento:
    def __init__(self):
        self.saltado = False

    def Skip(self):
        self.saltado = True


@unittest.skipUnless(_HAY_WX, "wxPython no está instalado")
class TestEsperaSonora(unittest.TestCase):

    def setUp(self):
        self.app = app_de_prueba()

    def _espera(self):
        ventana = wx.Frame(None)
        self.addCleanup(destruir, ventana)
        return EsperaSonora(ventana)

    def test_empezar_no_suena_y_un_tic_suena_espera(self):
        espera = self._espera()
        with mock.patch.object(
                espera_sonora.sound_player, "reproducir") as sonar:
            espera.empezar()
            self.assertTrue(espera._timer.IsRunning())
            sonar.assert_not_called()
            espera._al_tiempo(None)
        sonar.assert_called_once_with("espera")

    def test_terminar_listo_suena_solo_si_hubo_un_tic(self):
        espera = self._espera()
        with mock.patch.object(
                espera_sonora.sound_player, "reproducir") as sonar:
            espera.empezar()
            espera.terminar("listo")
        sonar.assert_not_called()

        with mock.patch.object(
                espera_sonora.sound_player, "reproducir") as sonar:
            espera.empezar()
            espera._al_tiempo(None)
            espera.terminar("listo")
        self.assertIn(mock.call("listo"), sonar.call_args_list)

    def test_terminar_error_suena_aunque_no_haya_tic(self):
        espera = self._espera()
        with mock.patch.object(
                espera_sonora.sound_player, "reproducir") as sonar:
            espera.empezar()
            espera.terminar("error")
        sonar.assert_called_once_with("error")

    def test_terminar_none_y_detener_no_suenan(self):
        espera = self._espera()
        with mock.patch.object(
                espera_sonora.sound_player, "reproducir") as sonar:
            espera.empezar()
            espera._al_tiempo(None)
            sonar.reset_mock()
            espera.terminar(None)
            self.assertFalse(espera._timer.IsRunning())
            espera.empezar()
            espera.detener()
            self.assertFalse(espera._timer.IsRunning())
        sonar.assert_not_called()

    def test_detener_y_destruir_no_dejan_sonar_el_final(self):
        espera = self._espera()
        evento = _Evento()
        with mock.patch.object(
                espera_sonora.sound_player, "reproducir") as sonar:
            espera.empezar()
            espera._al_tiempo(None)
            sonar.reset_mock()
            espera.detener()
            espera.terminar("error")
            sonar.assert_not_called()

            espera.empezar()
            espera._al_tiempo(None)
            sonar.reset_mock()
            espera._al_destruir(evento)
            espera.terminar("listo")
        self.assertTrue(evento.saltado)
        sonar.assert_not_called()

    def test_empezar_de_nuevo_vuelve_a_contar_desde_cero(self):
        espera = self._espera()
        with mock.patch.object(
                espera_sonora.sound_player, "reproducir") as sonar:
            espera.empezar()
            espera._al_tiempo(None)
            sonar.reset_mock()
            espera.empezar()
            espera.terminar("listo")
        sonar.assert_not_called()


if __name__ == "__main__":
    unittest.main()
