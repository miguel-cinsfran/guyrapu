# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de la lógica pura de qa/ventana_de_prueba.py, sin ventanas."""

import importlib.util
import tempfile
import unittest
from pathlib import Path

_RUTA = Path(__file__).resolve().parent.parent / "qa" / "ventana_de_prueba.py"
_espec = importlib.util.spec_from_file_location(
    "ventana_de_prueba_qa", _RUTA)
ventana_de_prueba = importlib.util.module_from_spec(_espec)
_espec.loader.exec_module(ventana_de_prueba)


class TestNumeroDeArchivo(unittest.TestCase):

    def test_lee_archivo_con_salto_de_linea(self):
        with tempfile.TemporaryDirectory() as tmp:
            ruta = Path(tmp) / "numero.txt"
            ruta.write_text("4826\n", encoding="utf-8")
            self.assertEqual(
                ventana_de_prueba.numero_de_archivo(str(ruta)), "4826")

    def test_archivo_inexistente_da_vacio(self):
        with tempfile.TemporaryDirectory() as tmp:
            ruta = Path(tmp) / "no-está.txt"
            self.assertEqual(ventana_de_prueba.numero_de_archivo(str(ruta)), "")

    def test_ruta_vacia_da_vacio(self):
        self.assertEqual(ventana_de_prueba.numero_de_archivo(""), "")
