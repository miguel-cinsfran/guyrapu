# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de la búsqueda y el primer plano de la ventana de OBS."""

import unittest

import wx

from tests.pseudo_prueba import con_pseudo
from tests.ventanas_prueba import app_de_prueba, destruir
from guyrapu.core.idioma import _
from guyrapu.obs import obs_ventana
from guyrapu.ui import obs_pagina_general


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
                _(obs_ventana.TEXTO_SIN_OBS),
                _(obs_ventana.TEXTO_SIN_FRENTE),
            ]
        for texto in marcados:
            with self.subTest(texto=texto):
                self.assertTrue(texto.startswith("[¡"), texto)


class TestBuscarVentanaReal(unittest.TestCase):

    def test_buscar_ventana_no_lanza_y_da_none_o_entero(self):
        resultado = obs_ventana.buscar_ventana()
        self.assertTrue(resultado is None or isinstance(resultado, int))


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


if __name__ == "__main__":
    unittest.main()
