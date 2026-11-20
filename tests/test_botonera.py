# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""La botonera común de las listas con acciones.

Abre ventanas.
"""

import ast
import unittest
from pathlib import Path
from unittest import mock

import wx

from guyrapu.ui import botonera
from guyrapu.ui.lista_pura import Accion
from tests.ventanas_prueba import app_de_prueba, destruir

PAGINAS = (
    "comandos_ventana.py", "disparadores_ventana.py", "encuestas_ventana.py",
    "estilos_ventana.py", "medios_ventana.py",
    "mensajes_automaticos_ventana.py", "metas_ventana.py",
    "palabras_bloqueadas_ventana.py", "preguntas_ventana.py",
    "obs_pagina_perfiles.py",
)


def _usa_botonera(ruta):
    arbol = ast.parse(ruta.read_text(encoding="utf-8"))
    for nodo in ast.walk(arbol):
        if not isinstance(nodo, ast.ImportFrom):
            continue
        if nodo.module == "guyrapu.ui.botonera":
            return True
        if nodo.module == "guyrapu.ui" and any(
                nombre.name == "botonera" for nombre in nodo.names):
            return True
    return False


class TestBotonera(unittest.TestCase):

    def setUp(self):
        self.app = app_de_prueba()
        self.marco = wx.Frame(None)
        self.addCleanup(destruir, self.marco)
        self.panel = wx.Panel(self.marco)
        self.addCleanup(destruir, self.panel)

    def _medir(self, fila, ancho=360):
        contenido = wx.BoxSizer(wx.VERTICAL)
        contenido.Add(fila, 0, wx.EXPAND)
        self.panel.SetSizer(contenido)
        exterior = wx.BoxSizer(wx.VERTICAL)
        exterior.Add(self.panel, 1, wx.EXPAND)
        self.marco.SetSizer(exterior)
        self.marco.SetClientSize((ancho, 300))
        self.marco.Show()
        self.addCleanup(self.marco.Hide)
        self.marco.SendSizeEvent()
        self.marco.Layout()

    def test_los_botones_son_iguales_y_forman_columnas(self):
        etiquetas = ["A", "BBBB", "CC", "DDDDDDDD", "EEEEEE"]
        acciones = [Accion(str(indice), texto, lambda: None)
                    for indice, texto in enumerate(etiquetas)]
        fila = botonera.armar(self.panel, acciones, mock.Mock())
        self._medir(fila)
        botones = [hijo for hijo in self.panel.GetChildren()
                   if isinstance(hijo, wx.Button)]
        self.assertEqual(len(botones), len(etiquetas))
        anchos = {boton.GetSize().width for boton in botones}
        self.assertEqual(len(anchos), 1)
        self.assertGreaterEqual(anchos.pop(), 96)
        filas = {}
        for boton in botones:
            filas.setdefault(boton.GetPosition().y, []).append(boton)
        self.assertGreaterEqual(len(filas), 2)
        primeros = []
        for en_fila in sorted(filas.values(),
                              key=lambda fila: fila[0].GetPosition().y):
            en_fila.sort(key=lambda boton: boton.GetPosition().x)
            if primeros:
                self.assertEqual(en_fila[0].GetPosition().x,
                                 primeros[0].GetPosition().x)
                self.assertEqual(
                    en_fila[0].GetPosition().y - (
                        primeros[-1].GetPosition().y
                        + primeros[-1].GetSize().height), 8)
            else:
                self.assertGreaterEqual(len(en_fila), 2)
            for anterior, siguiente in zip(en_fila, en_fila[1:]):
                self.assertEqual(
                    siguiente.GetPosition().x - (
                        anterior.GetPosition().x
                        + anterior.GetSize().width), 8)
            primeros = en_fila

    def test_el_ancho_sigue_al_boton_mas_ancho(self):
        etiquetas = ["A", "Un texto bastante más largo que los demás", "BB"]
        acciones = [Accion(str(indice), texto, lambda: None)
                    for indice, texto in enumerate(etiquetas)]
        fila = botonera.armar(self.panel, acciones, mock.Mock())
        self._medir(fila)
        botones = [hijo for hijo in self.panel.GetChildren()
                   if isinstance(hijo, wx.Button)]
        self.assertEqual(len({boton.GetSize().width for boton in botones}), 1)
        self.assertGreater(botones[0].GetSize().width, 96)

    def test_las_diez_paginas_usan_la_botonera(self):
        raiz = Path(__file__).resolve().parent.parent
        for nombre in PAGINAS:
            self.assertTrue(
                _usa_botonera(raiz / "guyrapu" / "ui" / nombre),
                f"{nombre} no usa la botonera")


if __name__ == "__main__":
    unittest.main()
