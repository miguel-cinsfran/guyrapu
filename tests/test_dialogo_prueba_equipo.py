# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de los cuadros de la prueba del equipo. Abren ventanas."""

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


class TestCasillaVertical(BaseCuadro):

    def test_con_el_plugin_la_casilla_esta_sin_marcar_antes_de_empezar(self):
        cuadro = self._mostrar(dialogo_prueba_equipo.DialogoPruebaEquipo(
            None, "Casa", _ajustes(), 48, vertical=True))
        self.assertIsNotNone(cuadro.chk_vertical)
        self.assertFalse(cuadro.chk_vertical.IsChecked())
        self.assertEqual(
            cuadro.chk_vertical.GetName(),
            "Incluir el lienzo vertical, para transmitir en horizontal y "
            "vertical a la vez")
        self.assertLess(cuadro.txt_detalle.GetPosition().y,
                        cuadro.chk_vertical.GetPosition().y)
        self.assertLess(cuadro.chk_vertical.GetPosition().y,
                        cuadro.btn_empezar.GetPosition().y)
        self.assertTrue(cuadro.btn_empezar.HasFocus())
        self.assertIn("se graban los dos y se borran las dos grabaciones",
                      cuadro.texto())

    def test_sin_el_plugin_no_hay_casilla_ni_frase(self):
        cuadro = self._mostrar(dialogo_prueba_equipo.DialogoPruebaEquipo(
            None, "Casa", _ajustes(), 48))
        self.assertIsNone(cuadro.chk_vertical)
        self.assertNotIn("se graban los dos", cuadro.texto())


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

    def _panel(self, en_hilo=None, anunciar_texto=None, escribir_texto=None):
        return dialogo_prueba_equipo.PruebaEquipoPanel(
            None, en_hilo or (lambda _funcion, _terminar: None),
            "cliente", lambda: self.refrescos.append(True),
            anunciar_texto or (lambda _texto, error=False: None),
            escribir_texto)

    def test_al_cancelar_lo_deja_escrito_en_la_ventana(self):
        resultado = prueba_equipo.ResultadoEquipo(
            "Casa", _ajustes(), None, (), cancelada=True)
        progreso = mock.Mock()
        self._panel()._terminada(progreso, resultado)
        progreso.terminar.assert_called_once_with(
            "Prueba cancelada. OBS quedó como estaba.", error=False)
        self.assertTrue(self.refrescos)

    def test_un_fallo_despues_de_abrir_la_ventana_queda_escrito(self):
        avisos = []
        escritos = []
        panel = self._panel(
            anunciar_texto=lambda texto, error=False: avisos.append(texto),
            escribir_texto=escritos.append)
        progreso = mock.Mock()
        panel._terminada(progreso, obs_cliente.ObsError("sin OBS"))
        texto = progreso.terminar.call_args.args[0]
        self.assertIn("sin OBS", texto)
        self.assertIn("OBS quedó como estaba", texto)
        self.assertEqual(progreso.terminar.call_args.kwargs["error"], True)
        self.assertEqual(escritos, [texto])
        self.assertEqual(avisos, [])

    def test_preparar_avisa_si_esta_el_plugin_vertical(self):
        panel = self._panel()
        preparacion = mock.Mock()
        with mock.patch.object(
                dialogo_prueba_equipo.prueba_equipo, "preparar",
                return_value=preparacion), \
                mock.patch.object(
                    dialogo_prueba_equipo.lienzo_vertical, "detectar",
                    return_value={"canvasUuid": "x"}):
            self.assertEqual(panel._preparar(), (preparacion, True))
        with mock.patch.object(
                dialogo_prueba_equipo.prueba_equipo, "preparar",
                return_value=preparacion), \
                mock.patch.object(
                    dialogo_prueba_equipo.lienzo_vertical, "detectar",
                    return_value=None):
            self.assertEqual(panel._preparar(), (preparacion, False))

    def _correr_capturando(self, incluir_vertical):
        panel = self._panel()
        capturado = {}

        def en_hilo(funcion, al_terminar=None):
            capturado["funcion"] = funcion

        panel._en_hilo = en_hilo
        with mock.patch.object(
                dialogo_prueba_equipo, "VentanaEspera"), \
                mock.patch.object(
                    dialogo_prueba_equipo.prueba_equipo,
                    "ejecutar") as ejecutar, \
                mock.patch.object(
                    dialogo_prueba_equipo, "prueba_vertical") as vertical:
            vertical.ClienteVertical.return_value = "envuelto"
            panel._correr(mock.Mock(disponibles=()),
                          incluir_vertical=incluir_vertical)
            capturado["funcion"]()
        return ejecutar, vertical

    def test_con_la_casilla_marcada_corre_con_el_cliente_envuelto(self):
        ejecutar, vertical = self._correr_capturando(True)
        vertical.ClienteVertical.assert_called_once_with("cliente")
        self.assertEqual(ejecutar.call_args.args[0], "envuelto")

    def test_con_la_casilla_sin_marcar_corre_con_el_cliente_de_siempre(self):
        ejecutar, vertical = self._correr_capturando(False)
        vertical.ClienteVertical.assert_not_called()
        self.assertEqual(ejecutar.call_args.args[0], "cliente")

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


class TestFalloDelPanel(unittest.TestCase):

    def test_p5_un_fallo_antes_de_abrir_la_ventana_va_por_el_aviso(self):
        recibidos = []
        panel = dialogo_prueba_equipo.PruebaEquipoPanel(
            None, lambda _funcion, _terminar: None, "cliente",
            lambda: None,
            lambda texto, error=False: recibidos.append((texto, error)))
        panel._preparado(obs_cliente.ObsError("sin OBS"))
        self.assertEqual(recibidos[0][1], True)


if __name__ == "__main__":
    unittest.main()
