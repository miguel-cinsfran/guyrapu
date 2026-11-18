# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""El resumen de la sonda cuenta los focos de su ventana y de nadie más."""

import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path

_RUTA = (Path(__file__).resolve().parent.parent / "qa"
         / "sonda_foco_listas.py")
_paquete = importlib.util.spec_from_file_location(
    "sonda_foco_listas_qa", _RUTA)
sonda = importlib.util.module_from_spec(_paquete)
_paquete.loader.exec_module(sonda)


class TestResumen(unittest.TestCase):

    def test_cuenta_los_focos_por_entrada_y_omite_las_otras_ventanas(self):
        eventos = [
            {"ms": 10, "evento": "FOCUS", "ventana": 100,
             "control": "ListBox", "id_hijo": 1, "nombre": "primera"},
            {"ms": 20, "evento": "FOCUS", "ventana": 100,
             "control": "ListBox", "id_hijo": 1, "nombre": "primera"},
            {"ms": 30, "evento": "FOCUS", "ventana": 100,
             "control": "ListBox", "id_hijo": 2, "nombre": "segunda"},
            {"ms": 40, "evento": "SELECTION", "ventana": 100,
             "control": "ListBox", "id_hijo": 2, "nombre": "segunda"},
            {"ms": 50, "evento": "FOCUS", "ventana": 200,
             "control": "ListBox", "id_hijo": 1, "nombre": "primera"},
        ]

        self.assertEqual(
            sonda.resumen(eventos, 100),
            ["ListBox: primera entrada 2 focos, segunda 1"])


class TestRutaDeLaRaiz(unittest.TestCase):

    def test_importa_guyrapu_con_el_interprete_aislado(self):
        codigo = (
            "import importlib.util\n"
            f"ruta = {str(_RUTA)!r}\n"
            "espec = importlib.util.spec_from_file_location('sonda_qa', ruta)\n"
            "modulo = importlib.util.module_from_spec(espec)\n"
            "espec.loader.exec_module(modulo)\n"
            "from guyrapu.ui import accesibilidad\n"
            "print(accesibilidad.__name__)\n")
        resultado = subprocess.run(
            [sys.executable, "-I", "-c", codigo],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace")
        self.assertEqual(resultado.returncode, 0, resultado.stderr)
        self.assertIn("guyrapu.ui.accesibilidad", resultado.stdout)


if __name__ == "__main__":
    unittest.main()
