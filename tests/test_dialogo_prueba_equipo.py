# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de los cuadros de la prueba del equipo. Abren ventanas."""

import threading
import unittest
from dataclasses import replace
from unittest import mock

import wx

from guyrapu.obs import ajustes_perfil, obs_cliente, prueba_equipo
from guyrapu.ui import dialogo_prueba_equipo
from tests.ventanas_prueba import app_de_prueba, destruir


def _ajustes():
    return ajustes_perfil.AjustesPerfil(
        ancho_lienzo=1920, alto_lienzo=1080,
        ancho_salida=1920, alto_salida=1080,
        fps=60, codificador="x264", preset="veryfast")


def _resultado(aguantaron, pasos=None):
    original = _ajustes()
    if pasos is None:
        pasos = (prueba_equipo.PasoEquipo(original, 1, 100, 1, 100),)
    return prueba_equipo.ResultadoEquipo(
        "Casa", original, aguantaron, pasos)


class BaseCuadro(unittest.TestCase):

    def setUp(self):
        self.app = app_de_prueba()

    def _mostrar(self, cuadro):
        self.addCleanup(destruir, cuadro)
        cuadro.Show()
        wx.Yield()
        return cuadro


class TestDialogoPruebaEquipo(BaseCuadro):

    def test_dice_perfil_ajustes_y_duracion_y_enfoca_empezar(self):
        cuadro = self._mostrar(dialogo_prueba_equipo.DialogoPruebaEquipo(
            None, "Casa", _ajustes(), 48))
        texto = cuadro.texto()
        self.assertIn("Casa", texto)
        self.assertIn("codificador", texto)
        self.assertIn("48 segundos", texto)
        self.assertTrue(cuadro.txt_detalle.GetWindowStyle() & wx.TE_READONLY)
        self.assertTrue(cuadro.btn_empezar.HasFocus())
        self.assertEqual(cuadro.btn_cancelar.GetLabel(), "&Cancelar")

    def test_el_texto_se_alcanza_con_tab_antes_de_los_botones(self):
        cuadro = self._mostrar(dialogo_prueba_equipo.DialogoPruebaEquipo(
            None, "Casa", _ajustes(), 48))
        self.assertLess(cuadro.txt_detalle.GetPosition().y,
                        cuadro.btn_empezar.GetPosition().y)


class TestDialogoProgresoPrueba(BaseCuadro):

    def test_cancelar_corta_la_prueba_y_el_foco_queda_en_cancelar(self):
        parada = threading.Event()
        cuadro = self._mostrar(
            dialogo_prueba_equipo.DialogoProgresoPrueba(None, parada))
        self.assertTrue(cuadro.btn_cancelar.HasFocus())
        cuadro._cancelar(None)
        self.assertTrue(parada.is_set())
        self.assertFalse(cuadro.btn_cancelar.IsEnabled())

    def test_cada_escalon_se_muestra_y_se_anuncia(self):
        parada = threading.Event()
        cuadro = self._mostrar(
            dialogo_prueba_equipo.DialogoProgresoPrueba(None, parada))
        with mock.patch.object(
                dialogo_prueba_equipo, "anunciar") as anunciar:
            cuadro.mostrar_paso(_ajustes())
        self.assertIn("Probando", cuadro.txt_estado.GetValue())
        self.assertIn("codificador", cuadro.txt_estado.GetValue())
        anunciar.assert_called_once_with(cuadro.txt_estado.GetValue())


