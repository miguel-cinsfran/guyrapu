# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Botones de la página YouTube que no se deshabilitan.

Abren ventanas. Cubren «Iniciar sesión» y «Cerrar sesión»: siempre se alcanzan
con Tab, dicen el motivo en la etiqueta cuando no pueden hacer nada y lo
anuncian al activarlos en ese momento.
"""

import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

import wx

from guyrapu.capture import redaccion
from guyrapu.ui import preferencias_api
from guyrapu.youtube import credenciales
from tests.rutas_temporales import redirigir_rutas
from tests.ventanas_prueba import app_de_prueba, destruir

BASE_LOGIN = "&Iniciar sesión"
BASE_LOGOUT = "Cerrar s&esión"
SIN_BIBLIOTECAS = redaccion.etiqueta_con_motivo(
    BASE_LOGIN, "Faltan las bibliotecas de Google")
ESPERANDO = redaccion.etiqueta_con_motivo(
    BASE_LOGIN, "Esperando la autorización en el navegador")
SIN_SESION = redaccion.etiqueta_con_motivo(
    BASE_LOGOUT, "No hay sesión iniciada")
TOKEN = '{"refresh_token": "x"}'


class _PaginaApi(unittest.TestCase):

    def setUp(self):
        self.app = app_de_prueba()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        parche = redirigir_rutas(Path(self.tmp.name))
        parche.__enter__()
        self.addCleanup(parche.__exit__, None, None, None)

    def _pagina(self, bibliotecas=True, sesion=False):
        marco = wx.Frame(None)
        self.addCleanup(destruir, marco)
        parche = mock.patch.object(
            preferencias_api.youtube_api, "google_disponible",
            return_value=bibliotecas)
        parche.start()
        self.addCleanup(parche.stop)
        if sesion:
            credenciales.guardar_campo("token", TOKEN)
        pagina = preferencias_api.PaginaApi(marco)
        pagina.construir(marco)
        return pagina

    @staticmethod
    def _con_cliente(pagina):
        pagina.txt_cid.SetValue("ID")
        pagina.txt_secret.SetValue("SECRETO")

    @staticmethod
    def _disparar(boton):
        boton.GetEventHandler().ProcessEvent(
            wx.CommandEvent(wx.EVT_BUTTON.typeId, boton.GetId()))

    @contextmanager
    def _red(self, iniciar=None, correr=False):
        hilo = mock.Mock()

        def crear_hilo(target, nombre):
            if correr:
                hilo.start.side_effect = target
            return hilo

        with mock.patch.object(
                preferencias_api.diagnostico, "crear_hilo",
                side_effect=crear_hilo) as crear, \
                mock.patch.object(
                    preferencias_api.youtube_api, "iniciar_sesion",
                    side_effect=iniciar) as login, \
                mock.patch.object(
                    preferencias_api.wx, "CallAfter",
                    side_effect=lambda f, *a: f(*a)), \
                mock.patch.object(preferencias_api, "anunciar") as anunciar, \
                mock.patch.object(preferencias_api._snd, "reproducir"), \
                mock.patch.object(preferencias_api.confirmar, "avisar"):
            yield crear, login, anunciar


class TestNuncaSeDeshabilitan(_PaginaApi):

    def test_p1_siguen_habilitados_en_todos_los_estados(self):
        sin_nada = self._pagina(bibliotecas=False)
        self.assertTrue(sin_nada.btn_api_login.IsEnabled())
        self.assertTrue(sin_nada.btn_api_logout.IsEnabled())
        con_sesion = self._pagina(sesion=True)
        self.assertTrue(con_sesion.btn_api_login.IsEnabled())
        self.assertTrue(con_sesion.btn_api_logout.IsEnabled())
        esperando = self._pagina()
        self._con_cliente(esperando)
        with self._red():
            self._disparar(esperando.btn_api_login)
        self.assertTrue(esperando.btn_api_login.IsEnabled())
        self.assertTrue(esperando.btn_api_logout.IsEnabled())


class TestEtiquetasConMotivo(_PaginaApi):

    def test_p2_llevan_el_motivo_cuando_no_pueden_hacer_nada(self):
        sin_nada = self._pagina(bibliotecas=False)
        self.assertEqual(sin_nada.btn_api_login.GetLabel(), SIN_BIBLIOTECAS)
        self.assertEqual(sin_nada.btn_api_logout.GetLabel(), SIN_SESION)

    def test_p2_sin_motivo_quedan_en_la_base(self):
        con_sesion = self._pagina(sesion=True)
        self.assertEqual(con_sesion.btn_api_login.GetLabel(), BASE_LOGIN)
        self.assertEqual(con_sesion.btn_api_logout.GetLabel(), BASE_LOGOUT)

    def test_p2_mientras_espera_la_autorizacion_lleva_su_motivo(self):
        pagina = self._pagina()
        self._con_cliente(pagina)
        with self._red():
            self._disparar(pagina.btn_api_login)
        self.assertEqual(pagina.btn_api_login.GetLabel(), ESPERANDO)


class TestActivarConMotivo(_PaginaApi):

    def test_p3_sin_bibliotecas_anuncia_y_no_abre_el_navegador(self):
        pagina = self._pagina(bibliotecas=False)
        with self._red() as (crear, login, anunciar):
            self._disparar(pagina.btn_api_login)
        anunciar.assert_called_once_with("Faltan las bibliotecas de Google.")
        crear.assert_not_called()
        login.assert_not_called()

    def test_p3_mientras_espera_anuncia_y_no_lanza_otro_hilo(self):
        pagina = self._pagina()
        self._con_cliente(pagina)
        with self._red() as (crear, login, anunciar):
            self._disparar(pagina.btn_api_login)
            self._disparar(pagina.btn_api_login)
        self.assertEqual(crear.call_count, 1)
        login.assert_not_called()
        anunciar.assert_called_with(
            "Esperando la autorización en el navegador.")

    def test_p3_sin_sesion_anuncia_y_no_cierra_la_sesion(self):
        pagina = self._pagina()
        with mock.patch.object(
                preferencias_api.credenciales, "cerrar_sesion") as cerrar, \
                mock.patch.object(
                    preferencias_api, "anunciar") as anunciar, \
                mock.patch.object(preferencias_api, "avisar") as avisar:
            self._disparar(pagina.btn_api_logout)
        anunciar.assert_called_once_with("No hay sesión iniciada.")
        cerrar.assert_not_called()
        avisar.assert_not_called()


class TestAlTerminarElLogin(_PaginaApi):

    def test_p4_con_exito_vuelven_a_la_base(self):
        pagina = self._pagina()
        self._con_cliente(pagina)
        etiquetas = []

        def iniciar(cid, secret):
            etiquetas.append(pagina.btn_api_login.GetLabel())
            return TOKEN

        with self._red(iniciar=iniciar, correr=True):
            self._disparar(pagina.btn_api_login)
        self.assertEqual(etiquetas, [ESPERANDO])
        self.assertEqual(pagina.btn_api_login.GetLabel(), BASE_LOGIN)
        self.assertEqual(pagina.btn_api_logout.GetLabel(), BASE_LOGOUT)

    def test_p4_con_error_vuelve_a_la_base_y_refleja_la_sesion(self):
        pagina = self._pagina()
        self._con_cliente(pagina)
        etiquetas = []

        def iniciar(cid, secret):
            etiquetas.append(pagina.btn_api_login.GetLabel())
            raise OSError("sin red")

        with self._red(iniciar=iniciar, correr=True):
            self._disparar(pagina.btn_api_login)
        self.assertEqual(etiquetas, [ESPERANDO])
        self.assertEqual(pagina.btn_api_login.GetLabel(), BASE_LOGIN)
        self.assertEqual(pagina.btn_api_logout.GetLabel(), SIN_SESION)


if __name__ == "__main__":
    unittest.main()
