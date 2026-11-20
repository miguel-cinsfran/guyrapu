# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""La posición del JSON sale del borde exterior del control, no del interior.

Un `wx.TextCtrl` con borde mide distinto por dentro y por fuera: usar
`ClientToScreen((0, 0))` corre el rectángulo unos píxeles y genera avisos
falsos de geometría. La galería tiene que usar `GetScreenPosition()`. Abre
una ventana de verdad: se corre en la PC donde no está el dueño.
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

    def test_textctrl_con_borde_parte_en_el_borde(self):
        import wx

        class Campo(wx.TextCtrl):
            # El interior del control con borde está corrido dos píxeles.
            def ClientToScreen(self, punto):
                interior = super().ClientToScreen(punto)
                return wx.Point(interior.x + 2, interior.y + 2)

        app_de_prueba()
        marco = wx.Dialog(None, id=900, title="Galería", size=(320, 200))
        try:
            panel = wx.Panel(marco, id=901)
            campo = Campo(panel, id=902, pos=(16, 38), size=(200, 23),
                          style=wx.BORDER_SIMPLE)
            marco.ShowWithoutActivating()
            wx.SafeYield()
            with tempfile.TemporaryDirectory() as base:
                contenido = galeria._escribir_json(
                    marco, Path(base) / "captura.json", "muestra", "clase",
                    "normal", None, "captura.png", 320, 200)
            por_id = {c["id"]: c for c in contenido["controles"]}
            self.assertEqual(len(por_id), 3)
            rect = por_id[campo.GetId()]["rect"]
            self.assertEqual(rect[0], 16)
            self.assertEqual(rect[1], 38)
            self.assertEqual(rect[2], campo.GetSize().GetWidth())
        finally:
            destruir(marco)


if __name__ == "__main__":
    unittest.main()
