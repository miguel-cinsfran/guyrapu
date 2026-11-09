# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de los cuadros de la prueba de conexión. Abren ventanas."""

import threading
import unittest
from dataclasses import replace
from unittest import mock

import wx

from guyrapu.core.idioma import _
from guyrapu.obs import ajustes_perfil, obs_cliente, prueba_conexion
from guyrapu.ui import dialogo_prueba_conexion
from tests.ventanas_prueba import app_de_prueba, destruir


def _ajustes():
    return ajustes_perfil.AjustesPerfil(bitrate_video=2500)


def _resultado(aguantaron, mayor=None, pasos=None, errores=()):
    original = _ajustes()
    if pasos is None:
        pasos = (prueba_conexion.PasoRed(2500, 0, 100),)
    return prueba_conexion.ResultadoConexion(
        "Casa", original, 2500, aguantaron, mayor, pasos, False, errores)


class BaseCuadro(unittest.TestCase):

    def setUp(self):
        self.app = app_de_prueba()

    def _mostrar(self, cuadro):
        self.addCleanup(destruir, cuadro)
        cuadro.Show()
        wx.Yield()
        return cuadro


class TestDialogoPruebaConexion(BaseCuadro):

    def test_dice_que_se_va_a_hacer_perfil_bitrate_y_duracion(self):
        cuadro = self._mostrar(dialogo_prueba_conexion.DialogoPruebaConexion(
            None, "Casa", 2500, 60))
        texto = cuadro.texto()
        self.assertIn("directo privado de prueba", texto)
        self.assertIn("nadie ve", texto)
        self.assertIn("se borra al terminar", texto)
        self.assertIn("Casa", texto)
        self.assertIn("2500 kbps", texto)
        self.assertIn("60 segundos", texto)
        self.assertTrue(cuadro.txt_detalle.GetWindowStyle() & wx.TE_READONLY)
        self.assertTrue(cuadro.btn_empezar.HasFocus())
        self.assertEqual(cuadro.btn_cancelar.GetLabel(), "&Cancelar")

    def test_el_texto_se_alcanza_con_tab_antes_de_los_botones(self):
        cuadro = self._mostrar(dialogo_prueba_conexion.DialogoPruebaConexion(
            None, "Casa", 2500, 60))
        self.assertLess(cuadro.txt_detalle.GetPosition().y,
                        cuadro.btn_empezar.GetPosition().y)


class TestDialogoProgresoPruebaConexion(BaseCuadro):

    def test_cancelar_corta_la_prueba_y_el_foco_queda_en_cancelar(self):
        parada = threading.Event()
        cuadro = self._mostrar(
            dialogo_prueba_conexion.DialogoProgresoPruebaConexion(
                None, parada))
        self.assertTrue(cuadro.btn_cancelar.HasFocus())
        cuadro._cancelar(None)
        self.assertTrue(parada.is_set())
        self.assertFalse(cuadro.btn_cancelar.IsEnabled())

    def test_cada_bitrate_se_muestra_y_se_anuncia(self):
        parada = threading.Event()
        cuadro = self._mostrar(
            dialogo_prueba_conexion.DialogoProgresoPruebaConexion(
                None, parada))
        with mock.patch.object(
                dialogo_prueba_conexion, "anunciar") as anunciar:
            cuadro.mostrar_bitrate(2500)
        self.assertIn("Probando la conexión a 2500 kbps",
                      cuadro.txt_estado.GetValue())
        anunciar.assert_called_once_with(cuadro.txt_estado.GetValue())


