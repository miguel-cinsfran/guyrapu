# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pseudotraducción de la página Voces de Preferencias.

Abre ventanas.
Construye el diálogo de Preferencias con la pseudotraducción y exige que
la página no deje ningún texto visible sin envolver.
"""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from guyrapu.ui import gui_preferencias
from guyrapu.voice import motores
from guyrapu.voice import reproductor_pcm
from tests.pseudo_prueba import con_pseudo, textos_sin_marcar
from tests.rutas_temporales import redirigir_rutas
from tests.ventanas_prueba import app_de_prueba, destruir


# Textos que arma otro módulo y aparecen en la parte recorrida: no se
# tocan acá. Los nombres de los motores (`guyrapu/voice/motores.py`,
# NOMBRES) ya salen marcados porque la página los traduce. La lista de
# voces se finge vacía, así los combinados muestran el aviso propio, ya
# envuelto.
PENDIENTES_OTROS_MODULOS = ()


class TestPseudoVoz(unittest.TestCase):
    def setUp(self):
        self.app = app_de_prueba()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        parche = redirigir_rutas(Path(self.tmp.name))
        parche.__enter__()
        self.addCleanup(parche.__exit__, None, None, None)

    def _dialogo(self):
        # Los nombres de las salidas de audio los pone Windows y no se
        # traducen: se finge la lista vacía para mirar solo los textos propios.
        with mock.patch.object(motores, "listar_voces", return_value=[]), \
                mock.patch.object(reproductor_pcm, "listar_salidas",
                                  return_value=[]):
            dialogo = gui_preferencias.PreferenciasDialog(None, {})
        self.addCleanup(destruir, dialogo)
        return dialogo

    def test_no_queda_ningun_texto_visible_sin_envolver(self):
        with con_pseudo():
            dialogo = self._dialogo()
            pagina = next(p for p in dialogo._paginas()
                          if p.GetName() == "PagVoz")
            sin_marcar = textos_sin_marcar(pagina)

        self.assertEqual(sorted(sin_marcar),
                         sorted(PENDIENTES_OTROS_MODULOS))


class TestSalidaDeVoz(unittest.TestCase):
    def setUp(self):
        self.app = app_de_prueba()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        parche = redirigir_rutas(Path(self.tmp.name))
        parche.__enter__()
        self.addCleanup(parche.__exit__, None, None, None)

    def _dialogo(self, configuracion, salidas):
        with mock.patch.object(motores, "listar_voces",
                               return_value=["Voz A"]), \
                mock.patch.object(reproductor_pcm, "listar_salidas",
                                  return_value=salidas):
            dialogo = gui_preferencias.PreferenciasDialog(None, configuracion)
        self.addCleanup(destruir, dialogo)
        return dialogo

    def test_la_salida_predeterminada_va_primero_y_el_rotulo_dice_el_alcance(self):
        dialogo = self._dialogo({}, ["Altavoces"])
        cho = dialogo.pagina_voz.cho_salida_voz
        self.assertEqual([cho.GetString(i) for i in range(cho.GetCount())],
                         ["Salida predeterminada", "Altavoces"])
        self.assertEqual(cho.GetSelection(), 0)
        self.assertTrue(cho.IsEnabled())
        self.assertEqual(cho.GetName(),
                         "Salida de audio de la voz (Phonon y Piper)")
        etiquetas = [h.GetLabel() for h in
                     dialogo.pagina_voz._pag_voz_panel.GetChildren()]
        self.assertIn("Salida de audio de la voz (P&honon y Piper):",
                      etiquetas)

    def test_la_salida_guardada_ausente_se_conserva(self):
        dialogo = self._dialogo({"salida_voz": "Salida vieja"}, ["Altavoces"])
        cho = dialogo.pagina_voz.cho_salida_voz
        self.assertEqual([cho.GetString(i) for i in range(cho.GetCount())],
                         ["Salida predeterminada", "Altavoces",
                          "Salida vieja"])
        self.assertEqual(cho.GetStringSelection(), "Salida vieja")


if __name__ == "__main__":
    unittest.main()
