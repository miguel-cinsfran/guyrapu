# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas del Aceptar de los cuadros de escena sin opciones."""

import unittest
from unittest import mock

import wx

from guyrapu.ui import escena_captura_ventana, escena_propiedades
from tests.ventanas_prueba import app_de_prueba, destruir

VACIO_VENTANA = "No hay ventanas para capturar."
VACIO_PANTALLA = "No hay pantallas para capturar."


class TestAceptarDeLosCuadrosDeEscena(unittest.TestCase):

    def setUp(self):
        self.app = app_de_prueba()
        self.anuncios = []
        for modulo in (escena_captura_ventana, escena_propiedades):
            parche = mock.patch.object(modulo, "anunciar",
                                       self.anuncios.append)
            parche.start()
            self.addCleanup(parche.stop)

    def _capturar_ventana(self, opciones):
        dialogo = escena_captura_ventana.DialogoCapturarVentana(
            None, opciones, "")
        self.addCleanup(destruir, dialogo)
        return dialogo

    def _eleccion(self, opciones):
        dialogo = escena_propiedades.DialogoEleccion(
            None, "Captura de pantalla", "DialogoPantalla", "&Pantalla:",
            opciones, "", VACIO_PANTALLA)
        self.addCleanup(destruir, dialogo)
        return dialogo

    def _juego(self, ventanas, modo="window"):
        dialogo = escena_propiedades.DialogoJuego(
            None, ventanas, {"modo": modo})
        self.addCleanup(destruir, dialogo)
        return dialogo

    def _aceptar(self, dialogo):
        dialogo.EndModal = mock.Mock()
        dialogo._al_aceptar(None)
        return dialogo.EndModal

    def test_aceptar_sigue_habilitado_sin_opciones_en_los_tres_cuadros(self):
        self.assertTrue(self._capturar_ventana(()).btn_aceptar.IsEnabled())
        self.assertTrue(self._eleccion(()).btn_aceptar.IsEnabled())
        self.assertTrue(self._juego(()).btn_aceptar.IsEnabled())

    def test_sin_opciones_la_etiqueta_lleva_el_motivo(self):
        capturar = self._capturar_ventana(())
        self.assertEqual(capturar.btn_aceptar.GetLabel(),
                         "&Aceptar (no hay ventanas para capturar)")
        self.assertEqual(capturar.btn_aceptar.GetName(), "Aceptar")
        eleccion = self._eleccion(())
        self.assertEqual(eleccion.btn_aceptar.GetLabel(),
                         "&Aceptar (no hay pantallas para capturar)")
        self.assertEqual(eleccion.btn_aceptar.GetName(), "Aceptar")
        juego = self._juego(())
        self.assertEqual(juego.btn_aceptar.GetLabel(),
                         "&Aceptar (no hay ventanas para capturar)")
        self.assertEqual(juego.btn_aceptar.GetName(), "Aceptar")

    def test_con_opciones_la_etiqueta_es_la_base(self):
        self.assertEqual(
            self._capturar_ventana((("Champions", "champions"),))
            .btn_aceptar.GetLabel(), "&Aceptar")
        self.assertEqual(
            self._eleccion((("HP", "hp"),)).btn_aceptar.GetLabel(),
            "&Aceptar")
        self.assertEqual(
            self._juego((("Champions", "champions"),))
            .btn_aceptar.GetLabel(), "&Aceptar")

    def test_el_cuadro_de_juego_solo_lleva_el_motivo_en_la_ventana(self):
        dialogo = self._juego((), modo="any_fullscreen")
        self.assertEqual(dialogo.btn_aceptar.GetLabel(), "&Aceptar")
        dialogo.cho_modo.SetSelection(1)
        dialogo.cho_modo.GetEventHandler().ProcessEvent(
            wx.CommandEvent(wx.EVT_CHOICE.typeId, dialogo.cho_modo.GetId()))
        self.assertEqual(dialogo.btn_aceptar.GetLabel(),
                         "&Aceptar (no hay ventanas para capturar)")
        dialogo.cho_modo.SetSelection(0)
        dialogo.cho_modo.GetEventHandler().ProcessEvent(
            wx.CommandEvent(wx.EVT_CHOICE.typeId, dialogo.cho_modo.GetId()))
        self.assertEqual(dialogo.btn_aceptar.GetLabel(), "&Aceptar")

    def test_aceptar_sin_opciones_anuncia_el_vacio_y_no_cierra(self):
        fin = self._aceptar(self._capturar_ventana(()))
        fin.assert_not_called()
        fin = self._aceptar(self._eleccion(()))
        fin.assert_not_called()
        fin = self._aceptar(self._juego(()))
        fin.assert_not_called()
        self.assertEqual(
            self.anuncios,
            [VACIO_VENTANA, VACIO_PANTALLA, VACIO_VENTANA])

    def test_con_opciones_aceptar_hace_lo_de_hoy(self):
        capturar = self._capturar_ventana((("Champions", "champions"),))
        capturar.cho_ventana.SetSelection(0)
        fin = self._aceptar(capturar)
        fin.assert_called_once_with(wx.ID_OK)

        eleccion = self._eleccion((("HP", "hp"),))
        fin = self._aceptar(eleccion)
        fin.assert_called_once_with(wx.ID_OK)
        self.assertEqual(eleccion.valor(), "hp")

        juego = self._juego((("Champions", "champions"),))
        juego.cho_ventana.SetSelection(0)
        fin = self._aceptar(juego)
        fin.assert_called_once_with(wx.ID_OK)
        self.assertEqual(juego.valor(),
                         {"modo": "window", "ventana": "champions"})

        libre = self._juego((), modo="any_fullscreen")
        fin = self._aceptar(libre)
        fin.assert_called_once_with(wx.ID_OK)
        self.assertEqual(libre.valor(),
                         {"modo": "any_fullscreen", "ventana": ""})
