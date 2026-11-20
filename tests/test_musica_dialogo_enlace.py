# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas del cuadro de enlace de la música.

Abren ventanas.
"""

import unittest
from tests.ventanas_prueba import app_de_prueba

try:
    import wx
    from guyrapu.ui import musica_dialogo_enlace
    from guyrapu.ui import formulario, tema
    from tests.pseudo_prueba import con_pseudo, textos_sin_marcar
    from tests.ventanas_prueba import destruir
    _HAY_WX = True
except Exception:
    wx = None
    musica_dialogo_enlace = None
    _HAY_WX = False


@unittest.skipUnless(_HAY_WX, "wxPython no está instalado")
class TestDialogoEnlacePseudo(unittest.TestCase):
    """Ningún texto visible del cuadro sin pasar por gettext."""

    def setUp(self):
        self.app = app_de_prueba()
        self.dialogo = None

    def tearDown(self):
        if self.dialogo is not None:
            destruir(self.dialogo)

    def test_no_queda_ningun_texto_visible_sin_envolver(self):
        with con_pseudo():
            self.dialogo = musica_dialogo_enlace.DialogoEnlace(None)
            sin_marcar = textos_sin_marcar(self.dialogo)
        self.assertEqual([], sin_marcar)


@unittest.skipUnless(_HAY_WX, "wxPython no está instalado")
class TestDisenioComun(unittest.TestCase):

    def setUp(self):
        self.app = app_de_prueba()

    def test_geometria_del_cuadro(self):
        cuadro = musica_dialogo_enlace.DialogoEnlace(None)
        self.addCleanup(destruir, cuadro)
        ancho, alto = cuadro.GetSize()
        self.assertGreaterEqual(ancho, formulario.ANCHO_MINIMO)
        self.assertLessEqual(alto, formulario.ALTO_MAXIMO)
        hijos = list(cuadro.txt_enlace.GetParent().GetChildren())
        indice = next(i for i, h in enumerate(hijos)
                      if isinstance(h, wx.StaticText) and h.GetLabel())
        rotulo, control = hijos[indice], hijos[indice + 1]
        self.assertEqual(
            rotulo.GetPosition().y + rotulo.GetSize().height,
            control.GetPosition().y - formulario.ETIQUETA_A_CONTROL)
        self.assertEqual(rotulo.GetPosition().x, control.GetPosition().x)
        cliente = cuadro.GetClientSize()
        botones = [cuadro.btn_ahora, cuadro.btn_continuacion,
                   cuadro.btn_cola, cuadro.btn_cancelar]
        self.assertEqual(len({b.GetPosition().y for b in botones}), 1)
        self.assertEqual(
            cliente.width - max(b.GetPosition().x + b.GetSize().width
                                for b in botones),
            formulario.MARGEN)
        self.assertEqual(
            cliente.height - (botones[0].GetPosition().y
                              + botones[0].GetSize().height),
            formulario.MARGEN)
        self.assertEqual(cuadro.btn_ahora.GetBackgroundColour(),
                         tema._T.primary)


if __name__ == "__main__":
    unittest.main()
