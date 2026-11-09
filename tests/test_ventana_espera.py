# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de la ventana de espera común. Abren ventanas con wx."""

import threading
import unittest
from unittest import mock

import wx

from guyrapu.core.idioma import _
from guyrapu.ui import ventana_espera
from guyrapu.ui.ventana_espera import VentanaEspera
from tests.ventanas_prueba import app_de_prueba, destruir

TITULO = "Probando la conexión"


class _Evento:
    def __init__(self):
        self.saltado = False

    def Skip(self):
        self.saltado = True


class TestVentanaEspera(unittest.TestCase):

    def setUp(self):
        self.app = app_de_prueba()

    def _abrir(self, parada=None):
        cuadro = VentanaEspera(None, _(TITULO), "", parada)
        self.addCleanup(destruir, cuadro)
        cuadro.Show()
        wx.Yield()
        return cuadro

    def test_el_estado_se_escribe_y_se_anuncia_una_vez(self):
        cuadro = self._abrir(threading.Event())
        with mock.patch.object(ventana_espera, "anunciar") as anunciar:
            cuadro.estado("Probando a 2500 kbps…")
        self.assertEqual(cuadro.txt_estado.GetValue(),
                         "Probando a 2500 kbps…")
        anunciar.assert_called_once_with("Probando a 2500 kbps…")

    def test_el_campo_lleva_el_titulo_es_solo_lectura_y_recibe_el_foco(self):
        cuadro = self._abrir(threading.Event())
        self.assertEqual(cuadro.txt_estado.GetName(), _(TITULO))
        estilo = cuadro.txt_estado.GetWindowStyle()
        self.assertTrue(estilo & wx.TE_READONLY)
        self.assertTrue(estilo & wx.TE_MULTILINE)
        self.assertIs(wx.Window.FindFocus(), cuadro.txt_estado)
        self.assertLess(cuadro.txt_estado.GetPosition().y,
                        cuadro._btn.GetPosition().y)

    def test_sin_parada_no_hay_cancelar(self):
        cuadro = self._abrir()
        self.assertIsNone(cuadro._btn)

    def test_cancelar_marca_la_parada_sigue_habilitado_y_avisa(self):
        parada = threading.Event()
        cuadro = self._abrir(parada)
        with mock.patch.object(ventana_espera, "anunciar") as anunciar:
            cuadro._cancelar()
            cuadro._cancelar()
        self.assertTrue(parada.is_set())
        self.assertTrue(cuadro._timer.IsRunning())
        self.assertTrue(cuadro._btn.IsEnabled())
        self.assertEqual(cuadro.txt_estado.GetValue(), _("Cancelando…"))
        anunciar.assert_called_once_with(_("Cancelando…"))

    def test_terminar_escribe_cambia_a_cerrar_para_el_timer_y_enfoca(self):
        cuadro = self._abrir(threading.Event())
        with mock.patch.object(ventana_espera, "anunciar") as anunciar:
            cuadro.terminar("La prueba terminó.")
        self.assertEqual(cuadro.txt_estado.GetValue(), "La prueba terminó.")
        anunciar.assert_called_once_with("La prueba terminó.")
        self.assertEqual(cuadro._btn.GetLabel(), _("&Cerrar"))
        self.assertEqual(cuadro._btn.GetName(), _("Cerrar"))
        self.assertFalse(cuadro._timer.IsRunning())
        self.assertIs(wx.Window.FindFocus(), cuadro._btn)

    def test_terminar_con_error_reproduce_el_sonido_de_error(self):
        cuadro = self._abrir(threading.Event())
        with mock.patch.object(
                ventana_espera.sound_player, "reproducir") as sonar:
            cuadro.terminar("Falló.", error=True)
        sonar.assert_called_once_with("error")

    def test_el_temporizador_reproduce_espera(self):
        cuadro = self._abrir(threading.Event())
        self.assertTrue(cuadro._timer.IsRunning())
        with mock.patch.object(
                ventana_espera.sound_player, "reproducir") as sonar:
            cuadro._al_tiempo(None)
        sonar.assert_called_once_with("espera")

    def test_cerrar_la_ventana_detiene_el_timer(self):
        cuadro = self._abrir(threading.Event())
        evento = _Evento()
        cuadro._al_cerrar(evento)
        self.assertFalse(cuadro._timer.IsRunning())
        self.assertTrue(evento.saltado)


if __name__ == "__main__":
    unittest.main()
