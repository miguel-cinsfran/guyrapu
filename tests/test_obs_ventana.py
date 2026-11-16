# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de la búsqueda y el primer plano de la ventana de OBS."""

import ctypes
import unittest
from ctypes import wintypes
from types import SimpleNamespace
from unittest import mock

import wx

from tests.pseudo_prueba import con_pseudo
from tests.ventanas_prueba import app_de_prueba, destruir
from guyrapu.core.idioma import _
from guyrapu.obs import obs_ventana
from guyrapu.ui import gui_grabaciones
from guyrapu.ui import obs_pagina_general
from guyrapu.ui import obs_ventana as panel_obs
from guyrapu.ui import operaciones_obs


class TestMostrar(unittest.TestCase):

    def test_sin_ventana_avisa_que_obs_no_esta_abierto(self):
        self.assertEqual(
            obs_ventana.mostrar(buscar=lambda: None),
            obs_ventana.TEXTO_SIN_OBS)

    def test_ventana_traida_no_devuelve_texto(self):
        self.assertEqual(
            obs_ventana.mostrar(buscar=lambda: 1234, traer=lambda h: True),
            "")

    def test_ventana_no_traida_avisa_el_fallo(self):
        vistos = []
        self.assertEqual(
            obs_ventana.mostrar(
                buscar=lambda: 5678,
                traer=lambda h: vistos.append(h) or False),
            obs_ventana.TEXTO_SIN_FRENTE)
        self.assertEqual(vistos, [5678])

    def test_buscar_que_lanza_cuenta_como_no_encontrado(self):
        def buscar():
            raise OSError("fallo de ctypes")

        self.assertEqual(
            obs_ventana.mostrar(buscar=buscar),
            obs_ventana.TEXTO_SIN_OBS)


class TestMostrarTrabada(unittest.TestCase):

    def test_ventana_trabada_avisa_y_no_la_trae(self):
        traidas = []
        self.assertEqual(
            obs_ventana.mostrar(
                buscar=lambda: 1234,
                trabada=lambda h: True,
                traer=lambda h: traidas.append(h) or True),
            obs_ventana.TEXTO_OBS_TRABADO)
        self.assertEqual(traidas, [])

    def test_ventana_no_trabada_la_trae_como_hoy(self):
        traidas = []
        self.assertEqual(
            obs_ventana.mostrar(
                buscar=lambda: 5678,
                trabada=lambda h: False,
                traer=lambda h: traidas.append(h) or True),
            "")
        self.assertEqual(traidas, [5678])


class TestPseudoTextos(unittest.TestCase):
    """Bajo pseudotraducción, cada frase al usuario sale marcada."""

    def test_avisos_salen_marcados(self):
        def buscar():
            raise OSError("fallo de ctypes")

        with con_pseudo():
            marcados = [
                obs_ventana.mostrar(buscar=lambda: None),
                obs_ventana.mostrar(buscar=buscar),
                obs_ventana.mostrar(
                    buscar=lambda: 5678, traer=lambda h: False),
                obs_ventana.mostrar(
                    buscar=lambda: 1234, trabada=lambda h: True),
                _(obs_ventana.TEXTO_SIN_OBS),
                _(obs_ventana.TEXTO_SIN_FRENTE),
                _(obs_ventana.TEXTO_OBS_TRABADO),
            ]
        for texto in marcados:
            with self.subTest(texto=texto):
                self.assertTrue(texto.startswith("[¡"), texto)


class TestBuscarVentanaReal(unittest.TestCase):

    def test_buscar_ventana_no_lanza_y_da_none_o_entero(self):
        resultado = obs_ventana.buscar_ventana()
        self.assertTrue(resultado is None or isinstance(resultado, int))


class TestVentanaTrabadaReal(unittest.TestCase):

    def test_el_escritorio_no_esta_trabado(self):
        user32 = ctypes.WinDLL("user32")
        user32.GetDesktopWindow.argtypes = []
        user32.GetDesktopWindow.restype = wintypes.HWND
        escritorio = user32.GetDesktopWindow()
        self.assertTrue(escritorio)
        self.assertFalse(obs_ventana._ventana_trabada(escritorio))


class TestTraerAsync(unittest.TestCase):

    def test_trae_con_showwindowasync(self):
        user32 = mock.MagicMock()
        with mock.patch.object(
                obs_ventana.ctypes, "WinDLL", return_value=user32):
            self.assertTrue(obs_ventana._traer(1234))
        self.assertTrue(user32.ShowWindowAsync.called)
        self.assertFalse(user32.ShowWindow.called)


