# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""El resumen de la sonda cuenta los focos de su ventana y de nadie más."""

import importlib.util
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


if __name__ == "__main__":
    unittest.main()
