# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de la página Cola de lectura del diálogo de Preferencias.

Abren ventanas.
"""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from guyrapu.core import config
from guyrapu.ui import gui
from guyrapu.voice import motores
from tests.rutas_temporales import redirigir_rutas
from tests.ventanas_prueba import (app_de_prueba, armar_preferencias, destruir,
                                   pagina_por_titulo)


class TestUmbralEnSizer(unittest.TestCase):
    """El contador va en el sizer de la página, con los mismos márgenes
    que el tamaño máximo de la cola.

    Abren ventanas.
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

    def _dialogo(self, configuracion=None):
        with mock.patch.object(motores, "listar_voces",
                               return_value=["Voz de prueba"]):
            dialogo = armar_preferencias(configuracion or {}, "Cola de lectura")
        self.addCleanup(destruir, dialogo)
        return dialogo

    def _pagina_cola(self, dialogo):
        return pagina_por_titulo(dialogo, "Cola de lectura")

    def _contenido(self, pagina):
        return pagina.GetSizer().GetChildren()[0].GetSizer()

    def test_contador_esta_en_el_sizer_de_la_pagina(self):
        dialogo = self._dialogo()
        pagina = self._pagina_cola(dialogo)
        self.assertIs(dialogo.sp_umbral_nombre.GetContainingSizer(),
                      self._contenido(pagina))

    def test_contador_con_los_mismos_margenes_que_tamanio_maximo(self):
        dialogo = self._dialogo()
        pagina = self._pagina_cola(dialogo)
        items = {it.GetWindow(): it
                 for it in self._contenido(pagina).GetChildren()}
        for control in (dialogo.sp_cola_maxima, dialogo.sp_umbral_nombre):
            with self.subTest(control=control.GetName()):
                item = items[control]
                self.assertEqual(item.GetBorder(), 4)
                self.assertTrue(item.GetFlag() & gui.wx.TOP)


if __name__ == "__main__":
    unittest.main()
