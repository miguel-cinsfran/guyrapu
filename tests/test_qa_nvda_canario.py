# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de la ventana canario del carril con wx sustituido, sin ventanas.

El manejador de `EVT_SHOW` pide el primer plano con `traer_al_frente` antes
de enfocar el campo y anunciar. Si Windows no se lo da, lo escribe en la
salida de error y sigue con el foco y el anuncio.
"""

import contextlib
import io
import os
import sys
import types
import unittest
from unittest import mock

from qa import foco_ventanas
from qa.nvda import canario

HWND = 987654


class _Evento:
    def IsShown(self):
        return True


def _wx_falso(registro):
    """Módulo `wx` mínimo que dispara el `EVT_SHOW` al mostrarse el marco."""
    evt_show = object()

    class App:
        def __init__(self, *args, **kwargs):
            pass

        def MainLoop(self):
            pass

    class Panel:
        def __init__(self, padre):
            pass

        def SetSizer(self, caja):
            pass

    class Sizer:
        def __init__(self, orientacion):
            pass

        def Add(self, *args, **kwargs):
            pass

    class Etiqueta:
        def __init__(self, panel, label=""):
            pass

    class Campo:
        def __init__(self, panel):
            pass

        def SetName(self, nombre):
            self.nombre = nombre

        def SetFocus(self):
            registro.append(("foco",))

    class Casilla:
        def __init__(self, panel, label=""):
            pass

    class Boton:
        def __init__(self, panel, label=""):
            pass

    class Marco:
        def __init__(self, padre, title=""):
            self._manejadores = {}

        def Bind(self, tipo, manejador):
            self._manejadores[tipo] = manejador

        def Show(self):
            self._manejadores[evt_show](_Evento())

        def GetHandle(self):
            return HWND

        def Fit(self):
            pass

        def Centre(self):
            pass

    return types.SimpleNamespace(
        App=App, Frame=Marco, Panel=Panel, BoxSizer=Sizer,
        StaticText=Etiqueta, TextCtrl=Campo, CheckBox=Casilla,
        Button=Boton, EVT_SHOW=evt_show, VERTICAL=1, ALL=2, EXPAND=4,
        LEFT=8, RIGHT=16)


class TestCanario(unittest.TestCase):

    def _mostrar(self, queda_al_frente):
        registro = []
        modulo_lector = types.ModuleType("guyrapu.voice.lector")

        class LectorFalso:
            def speak(self, texto, interrupt=False):
                registro.append(("habla", texto))

        modulo_lector.Lector = LectorFalso

        def frente_falso(hwnd, pid):
            registro.append(("frente", hwnd, pid))
            return queda_al_frente

        with (
            mock.patch.object(foco_ventanas, "traer_al_frente",
                              side_effect=frente_falso) as frente,
            mock.patch.dict(sys.modules, {
                "wx": _wx_falso(registro),
                "guyrapu.voice.lector": modulo_lector,
            }),
        ):
            error = io.StringIO()
            with contextlib.redirect_stderr(error):
                canario.main()
        return registro, frente, error.getvalue()

    def test_al_mostrarse_trae_al_frente_antes_del_foco_y_el_anuncio(self):
        registro, frente, _ = self._mostrar(True)
        self.assertEqual(registro, [
            ("frente", HWND, os.getpid()),
            ("foco",),
            ("habla", canario.ANUNCIO),
        ])
        frente.assert_called_once_with(HWND, os.getpid())

    def test_si_no_queda_al_frente_lo_escribe_y_sigue(self):
        registro, _, error = self._mostrar(False)
        lineas = error.strip().splitlines()
        self.assertEqual(len(lineas), 1)
        self.assertIn("Windows no le dio el primer plano", lineas[0])
        self.assertEqual(registro[-2:],
                         [("foco",), ("habla", canario.ANUNCIO)])
