# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Guardiana: ninguna prueba deja ventanas de primer nivel pendientes.

Crea y destruye con `destruir` 10 `PreferenciasDialog` y exige que la
cuenta de objetos USER del proceso no crezca (medido: sin `SafeYield`
cada diálogo dejaba unos 235 ocupados hasta cortar Windows en 10.000).
Abren ventanas.
"""

import gc
import sys
import unittest
from pathlib import Path
from unittest import mock

try:
    import wx
    from guyrapu.ui import gui_preferencias
    from guyrapu.voice import motores
    _HAY_WX = True
except Exception:
    _HAY_WX = False

from tests.rutas_temporales import redirigir_rutas
from tests.ventanas_prueba import (app_de_prueba, armar_preferencias,
                                   destruir, pagina_por_titulo)

_SOLO_WINDOWS = _HAY_WX and sys.platform == "win32"

_TITULO_GENERICO = "Ventana genérica sin fugas"


def _objetos_usuario():
    """Objetos USER del proceso actual (`GetGuiResources`, bandera 1)."""
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.WinDLL("user32")
    user32.GetGuiResources.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    user32.GetGuiResources.restype = wintypes.DWORD
    return user32.GetGuiResources(-1, 1)


@unittest.skipUnless(_SOLO_WINDOWS, "solo Windows con wxPython")
class TestVentanasSinFugas(unittest.TestCase):

    def setUp(self):
        self.app = app_de_prueba()
        self.ruta = Path.cwd()
        self.parche_ruta = redirigir_rutas(self.ruta)
        self.parche_ruta.__enter__()
        self.addCleanup(self.parche_ruta.__exit__, None, None, None)

    def _dialogo(self):
        return armar_preferencias({})

    def _dialogo_generico(self):
        dialogo = wx.Dialog(None, title=_TITULO_GENERICO)
        panel = wx.Panel(dialogo)
        wx.Button(panel, label="Aceptar")
        wx.StaticText(panel, label="Texto de prueba")
        return dialogo

    def test_diez_dialogos_no_acumulan_objetos_ni_quedan_vivos(self):
        with mock.patch.object(motores, "listar_voces",
                               return_value=["Voz de prueba"]):
            destruir(self._dialogo())
            base = _objetos_usuario()
            for _ in range(9):
                destruir(self._dialogo())
            final = _objetos_usuario()
        self.assertLessEqual(final, base + 300)
        vivos = [ventana for ventana in wx.GetTopLevelWindows()
                 if isinstance(ventana, gui_preferencias.PreferenciasDialog)]
        self.assertEqual(vivos, [])

    def test_ventana_generica_no_deja_fugas_ni_queda_viva(self):
        destruir(self._dialogo_generico())
        base = _objetos_usuario()
        for _ in range(59):
            destruir(self._dialogo_generico())
        final = _objetos_usuario()
        self.assertLessEqual(final, base + 300)
        vivos = [ventana for ventana in wx.GetTopLevelWindows()
                 if ventana.GetTitle() == _TITULO_GENERICO]
        self.assertEqual(vivos, [])

    def test_app_de_prueba_se_reutiliza_y_sigue_vivo(self):
        app = app_de_prueba()
        self.assertIs(app_de_prueba(), app)
        identidad = id(app)
        del app
        gc.collect()
        vivo = wx.App.Get()
        self.assertIsNotNone(vivo)
        self.assertEqual(id(vivo), identidad)


@unittest.skipUnless(_SOLO_WINDOWS, "solo Windows con wxPython")
class TestAyudaDePreferencias(unittest.TestCase):

    def setUp(self):
        self.app = app_de_prueba()
        self.ruta = Path.cwd()
        parche = redirigir_rutas(self.ruta)
        parche.__enter__()
        self.addCleanup(parche.__exit__, None, None, None)

    def _indice(self, dialogo, titulo):
        for i in range(dialogo.nb.GetPageCount()):
            if dialogo.nb.GetPageText(i) == titulo:
                return i
        self.fail(f"No está la categoría {titulo}")

    def test_la_ayuda_construye_solo_las_paginas_pedidas(self):
        with mock.patch.object(motores, "listar_voces", return_value=[]):
            dialogo = armar_preferencias({}, "Cámara")
        self.addCleanup(destruir, dialogo)
        libro = dialogo._libro_perezoso
        self.assertTrue(libro.construida(self._indice(dialogo, "Cámara")))
        self.assertFalse(libro.construida(self._indice(dialogo, "Música")))

    def test_la_pagina_por_titulo_es_la_real_y_no_el_panel_vacio(self):
        with mock.patch.object(motores, "listar_voces", return_value=[]):
            dialogo = armar_preferencias({}, "Cámara")
        self.addCleanup(destruir, dialogo)
        pagina = pagina_por_titulo(dialogo, "Cámara")
        nombres = set()
        pendientes = list(pagina.GetChildren())
        while pendientes:
            actual = pendientes.pop()
            nombres.add(actual.GetName())
            pendientes.extend(actual.GetChildren())
        self.assertIn("Sonido de la guía", nombres)

    def test_un_titulo_que_no_existe_falla_con_su_nombre(self):
        titulo = "Categoría que no existe"
        with mock.patch.object(motores, "listar_voces", return_value=[]):
            with self.assertRaises(ValueError) as fallo:
                armar_preferencias({}, titulo)
        self.assertIn(titulo, str(fallo.exception))


if __name__ == "__main__":
    unittest.main()
