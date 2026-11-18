# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas del doble del lector y de la lista de ventanas de la aplicación.

No se abre ninguna ventana: se comprueba que cada anuncio se reenvíe al lector
real y al grabador de la sonda, que el inicializador deje ese doble donde
`anunciar` lo encuentra y que la lista de ventanas traiga lo que pide el
carril.
"""

import unittest
from unittest import mock

from guyrapu.ui import accesibilidad, gui
from qa.nvda import app, ventanas_app


class TestVentanas(unittest.TestCase):

    def test_la_lista_empieza_por_preferencias_y_la_ventana_interaccion(self):
        self.assertEqual(
            [entrada["nombre"] for entrada in ventanas_app.VENTANAS],
            ["preferencias", "interaccion"])
        for entrada in ventanas_app.VENTANAS:
            self.assertEqual(set(entrada),
                             {"nombre", "menu", "titulo", "primero"})
            self.assertTrue(all(entrada[clave] for clave in entrada))
        self.assertEqual(ventanas_app.VENTANAS[0]["titulo"], "Preferencias")
        self.assertEqual(ventanas_app.VENTANAS[0]["primero"], "General")
        self.assertEqual(ventanas_app.VENTANAS[1]["titulo"], "Interacción")


class TestDobleLector(unittest.TestCase):

    def test_pasa_la_misma_frase_al_lector_real_y_al_grabador(self):
        real = mock.Mock()
        grabador = mock.Mock()
        app.DobleLector(real, grabador).speak("Mensaje")
        real.speak.assert_called_once_with("Mensaje", interrupt=False)
        grabador.speak.assert_called_once_with("Mensaje", interrupt=False)

    def test_tambien_manda_el_braille_a_los_dos(self):
        real = mock.Mock()
        grabador = mock.Mock()
        app.DobleLector(real, grabador).braille("Mensaje")
        real.braille.assert_called_once_with("Mensaje")
        grabador.braille.assert_called_once_with("Mensaje")


class TestPreparar(unittest.TestCase):

    def test_el_inicializador_deja_el_doble_que_usa_anunciar(self):
        real = mock.Mock()
        grabador = mock.Mock()

        def init_gui():
            accesibilidad._lector = real

        def init_accesibilidad():
            accesibilidad._lector = real

        anterior = accesibilidad._lector
        self.addCleanup(setattr, accesibilidad, "_lector", anterior)

        def instalar():
            accesibilidad._lector = grabador

        with (
            mock.patch.object(gui, "_lector_init", init_gui),
            mock.patch.object(accesibilidad, "_lector_init",
                              init_accesibilidad),
            mock.patch.object(app.sonda, "instalar", side_effect=instalar),
        ):
            app.preparar()
            gui._lector_init()
            doble = accesibilidad._lector
            self.assertIsInstance(doble, app.DobleLector)
            doble.speak("Hola")

        real.speak.assert_called_once_with("Hola", interrupt=False)
        grabador.speak.assert_called_once_with("Hola", interrupt=False)


if __name__ == "__main__":
    unittest.main()
