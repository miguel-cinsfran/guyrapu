# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""La posición del JSON sale del borde exterior del control, no del interior.

Un `wx.TextCtrl` con borde mide distinto por dentro y por fuera:
`GetScreenPosition()` toma el origen interior y genera avisos falsos de
geometría. La galería mide los controles desde la posición respecto del
padre y la ventana raíz desde el origen del área cliente. Abre una ventana
de verdad: se corre en la PC donde no está el dueño.
"""

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

from tests.ventanas_prueba import app_de_prueba, destruir

_QA = Path(__file__).resolve().parent.parent / "qa"
sys.path.insert(0, str(_QA))
_paquete = importlib.util.spec_from_file_location(
    "galeria_controles_prueba", _QA / "galeria.py")
galeria = importlib.util.module_from_spec(_paquete)
_paquete.loader.exec_module(galeria)


class TestPosicionBordeExterior(unittest.TestCase):

    def test_raiz_y_textctrl_desde_el_borde_exterior(self):
        import wx

        app_de_prueba()
        marco = wx.Dialog(None, id=900, title="Galería", size=(320, 200))
        try:
            panel = wx.Panel(marco, id=901, pos=(0, 0), size=(300, 180))
            sizer = wx.BoxSizer(wx.VERTICAL)
            panel.SetSizer(sizer)
            campo = wx.TextCtrl(panel, id=902, size=(200, 23))
            sizer.Add((0, 38))
            sizer.Add(campo, 0, wx.LEFT, 16)
            marco.ShowWithoutActivating()
            panel.Layout()
            wx.SafeYield()
            with tempfile.TemporaryDirectory() as base:
                contenido = galeria._escribir_json(
                    marco, Path(base) / "captura.json", "muestra", "clase",
                    "normal", None, "captura.png")
            controles = contenido["controles"]
            self.assertEqual(controles[0]["id"], marco.GetId())
            self.assertEqual(controles[0]["rect"], [0, 0, *marco.GetSize()])
            campo_control = next(c for c in controles
                                 if c["id"] == campo.GetId())
            self.assertEqual(campo.GetPosition().x, 16)
            self.assertEqual(campo_control["rect"][0], 16)
            self.assertEqual(campo_control["rect"][1], 38)
        finally:
            destruir(marco)


if __name__ == "__main__":
    unittest.main()