class TestDialogoResultadoPruebaConexion(BaseCuadro):

    def test_si_el_perfil_aguanta_lo_dice_con_el_mayor_y_solo_cierra(self):
        cuadro = self._mostrar(
            dialogo_prueba_conexion.DialogoResultadoPruebaConexion(
                None, _resultado(2500, mayor=3800)))
        texto = cuadro.texto()
        self.assertIn("aguantó con 2500 kbps", texto)
        self.assertIn("hasta 3800 kbps", texto)
        self.assertFalse(hasattr(cuadro, "btn_guardar"))
        self.assertTrue(hasattr(cuadro, "btn_cerrar"))
        self.assertTrue(cuadro.txt_resultado.HasFocus())

    def test_si_aguanta_uno_menor_ofrece_guardar_y_dejar(self):
        pasos = (prueba_conexion.PasoRed(2500, 5, 100),
                 prueba_conexion.PasoRed(1300, 0, 100))
        cuadro = self._mostrar(
            dialogo_prueba_conexion.DialogoResultadoPruebaConexion(
                None, _resultado(1300, pasos=pasos)))
        texto = cuadro.texto()
        self.assertIn("no aguantó con 2500 kbps", texto)
        self.assertIn("Aguanta con 1300 kbps", texto)
        self.assertTrue(hasattr(cuadro, "btn_guardar"))
        self.assertTrue(hasattr(cuadro, "btn_dejar"))
        self.assertFalse(cuadro.guardar())

    def test_si_nada_aguanta_lo_dice_con_el_porcentaje_del_ultimo(self):
        pasos = (prueba_conexion.PasoRed(2500, 5, 100),
                 prueba_conexion.PasoRed(1300, 3, 100))
        cuadro = self._mostrar(
            dialogo_prueba_conexion.DialogoResultadoPruebaConexion(
                None, _resultado(None, pasos=pasos)))
        texto = cuadro.texto()
        self.assertIn("Ninguna tasa de bits aguantó", texto)
        self.assertIn("3 %", texto)
        self.assertTrue(hasattr(cuadro, "btn_cerrar"))

    def test_si_quedo_algo_pendiente_lo_nombra(self):
        cuadro = self._mostrar(
            dialogo_prueba_conexion.DialogoResultadoPruebaConexion(
                None, _resultado(2500, errores=(
                    "El directo privado «Prueba de conexión de Guyrapu» quedó "
                    "en YouTube.",))))
        self.assertIn("Quedó pendiente", cuadro.texto())
        self.assertIn("Prueba de conexión de Guyrapu", cuadro.texto())


class TestCoordinador(unittest.TestCase):

    def setUp(self):
        self.app = app_de_prueba()
        self.refrescos = []

    def _panel(self, en_hilo=None, anunciar_texto=None, cliente=None):
        return dialogo_prueba_conexion.PruebaConexionPanel(
            None, en_hilo or (lambda _funcion, _terminar: None),
            cliente or "cliente-obs", "cliente-yt", True,
            lambda: self.refrescos.append(True),
            anunciar_texto or (lambda _texto, error=False: None))

    def test_al_cancelar_anuncia_que_obs_y_youtube_quedaron_limpios(self):
        resultado = _resultado(None, pasos=())
        resultado = replace(resultado, cancelada=True)
        with mock.patch.object(dialogo_prueba_conexion, "anunciar") as anunciar:
            self._panel()._terminada(mock.Mock(), resultado)
        anunciar.assert_called_once_with(
            "Prueba cancelada. OBS quedó como estaba y la prueba se borró "
            "de YouTube.")
        self.assertTrue(self.refrescos)

    def test_un_fallo_se_anuncia_con_su_texto(self):
        avisos = []
        panel = self._panel(
            anunciar_texto=lambda texto, error=False: avisos.append(texto))
        panel._terminada(
            mock.Mock(), prueba_conexion.ErrorPruebaConexion("sin sesión"))
        self.assertEqual(avisos, ["sin sesión"])

    def test_al_guardar_avisa_con_el_perfil_y_el_bitrate(self):
        resultado = _resultado(1300)

        def en_hilo(funcion, al_terminar):
            al_terminar(funcion())

        with mock.patch.object(
                dialogo_prueba_conexion, "DialogoResultadoPruebaConexion") as cuadro, \
                mock.patch.object(
                    dialogo_prueba_conexion.perfiles_obs,
                    "guardar_ajustes") as guardar, \
                mock.patch.object(dialogo_prueba_conexion, "anunciar") as anunciar:
            cuadro.return_value.guardar.return_value = True
            self._panel(en_hilo)._terminada(mock.Mock(), resultado)
        guardar.assert_called_once_with(
            "cliente-obs", replace(resultado.original, bitrate_video=1300),
            "Casa")
        anunciar.assert_called_once_with(
            "Tasa de bits guardada en el perfil Casa: 1300 kbps.")
        self.assertTrue(self.refrescos)

    def test_un_error_de_obs_generico_dice_que_fue_de_la_prueba(self):
        avisos = []
        panel = self._panel(
            anunciar_texto=lambda texto, error=False: avisos.append(texto))
        panel._terminada(mock.Mock(), obs_cliente.ObsError("sin OBS"))
        self.assertIn("sin OBS", avisos[0])
        self.assertIn("prueba de conexión", avisos[0])


