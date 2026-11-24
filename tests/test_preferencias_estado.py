# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de la página Estado (F2) del diálogo de Preferencias.

Abren ventanas.
"""

import unittest

import wx

from guyrapu.ui.preferencias_estado import PaginaEstado
from tests.ventanas_prueba import app_de_prueba, destruir


class TestGuardadoDeEstado(unittest.TestCase):
    """El dict que recibe la config en memoria solo conserva lo marcado.

    Abren ventanas.
    """

    def setUp(self):
        self.app = app_de_prueba()

    def test_guardar_copia_y_fija_solo_las_casillas_marcadas(self):
        marco = wx.Frame(None)
        self.addCleanup(destruir, marco)
        pagina = PaginaEstado(
            {"estado_toggles": ["estado", "titulo", "canal"]})
        pagina.construir(marco)

        pagina._chk_estado["estado"].SetValue(False)
        pagina._chk_estado["espectadores"].SetValue(True)

        fijados = {}
        en_memoria = {}
        pagina.guardar(
            lambda seccion, clave, valor: fijados.__setitem__(
                (seccion, clave), valor), en_memoria)

        self.assertEqual(en_memoria["estado_toggles"],
                         {"titulo", "canal", "espectadores"})
        for clave, valor in (("estado", "false"), ("titulo", "true"),
                             ("canal", "true"), ("espectadores", "true"),
                             ("musica", "false")):
            with self.subTest(clave=clave):
                self.assertEqual(fijados[("estado", clave)], valor)


if __name__ == "__main__":
    unittest.main()