class TestDialogoResultadoPrueba(BaseCuadro):

    def test_si_aguanta_tal_cual_lo_dice_y_solo_cierra(self):
        resultado = _resultado(_ajustes())
        cuadro = self._mostrar(
            dialogo_prueba_equipo.DialogoResultadoPrueba(None, resultado))
        self.assertIn("tal como está", cuadro.texto())
        self.assertFalse(hasattr(cuadro, "btn_guardar"))
        self.assertTrue(hasattr(cuadro, "btn_cerrar"))
        self.assertTrue(cuadro.txt_resultado.HasFocus())

    def test_si_aguanta_con_cambios_dice_cuales_y_ofrece_guardar(self):
        resultado = _resultado(replace(_ajustes(), fps=30,
                                       ancho_salida=1280, alto_salida=720))
        cuadro = self._mostrar(
            dialogo_prueba_equipo.DialogoResultadoPrueba(None, resultado))
        self.assertIn("cambios", cuadro.texto())
        self.assertIn("30", cuadro.texto())
        self.assertTrue(hasattr(cuadro, "btn_guardar"))
        self.assertTrue(hasattr(cuadro, "btn_dejar"))
        self.assertFalse(cuadro.guardar())
        self.assertTrue(cuadro.txt_resultado.HasFocus())

    def test_si_queda_una_grabacion_la_nombra(self):
        original = _ajustes()
        paso = prueba_equipo.PasoEquipo(original, 0, 100, 0, 100)
        resultado = prueba_equipo.ResultadoEquipo(
            "Casa", original, original, (paso,), False,
            ("C:/Vídeos/prueba.mkv",))
        cuadro = self._mostrar(
            dialogo_prueba_equipo.DialogoResultadoPrueba(None, resultado))
        self.assertIn("No se pudo eliminar la grabación", cuadro.texto())
        self.assertIn("C:/Vídeos/prueba.mkv", cuadro.texto())

    def test_si_nada_aguanta_lo_dice_con_los_porcentajes_del_ultimo(self):
        original = _ajustes()
        paso = prueba_equipo.PasoEquipo(original, 10, 100, 20, 100)
        cuadro = self._mostrar(dialogo_prueba_equipo.DialogoResultadoPrueba(
            None, _resultado(None, (paso,))))
        texto = cuadro.texto()
        self.assertIn("Ningún ajuste aguantó", texto)
        self.assertIn("10 %", texto)
        self.assertIn("20 %", texto)
        self.assertTrue(hasattr(cuadro, "btn_cerrar"))


class TestCoordinador(unittest.TestCase):

    def setUp(self):
        self.app = app_de_prueba()
        self.refrescos = []

    def _panel(self, en_hilo=None):
        return dialogo_prueba_equipo.PruebaEquipoPanel(
            None, en_hilo or (lambda _funcion, _terminar: None),
            "cliente", lambda: self.refrescos.append(True),
            lambda _texto: None)

    def test_al_cancelar_anuncia_que_obs_quedo_como_estaba(self):
        resultado = prueba_equipo.ResultadoEquipo(
            "Casa", _ajustes(), None, (), cancelada=True)
        with mock.patch.object(dialogo_prueba_equipo, "anunciar") as anunciar:
            self._panel()._terminada(mock.Mock(), resultado)
        anunciar.assert_called_once_with(
            "Prueba cancelada. OBS quedó como estaba.")
        self.assertTrue(self.refrescos)

    def test_un_fallo_dice_que_obs_quedo_como_estaba(self):
        avisos = []
        panel = dialogo_prueba_equipo.PruebaEquipoPanel(
            None, lambda _funcion, _terminar: None, "cliente",
            lambda: None, avisos.append)
        with mock.patch.object(dialogo_prueba_equipo, "anunciar"):
            panel._terminada(mock.Mock(), obs_cliente.ObsError("sin OBS"))
        self.assertIn("sin OBS", avisos[0])
        self.assertIn("OBS quedó como estaba", avisos[0])

    def test_al_guardar_avisa_y_refresca(self):
        resultado = prueba_equipo.ResultadoEquipo(
            "Casa", _ajustes(), replace(_ajustes(), fps=30),
            (prueba_equipo.PasoEquipo(_ajustes(), 0, 100, 0, 100),))

        def en_hilo(funcion, al_terminar):
            al_terminar(funcion())

        with mock.patch.object(
                dialogo_prueba_equipo, "DialogoResultadoPrueba") as cuadro, \
                mock.patch.object(
                    dialogo_prueba_equipo.perfiles_obs,
                    "guardar_ajustes") as guardar, \
                mock.patch.object(dialogo_prueba_equipo, "anunciar") as anunciar:
            cuadro.return_value.guardar.return_value = True
            self._panel(en_hilo)._terminada(mock.Mock(), resultado)
        guardar.assert_called_once_with(
            "cliente", resultado.aguantaron, "Casa")
        anunciar.assert_called_once_with(
            "Ajustes guardados en el perfil Casa.")
        self.assertTrue(self.refrescos)


if __name__ == "__main__":
    unittest.main()