class TestFalloDelPanel(unittest.TestCase):

    def _panel(self, anunciar_texto):
        return dialogo_prueba_conexion.PruebaConexionPanel(
            None, lambda _funcion, _terminar: None, "cliente-obs",
            "cliente-yt", True, lambda: None, anunciar_texto)

    def test_p3_una_sesion_vencida_dice_que_hay_que_volver_a_entrar(self):
        error = RuntimeError(
            "('invalid_grant: Token has been expired or revoked.', {})")
        texto = self._panel(lambda _texto, error=False: None)._texto_fallo(
            error)
        self.assertEqual(
            texto,
            "Tu sesión de YouTube caducó. Vuelve a iniciar sesión en "
            "Preferencias, categoría YouTube.")

    def test_p4_el_texto_con_algo_pendiente_no_termina_con_dos_puntos(self):
        error = prueba_conexion.ErrorPruebaConexion(
            _(prueba_conexion.MENSAJE_ERROR_RESTABLECER).format(
                error="OBS no pudo completar la operación. Vuelve a intentarlo.",
                errores="Restablecer los ajustes del perfil: OBS no pudo "
                        "completar la operación. Vuelve a intentarlo."))
        texto = self._panel(lambda _texto, error=False: None)._texto_fallo(
            error)
        self.assertFalse(texto.endswith(".."), texto)

    def test_p5_el_fallo_llega_al_aviso_con_error(self):
        recibidos = []
        panel = self._panel(
            lambda texto, error=False: recibidos.append((texto, error)))
        panel._terminada(mock.Mock(), obs_cliente.ObsError("sin OBS"))
        self.assertEqual(recibidos[0][1], True)

    def test_p5_el_texto_de_error_va_por_avisar_con_el_sonido_de_error(self):
        from guyrapu.ui import obs_ventana
        general = mock.Mock()
        falso = mock.Mock()
        falso._pagina_general = general
        with mock.patch.object(
                obs_ventana.aviso_importante, "avisar") as avisar, \
                mock.patch.object(obs_ventana, "anunciar") as anunciar:
            obs_ventana.VentanaObs._anunciar_equipo(
                falso, "sin OBS", error=True)
        general.mostrar.assert_called_once_with(["sin OBS"])
        avisar.assert_called_once_with("sin OBS", "error", error=True)
        anunciar.assert_not_called()

    def test_p5_un_texto_sin_error_se_sigue_anunciando(self):
        from guyrapu.ui import obs_ventana
        general = mock.Mock()
        falso = mock.Mock()
        falso._pagina_general = general
        with mock.patch.object(
                obs_ventana.aviso_importante, "avisar") as avisar, \
                mock.patch.object(obs_ventana, "anunciar") as anunciar:
            obs_ventana.VentanaObs._anunciar_equipo(falso, "listo")
        general.mostrar.assert_called_once_with(["listo"])
        anunciar.assert_called_once_with("listo")
        avisar.assert_not_called()


if __name__ == "__main__":
    unittest.main()
