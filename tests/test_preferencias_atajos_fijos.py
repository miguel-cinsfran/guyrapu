# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Atajos fijos de la página Atajos de Preferencias.

Abren ventanas. Los botones de `cfg.ATAJOS_FIJOS` se alcanzan con Tab como
el resto, conservan su etiqueta con «(fija)» y, al activarlos, anuncian que
no se pueden cambiar sin empezar una captura.
"""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import wx

from guyrapu.core import config
from guyrapu.ui import preferencias_atajos
from guyrapu.voice import motores
from tests.rutas_temporales import redirigir_rutas
from tests.ventanas_prueba import app_de_prueba, armar_preferencias, destruir


ACCION_FIJA = "salir"
ACCION_EDITABLE = "rep_play"


class TestAtajosFijos(unittest.TestCase):

    def setUp(self):
        self.app = app_de_prueba()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.ruta = Path(self.tmp.name)
        (self.ruta / "config.ini").write_text(config._CONFIG_FALLBACK,
                                              encoding="utf-8")
        parche = redirigir_rutas(self.ruta)
        parche.__enter__()
        self.addCleanup(parche.__exit__, None, None, None)

    def _pagina(self):
        with mock.patch.object(motores, "listar_voces",
                               return_value=["Voz de prueba"]):
            dialogo = armar_preferencias({}, "Atajos")
        self.addCleanup(destruir, dialogo)
        return dialogo.pagina_atajos

    @staticmethod
    def _activar(boton):
        boton.GetEventHandler().ProcessEvent(
            wx.CommandEvent(wx.EVT_BUTTON.typeId, boton.GetId()))

    def test_p1_los_fijos_siguen_habilitados_y_en_el_recorrido(self):
        pagina = self._pagina()
        for accion in config.ATAJOS_FIJOS:
            boton = pagina._botones_atajo[accion]
            with self.subTest(accion=accion):
                self.assertTrue(boton.IsEnabled())
                self.assertTrue(boton.AcceptsFocusFromKeyboard())

    def test_p2_conservan_el_nombre_y_la_etiqueta_con_fija(self):
        pagina = self._pagina()
        for accion in config.ATAJOS_FIJOS:
            boton = pagina._botones_atajo[accion]
            with self.subTest(accion=accion):
                self.assertEqual(boton.GetName(), f"Atajo_{accion}")
                self.assertTrue(boton.GetLabel().endswith(" (fija)"))

    def test_p3_activar_anuncia_que_es_fijo_y_no_empieza_la_captura(self):
        pagina = self._pagina()
        boton = pagina._botones_atajo[ACCION_FIJA]
        etiqueta = boton.GetLabel()
        with mock.patch.object(preferencias_atajos, "anunciar") as anunciar:
            self._activar(boton)
        anunciar.assert_called_once_with("Este atajo es fijo.")
        self.assertIsNone(pagina._capturando_atajo)
        self.assertEqual(boton.GetLabel(), etiqueta)

    def test_p4_restablecer_no_cambia_los_fijos(self):
        pagina = self._pagina()
        boton = pagina._botones_atajo[ACCION_FIJA]
        etiqueta = boton.GetLabel()
        pagina._valores_atajo[ACCION_FIJA] = "alt+x"
        pagina._valores_atajo[ACCION_EDITABLE] = "ctrl+q"
        with mock.patch.object(preferencias_atajos, "anunciar"):
            pagina._restablecer_atajos(None)
        self.assertEqual(pagina._valores_atajo[ACCION_FIJA], "alt+x")
        self.assertEqual(boton.GetLabel(), etiqueta)
        self.assertTrue(boton.IsEnabled())
        self.assertEqual(pagina._valores_atajo[ACCION_EDITABLE], "ctrl+p")


if __name__ == "__main__":
    unittest.main()
