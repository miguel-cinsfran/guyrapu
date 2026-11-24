# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pseudotraducción de la sección de clave de IA de Preferencias.

Abre ventanas.
Construye la sección sobre un panel propio con la pseudotraducción y
exige que no deje ningún texto visible sin envolver.
"""

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import wx

from guyrapu.ai import catalogo
from guyrapu.ui import preferencias_ia
from guyrapu.ui import preferencias_ia_clave
from guyrapu.ui.preferencias_ia_clave import SeccionClaveIA
from guyrapu.voice import motores
from tests.pseudo_prueba import con_pseudo, textos_sin_marcar
from tests.rutas_temporales import redirigir_rutas
from tests.ventanas_prueba import app_de_prueba, armar_preferencias, destruir


class TestPseudoClaveIA(unittest.TestCase):
    def setUp(self):
        self.app = app_de_prueba()

    def test_no_queda_ningun_texto_visible_sin_envolver(self):
        proveedor = SimpleNamespace(id="gemini", nombre="Gemini")
        # Nunca el Administrador de credenciales real.
        with mock.patch.object(preferencias_ia_clave.claves, "leer",
                               return_value=""):
            with con_pseudo():
                marco = wx.Frame(None)
                self.addCleanup(destruir, marco)
                panel = wx.Panel(marco)
                sizer = wx.BoxSizer(wx.VERTICAL)
                seccion = SeccionClaveIA(lambda: proveedor, lambda: None)
                seccion.construir(panel, sizer)
                panel.SetSizer(sizer)
                sin_marcar = textos_sin_marcar(panel)

        self.assertEqual([], sin_marcar)

    def test_la_clave_esta_a_cuatro_pixeles_de_su_rotulo(self):
        proveedor = SimpleNamespace(id="gemini", nombre="Gemini")
        clave = "AIza" + "a" * 35
        with mock.patch.object(preferencias_ia_clave.claves, "leer",
                               return_value=clave):
            marco = wx.Frame(None)
            self.addCleanup(destruir, marco)
            panel = wx.Panel(marco)
            sizer = wx.BoxSizer(wx.VERTICAL)
            seccion = SeccionClaveIA(lambda: proveedor, lambda: None)
            seccion.construir(panel, sizer)
            panel.SetSizer(sizer)
            panel.Layout()
            campo = seccion.txt_estado
            etiqueta = [h for h in panel.GetChildren()
                        if isinstance(h, wx.StaticText)
                        and h.GetLabel() == "Cla&ve:"][0]
            separacion = campo.GetPosition().y - (
                etiqueta.GetPosition().y + etiqueta.GetSize().GetHeight())

        self.assertEqual(separacion, 4)

    def test_el_campo_de_clave_esta_a_cuatro_pixeles_de_su_rotulo(self):
        proveedor = SimpleNamespace(id="gemini", nombre="Gemini")
        with mock.patch.object(preferencias_ia_clave.claves, "leer",
                               return_value=""):
            marco = wx.Frame(None)
            self.addCleanup(destruir, marco)
            panel = wx.Panel(marco)
            sizer = wx.BoxSizer(wx.VERTICAL)
            seccion = SeccionClaveIA(lambda: proveedor, lambda: None)
            seccion.construir(panel, sizer)
            panel.SetSizer(sizer)
            panel.Layout()
            campo = seccion.txt_clave
            etiqueta = [h for h in panel.GetChildren()
                        if isinstance(h, wx.StaticText)
                        and h.GetLabel() == "Cla&ve:"][0]
            separacion = campo.GetPosition().y - (
                etiqueta.GetPosition().y + etiqueta.GetSize().GetHeight())

        self.assertEqual(separacion, 4)


class TestBotonesDeLaClave(unittest.TestCase):
    """Guardar y Comprobar comparten fila sin estirarse."""

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
        catalogo_vacio = mock.patch.object(
            preferencias_ia.catalogo, "cargar",
            return_value={"version": catalogo.VERSION, "fecha": None,
                          "proveedores": {}})
        catalogo_vacio.start()
        self.addCleanup(catalogo_vacio.stop)

    def test_comprobar_clave_va_a_su_ancho_natural(self):
        with mock.patch.object(motores, "listar_voces",
                               return_value=["Voz de prueba"]):
            dialogo = armar_preferencias({}, "Inteligencia artificial")
        self.addCleanup(destruir, dialogo)
        boton = dialogo.pagina_ia.btn_ia_probar_clave
        self.assertEqual(boton.GetSize().width, boton.GetBestSize().width)


if __name__ == "__main__":
    unittest.main()
