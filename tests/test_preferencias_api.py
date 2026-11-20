# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pseudotraducción de la página YouTube de Preferencias.

Abre ventanas.
Comprueba que ningún texto visible de la página queda sin pasar por
gettext.
"""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import wx

from guyrapu.core import config
from guyrapu.voice import motores
from tests.pseudo_prueba import con_pseudo, textos_sin_marcar
from tests.rutas_temporales import redirigir_rutas
from tests.ventanas_prueba import (app_de_prueba, armar_preferencias, destruir,
                                   pagina_por_titulo)


class TestApiSinTextosSinEnvolver(unittest.TestCase):
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

    def _dialogo(self, configuracion=None):
        with mock.patch.object(motores, "listar_voces",
                               return_value=["Voz de prueba"]):
            dialogo = armar_preferencias(configuracion or {}, "YouTube")
        self.addCleanup(destruir, dialogo)
        return dialogo

    def _pagina(self, dialogo):
        return pagina_por_titulo(dialogo, "YouTube")

    def test_no_queda_ningun_texto_visible_sin_envolver(self):
        with con_pseudo():
            dialogo = self._dialogo()
            sin_marcar = textos_sin_marcar(self._pagina(dialogo))

        self.assertEqual([], sin_marcar)


class TestDisenoDeLosCampos(unittest.TestCase):
    """Los tres campos con el rótulo encima y a lo ancho de la página.

    Abre ventanas.
    """

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

    def _dialogo(self):
        with mock.patch.object(motores, "listar_voces",
                               return_value=["Voz de prueba"]):
            dialogo = armar_preferencias({}, "YouTube")
        self.addCleanup(destruir, dialogo)
        return dialogo

    @staticmethod
    def _rotulo(pagina, texto):
        return next(hijo for hijo in pagina.GetChildren()
                    if isinstance(hijo, wx.StaticText)
                    and hijo.GetLabel().replace("&", "").rstrip(":") == texto)

    @staticmethod
    def _medir(pagina):
        pagina.SetSize((760, 900))
        pagina.Layout()

    def test_cada_rotulo_queda_encima_de_su_campo(self):
        dialogo = self._dialogo()
        panel = pagina_por_titulo(dialogo, "YouTube")
        pagina = dialogo.pagina_api
        self._medir(panel)
        for campo, texto in (
                (pagina.txt_api, "Clave de API"),
                (pagina.txt_cid, "ID de cliente OAuth"),
                (pagina.txt_secret, "Secreto de cliente OAuth")):
            with self.subTest(campo=campo.GetName()):
                rotulo = self._rotulo(panel, texto)
                self.assertEqual(rotulo.GetPosition().x, campo.GetPosition().x)
                self.assertLessEqual(
                    rotulo.GetPosition().y + rotulo.GetSize().height,
                    campo.GetPosition().y + 1)

    def test_los_campos_ocupan_el_ancho_de_la_pagina(self):
        dialogo = self._dialogo()
        panel = pagina_por_titulo(dialogo, "YouTube")
        pagina = dialogo.pagina_api
        self._medir(panel)
        ancho = panel.GetClientSize().width
        self.assertGreater(ancho, 100)
        for campo in (pagina.txt_api, pagina.txt_cid, pagina.txt_secret):
            with self.subTest(campo=campo.GetName()):
                self.assertEqual(campo.GetPosition().x, 10)
                self.assertEqual(ancho - (campo.GetPosition().x
                                           + campo.GetSize().width), 10)


if __name__ == "__main__":
    unittest.main()
