# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de la fuente común de las listas."""

import unittest

import wx

from guyrapu.ui import tema
from tests.ventanas_prueba import app_de_prueba


class TestFuenteDeLista(unittest.TestCase):

    def setUp(self):
        self.app = app_de_prueba()

    def test_la_fuente_tiene_el_tamanio_y_la_familia_de_la_interfaz(self):
        fuente = tema.fuente_de_lista(16)
        de_interfaz = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        self.assertEqual(fuente.GetPointSize(), 16)
        self.assertEqual(fuente.GetFaceName(), de_interfaz.GetFaceName())