class TestBotonCerrarObs(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = app_de_prueba()

    @classmethod
    def tearDownClass(cls):
        del cls.app

    def _pagina(self, al_cerrar=None):
        marco = wx.Frame(None)
        self.addCleanup(destruir, marco)
        pagina = obs_pagina_general.PaginaGeneral(
            marco, lambda: None, lambda: None,
            al_cerrar or (lambda: None), lambda: None, lambda: None)
        self.addCleanup(destruir, pagina)
        return pagina

    def test_boton_con_nombre_accesible_despues_de_mostrar(self):
        pagina = self._pagina()
        self.assertEqual(pagina.btn_cerrar.GetLabel(), _("&Cerrar OBS"))
        self.assertEqual(pagina.btn_cerrar.GetName(), _("Cerrar OBS"))
        self.assertTrue(pagina.btn_cerrar.IsEnabled())
        self.assertIn(pagina.btn_cerrar, pagina.acciones)
        self.assertIs(pagina.btn_mostrar.GetNextSibling(),
                      pagina.btn_cerrar)

    def test_pulsarlo_llama_a_al_cerrar(self):
        llamadas = []
        pagina = self._pagina(lambda: llamadas.append("cerrar"))
        evento = wx.CommandEvent(
            wx.EVT_BUTTON.typeId, pagina.btn_cerrar.GetId())
        pagina.btn_cerrar.GetEventHandler().ProcessEvent(evento)
        self.assertEqual(llamadas, ["cerrar"])


class GestorSinConexion:
    """Gestor doble que nunca se conecta con OBS."""

    conectado = False

    def conectar(self):
        pass

    def cerrar(self):
        pass


class TestVentanaSinDeshabilitar(unittest.TestCase):
    """Sin conexión o en vuelo, todo control sigue en el recorrido con Tab."""

    @classmethod
    def setUpClass(cls):
        cls.app = app_de_prueba()

    @classmethod
    def tearDownClass(cls):
        del cls.app

    def _crear(self, gestor=None):
        principal = SimpleNamespace(_config={})
        with mock.patch.object(panel_obs.VentanaObs, "_en_hilo"), \
                mock.patch.object(gui_grabaciones.grabaciones, "existentes",
                                  return_value=[]):
            dialogo = panel_obs.VentanaObs(
                None, principal, gestor=gestor or GestorSinConexion())
        self.addCleanup(destruir, dialogo)
        return dialogo

    def _fallar(self, dialogo):
        with mock.patch.object(operaciones_obs, "avisar"):
            dialogo._operaciones.fallo("OBS está abierto pero no responde")
        return dialogo

    def _paginas(self, dialogo):
        return (dialogo._pagina_transmision, dialogo._pagina_escena,
                dialogo._pagina_audio, dialogo._pagina_grabacion,
                dialogo._pagina_perfiles, dialogo._pagina_fuentes,
                dialogo._pagina_general)

    def _pulsar(self, control):
        control.GetEventHandler().ProcessEvent(
            wx.CommandEvent(wx.EVT_BUTTON.typeId, control.GetId()))

    def _pulsar_casilla(self, control):
        control.GetEventHandler().ProcessEvent(
            wx.CommandEvent(wx.EVT_CHECKBOX.typeId, control.GetId()))

    def _en_vuelo(self, dialogo):
        with mock.patch.object(operaciones_obs.diagnostico, "crear_hilo",
                               return_value=mock.Mock()):
            dialogo._en_hilo(lambda: None)

    def test_sin_conexion_y_en_vuelo_ningun_control_se_deshabilita(self):
        dialogo = self._fallar(self._crear())
        for pagina in self._paginas(dialogo):
            for control in pagina.acciones:
                self.assertTrue(control.IsEnabled(), control.GetName())
        self._en_vuelo(dialogo)
        self.assertTrue(dialogo._operaciones.en_vuelo)
        for pagina in self._paginas(dialogo):
            for control in pagina.acciones:
                self.assertTrue(control.IsEnabled(), control.GetName())

    def test_sin_conexion_btn_cambiar_dice_el_motivo_y_avisa_al_pulsar(self):
        dialogo = self._fallar(self._crear())
        boton = dialogo._pagina_escena.btn_cambiar
        self.assertIn("(sin conexión con OBS)", boton.GetLabel())
        with mock.patch.object(operaciones_obs, "anunciar") as anunciar, \
                mock.patch.object(dialogo._operaciones,
                                  "en_hilo") as en_hilo:
            self._pulsar(boton)
        anunciar.assert_called_once_with("OBS no está conectado.")
        en_hilo.assert_not_called()

    def test_sin_conexion_cada_accion_que_necesita_obs_dice_el_motivo(self):
        dialogo = self._fallar(self._crear())
        controles = (
            dialogo._pagina_escena.btn_cambiar,
            dialogo._pagina_escena.btn_agregar,
            dialogo._pagina_audio.chk_silenciar,
            dialogo._pagina_audio.btn_probar,
            dialogo._pagina_audio.btn_filtros,
            dialogo._pagina_audio.chk_escuchar,
            dialogo._pagina_grabacion._grabacion.boton,
            dialogo._pagina_grabacion._grabacion.pausar,
            dialogo._pagina_perfiles.btn_usar,
            dialogo._pagina_fuentes.btn_diseno,
            dialogo._pagina_fuentes.btn_restaurar,
            dialogo._pagina_general.btn_actualizar,
        )
        for control in controles:
            with self.subTest(control=control.GetName()):
                self.assertIn("(sin conexión con OBS)", control.GetLabel())

    def test_en_vuelo_una_accion_avisa_y_no_cambia_su_etiqueta(self):
        dialogo = self._crear()
        boton = dialogo._pagina_escena.btn_cambiar
        etiqueta = boton.GetLabel()
        self._en_vuelo(dialogo)
        with mock.patch.object(operaciones_obs, "anunciar") as anunciar, \
                mock.patch.object(dialogo._operaciones,
                                  "en_hilo") as en_hilo:
            self._pulsar(boton)
        anunciar.assert_called_once_with("Consultando OBS.")
        en_hilo.assert_not_called()
        self.assertEqual(boton.GetLabel(), etiqueta)

    def test_en_vuelo_probar_el_equipo_avisa_y_no_abre_el_cuadro(self):
        dialogo = self._crear()
        self._en_vuelo(dialogo)
        with mock.patch.object(operaciones_obs, "anunciar") as anunciar, \
                mock.patch.object(
                    panel_obs.dialogo_prueba_equipo,
                    "PruebaEquipoPanel") as panel:
            self._pulsar(dialogo._pagina_general.btn_probar_equipo)
        anunciar.assert_called_once_with("Consultando OBS.")
        panel.assert_not_called()

    def test_sin_conexion_la_casilla_de_silenciar_vuelve_a_su_valor(self):
        dialogo = self._fallar(self._crear())
        pagina = dialogo._pagina_audio
        pagina._poner_filas((("Mic/Aux", False, ()),), "Mic/Aux")
        casilla = pagina.chk_silenciar
        casilla.SetValue(True)
        with mock.patch.object(operaciones_obs, "anunciar") as anunciar, \
                mock.patch.object(dialogo._operaciones,
                                  "en_hilo") as en_hilo:
            self._pulsar_casilla(casilla)
        self.assertFalse(casilla.GetValue())
        anunciar.assert_called_once_with("OBS no está conectado.")
        en_hilo.assert_not_called()

    def test_al_conectar_las_etiquetas_vuelven_a_su_texto_sin_motivo(self):
        dialogo = self._fallar(self._crear())
        boton = dialogo._pagina_escena.btn_cambiar
        self.assertIn("(sin conexión con OBS)", boton.GetLabel())
        dialogo._gestor.conectado = True
        dialogo._operaciones._terminar(None, None)
        self.assertEqual(boton.GetLabel(), _("Cambiar e&scena"))
        self.assertNotIn(
            "sin conexión", dialogo._pagina_general.btn_actualizar.GetLabel())

    def test_sin_conexion_probar_el_equipo_sigue_abriendo_el_cuadro(self):
        dialogo = self._fallar(self._crear())
        with mock.patch.object(
                dialogo, "_cliente_obs", return_value=object()), \
                mock.patch.object(
                    panel_obs.dialogo_prueba_equipo,
                    "PruebaEquipoPanel") as panel:
            self._pulsar(dialogo._pagina_general.btn_probar_equipo)
        panel.assert_called_once()


if __name__ == "__main__":
    unittest.main()
