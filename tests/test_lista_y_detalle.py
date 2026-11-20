# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""La regla de lista que elige, búsqueda y lista de elementos, en dos ventanas.

Abren ventanas: quedan escritas para correrlas después. Toda ventana de
primer nivel se libera con `tests/ventanas_prueba.destruir`.
"""

import contextlib
import unittest
from unittest import mock

from guyrapu.core import idioma
from guyrapu.ui import musica_ventana, voces_ventana
from tests.test_musica_ventana import ControlFalso
from tests.test_voces_ventana import (
    HiloInmediato, _Instalados, _catalogo)
from tests.ventanas_prueba import app_de_prueba, destruir

try:
    import wx
except Exception:
    wx = None


class _Tecla:
    def __init__(self, codigo):
        self.codigo = codigo

    def GetKeyCode(self):
        return self.codigo

    def Skip(self):
        pass


def _en_orden(hijos, controles):
    indices = [next(i for i, hijo in enumerate(hijos) if hijo is control)
               for control in controles]
    return indices == sorted(indices)


class TestListaQueElige(unittest.TestCase):

    def setUp(self):
        self.app = app_de_prueba()
        self.pila = contextlib.ExitStack()
        self.addCleanup(self.pila.close)
        idioma.instalar("es")
        self.addCleanup(idioma._reiniciar)

    def _musica(self):
        ventana = musica_ventana.VentanaMusica(None, ControlFalso())
        self.addCleanup(destruir, ventana)
        return ventana

    def _voces(self):
        self.pila.enter_context(mock.patch.object(
            voces_ventana.paquetes_instalacion, "instalados", _Instalados([])))
        self.pila.enter_context(mock.patch.object(
            voces_ventana.red, "pedir_texto",
            mock.Mock(return_value=_catalogo())))
        self.pila.enter_context(mock.patch.object(
            voces_ventana.diagnostico, "crear_hilo", HiloInmediato))
        self.pila.enter_context(mock.patch.object(
            voces_ventana.wx, "CallAfter",
            lambda funcion, *args: funcion(*args)))
        self.pila.enter_context(mock.patch.object(
            voces_ventana.voces_disponibles, "idioma_actual", return_value="es"))
        self.pila.enter_context(mock.patch.object(
            voces_ventana.confirmar, "avisar", mock.Mock()))
        self.pila.enter_context(mock.patch.object(
            voces_ventana._snd, "reproducir", mock.Mock()))
        self.pila.enter_context(mock.patch.object(
            voces_ventana, "anunciar", mock.Mock()))
        ventana = voces_ventana.VentanaVoces(None)
        self.addCleanup(destruir, ventana)
        return ventana

    def _foco_tras_flecha_abajo(self, ventana, lista):
        ventana.Show()
        try:
            ventana.txt_buscar.SetFocus()
            ventana._tecla_buscar(_Tecla(wx.WXK_DOWN))
            self.assertIs(wx.Window.FindFocus(), lista)
        finally:
            ventana.Hide()

    def test_musica_empieza_por_colecciones_busqueda_y_canciones(self):
        ventana = self._musica()
        self.assertTrue(_en_orden(
            ventana._panel.GetChildren(),
            (ventana.lb_colecciones, ventana.txt_buscar, ventana.lb_temas)))
        self._foco_tras_flecha_abajo(ventana, ventana.lb_temas)

    def test_voces_empieza_por_motor_busqueda_y_voces(self):
        ventana = self._voces()
        self.assertTrue(_en_orden(
            ventana.GetChildren(),
            (ventana.lista_motores, ventana.txt_buscar, ventana.lista_voces)))
        self._foco_tras_flecha_abajo(ventana, ventana.lista_voces)


if __name__ == "__main__":
    unittest.main()
