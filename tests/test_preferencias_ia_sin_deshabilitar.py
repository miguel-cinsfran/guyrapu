# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Botones de la página Inteligencia artificial que no se deshabilitan.

Abren ventanas. Cubren «Probar clave» y «Actualizar lista de modelos»: siempre
se alcanzan con Tab, dicen el motivo en la etiqueta mientras trabajan y lo
anuncian al activarlos en ese momento.
"""

import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

import wx

from guyrapu.ai import catalogo
from guyrapu.ai import protocolos
from guyrapu.capture import redaccion
from guyrapu.ui import preferencias_ia
from guyrapu.ui import preferencias_ia_clave
from guyrapu.ui import preferencias_ia_lista
from guyrapu.voice import motores
from tests.rutas_temporales import redirigir_rutas
from tests.ventanas_prueba import app_de_prueba, armar_preferencias, destruir

BASE_PROBAR = "Compro&bar clave"
PROBANDO = redaccion.etiqueta_con_motivo(BASE_PROBAR, "Probando la clave")
BASE_ACTUALIZAR = "&Actualizar lista de modelos"
ACTUALIZANDO = redaccion.etiqueta_con_motivo(
    BASE_ACTUALIZAR, "Actualizando la lista de modelos")
CLAVE_GEMINI = "AIza" + "a" * 35


def _catalogo_de_prueba():
    base = "https://generativelanguage.googleapis.com/v1beta"
    return {
        "version": catalogo.VERSION,
        "fecha": "2026-10-21",
        "proveedores": {
            "google": {
                "nombre": "Google",
                "modelos": [
                    {"id": "gemini-gratis", "nombre": "Gemini Gratis",
                     "protocolo": protocolos.GEMINI, "base": base,
                     "gratis": True},
                    {"id": "gemini-caro", "nombre": "Gemini Caro",
                     "protocolo": protocolos.GEMINI, "base": base},
                ],
            },
        },
    }


class _PaginaIA(unittest.TestCase):
    def setUp(self):
        self.app = app_de_prueba()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        parche = redirigir_rutas(Path(self.tmp.name))
        parche.__enter__()
        self.addCleanup(parche.__exit__, None, None, None)
        sin_clave = mock.patch.object(
            preferencias_ia_clave.claves, "leer", return_value="")
        sin_clave.start()
        self.addCleanup(sin_clave.stop)

    def _dialogo(self, muestra=None):
        with mock.patch.object(motores, "listar_voces",
                               return_value=["Voz de prueba"]), \
                mock.patch.object(
                    preferencias_ia.catalogo, "cargar",
                    return_value=muestra or _catalogo_de_prueba()):
            dialogo = armar_preferencias({}, "Inteligencia artificial")
        self.addCleanup(destruir, dialogo)
        return dialogo

    def _pagina_con_clave(self):
        pagina = self._dialogo().pagina_ia
        pagina.cho_ia_modelo.SetSelection(0)
        pagina.ia_clave.txt_clave.SetValue(CLAVE_GEMINI)
        return pagina

    @staticmethod
    def _disparar(boton):
        boton.GetEventHandler().ProcessEvent(
            wx.CommandEvent(wx.EVT_BUTTON.typeId, boton.GetId()))


class TestProbarClaveSinDeshabilitar(_PaginaIA):

    @contextmanager
    def _red(self, pagina, enviar=None, correr=False):
        hilo = mock.Mock()
        destino = {}
        if enviar is None:
            enviar = mock.Mock()

        def crear_hilo(target, nombre):
            destino["target"] = target
            if correr:
                hilo.start.side_effect = target
            return hilo

        with mock.patch.object(
                preferencias_ia.diagnostico, "crear_hilo",
                side_effect=crear_hilo) as crear, \
                mock.patch.object(
                    preferencias_ia.envio_ia, "enviar",
                    side_effect=enviar), \
                mock.patch.object(
                    preferencias_ia.wx, "CallAfter",
                    side_effect=lambda f, *a: f(*a)), \
                mock.patch.object(
                    preferencias_ia._snd, "reproducir") as sonar, \
                mock.patch.object(preferencias_ia, "anunciar") as anunciar:
            yield destino, crear, anunciar, sonar

    def test_p1_sigue_habilitado_mientras_prueba(self):
        pagina = self._pagina_con_clave()
        with self._red(pagina):
            self._disparar(pagina.btn_ia_probar_clave)
        self.assertTrue(pagina.btn_ia_probar_clave.IsEnabled())

    def test_p2_lleva_el_motivo_mientras_prueba(self):
        pagina = self._pagina_con_clave()
        boton = pagina.btn_ia_probar_clave
        self.assertEqual(boton.GetLabel(), BASE_PROBAR)
        with self._red(pagina):
            self._disparar(boton)
        self.assertEqual(boton.GetLabel(), PROBANDO)

    def test_p3_activar_mientras_prueba_anuncia_y_no_repite(self):
        pagina = self._pagina_con_clave()
        with self._red(pagina) as (_destino, crear, anunciar, _sonar):
            self._disparar(pagina.btn_ia_probar_clave)
            self._disparar(pagina.btn_ia_probar_clave)
        self.assertEqual(crear.call_count, 1)
        anunciar.assert_any_call("Probando la clave.")

    def _etiqueta_mientras_prueba(self, pagina, enviar, correr):
        etiquetas = []

        def enviar_anotando(pedido, clave, tiempo_espera):
            etiquetas.append(pagina.btn_ia_probar_clave.GetLabel())
            return enviar(pedido, clave, tiempo_espera)

        with self._red(pagina, enviar=enviar_anotando, correr=correr):
            self._disparar(pagina.btn_ia_probar_clave)
        return etiquetas

    def test_p4_vuelve_a_la_base_con_exito(self):
        pagina = self._pagina_con_clave()
        etiquetas = self._etiqueta_mientras_prueba(
            pagina, lambda *_argumentos: mock.Mock(), correr=True)
        self.assertEqual(etiquetas, [PROBANDO])
        self.assertEqual(pagina.btn_ia_probar_clave.GetLabel(), BASE_PROBAR)
        self.assertTrue(pagina.btn_ia_probar_clave.IsEnabled())

    def test_p4_vuelve_a_la_base_con_error(self):
        pagina = self._pagina_con_clave()

        def enviar(*_argumentos):
            raise OSError("sin red")

        etiquetas = self._etiqueta_mientras_prueba(
            pagina, enviar, correr=True)
        self.assertEqual(etiquetas, [PROBANDO])
        self.assertEqual(pagina.btn_ia_probar_clave.GetLabel(), BASE_PROBAR)
        self.assertTrue(pagina.btn_ia_probar_clave.IsEnabled())


class TestActualizarListaSinDeshabilitar(_PaginaIA):

    @contextmanager
    def _red(self, pagina, descargar=None, enviar=None, correr=False):
        if descargar is None:
            def descargar(*_argumentos):
                return _catalogo_de_prueba()
        if enviar is None:
            enviar = mock.Mock()
        hilo = mock.Mock()

        def crear_hilo(target, nombre):
            if correr:
                hilo.start.side_effect = target
            return hilo

        with mock.patch.object(
                preferencias_ia_lista.catalogo, "descargar",
                side_effect=descargar), \
                mock.patch.object(
                    preferencias_ia_lista.diagnostico, "crear_hilo",
                    side_effect=crear_hilo) as crear, \
                mock.patch.object(
                    preferencias_ia_lista.envio_ia, "enviar",
                    side_effect=enviar), \
                mock.patch.object(
                    preferencias_ia_lista.wx, "CallAfter",
                    side_effect=lambda f, *a: f(*a)), \
                mock.patch.object(
                    preferencias_ia_lista._snd, "reproducir") as sonar, \
                mock.patch.object(preferencias_ia_lista, "anunciar") as anunciar:
            yield crear, anunciar, sonar

    def test_p1_sigue_habilitado_mientras_actualiza(self):
        pagina = self._dialogo().pagina_ia
        with self._red(pagina):
            self._disparar(pagina.btn_ia_actualizar)
        self.assertTrue(pagina.btn_ia_actualizar.IsEnabled())

    def test_p2_lleva_el_motivo_mientras_actualiza(self):
        pagina = self._dialogo().pagina_ia
        boton = pagina.btn_ia_actualizar
        self.assertEqual(boton.GetLabel(), BASE_ACTUALIZAR)
        with self._red(pagina):
            self._disparar(boton)
        self.assertEqual(boton.GetLabel(), ACTUALIZANDO)

    def test_p3_activar_mientras_actualiza_anuncia_y_no_repite(self):
        pagina = self._dialogo().pagina_ia
        with self._red(pagina) as (crear, anunciar, _sonar):
            self._disparar(pagina.btn_ia_actualizar)
            self._disparar(pagina.btn_ia_actualizar)
        self.assertEqual(crear.call_count, 1)
        anunciar.assert_any_call("Actualizando la lista de modelos.")

    def _etiqueta_mientras_actualiza(self, pagina, descargar):
        etiquetas = []

        def descargar_anotando(*argumentos):
            etiquetas.append(pagina.btn_ia_actualizar.GetLabel())
            return descargar(*argumentos)

        with self._red(pagina, descargar=descargar_anotando, correr=True):
            self._disparar(pagina.btn_ia_actualizar)
        return etiquetas

    def test_p4_vuelve_a_la_base_con_exito(self):
        pagina = self._dialogo().pagina_ia
        etiquetas = self._etiqueta_mientras_actualiza(
            pagina, lambda *_argumentos: _catalogo_de_prueba())
        self.assertEqual(etiquetas, [ACTUALIZANDO])
        self.assertEqual(pagina.btn_ia_actualizar.GetLabel(), BASE_ACTUALIZAR)
        self.assertTrue(pagina.btn_ia_actualizar.IsEnabled())

    def test_p4_vuelve_a_la_base_con_error(self):
        pagina = self._dialogo().pagina_ia

        def descargar(*_argumentos):
            raise OSError("sin red")

        etiquetas = self._etiqueta_mientras_actualiza(pagina, descargar)
        self.assertEqual(etiquetas, [ACTUALIZANDO])
        self.assertEqual(pagina.btn_ia_actualizar.GetLabel(), BASE_ACTUALIZAR)
        self.assertTrue(pagina.btn_ia_actualizar.IsEnabled())


if __name__ == "__main__":
    unittest.main()
