# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de la fila de la lista y de la frase de Escuchar de un disparador."""

import unittest

from guyrapu.interaction import descripcion_disparador, disparadores


def _comando(**cambios):
    datos = {"nombre": "aplauso", "cuando": "comando",
             "comandos": ("aplauso",)}
    datos.update(cambios)
    return disparadores.Disparador(**datos)


def _evento(**cambios):
    datos = {"nombre": "regalo", "cuando": "evento", "evento": "superchat"}
    datos.update(cambios)
    return disparadores.Disparador(**datos)


def _atajo(**cambios):
    datos = {"nombre": "botonera", "cuando": "atajo", "atajo": 3}
    datos.update(cambios)
    return disparadores.Disparador(**datos)


class TestFila(unittest.TestCase):

    def test_dice_el_nombre_y_cuando_sale(self):
        self.assertEqual(
            descripcion_disparador.fila(_comando()),
            "aplauso, cuando alguien escribe !aplauso")

    def test_marca_los_pausados(self):
        self.assertEqual(
            descripcion_disparador.fila(_comando(activo=False)),
            "aplauso, cuando alguien escribe !aplauso, pausado")

    def test_cuenta_el_evento_con_su_minimo(self):
        self.assertEqual(
            descripcion_disparador.fila(
                _evento(minimo=5)),
            "regalo, cuando llega Super Chats y regalos desde 5")

    def test_p5_la_fila_dice_el_regalo_con_su_minimo(self):
        self.assertEqual(
            descripcion_disparador.fila(_evento(regalo="Lion", minimo=5)),
            "regalo, cuando llega el regalo Lion desde 5")

    def test_p6_la_fila_dice_el_atajo(self):
        self.assertEqual(
            descripcion_disparador.fila(_atajo()),
            "botonera, con Ctrl+Alt+Mayús+3")


class TestEscuchar(unittest.TestCase):

    def test_cuenta_un_disparador_de_comando_con_medio_y_tarjeta(self):
        disparador = _comando(
            medio="aplauso.gif", tarjeta="Gracias por el apoyo")
        self.assertEqual(
            descripcion_disparador.escuchar(disparador),
            "aplauso: cuando alguien escribe !aplauso, muestra el medio "
            "aplauso.gif y la tarjeta «Gracias por el apoyo».")

    def test_cuenta_un_disparador_de_evento_con_minimo(self):
        disparador = _evento(minimo=5, medio="fuegos.gif")
        self.assertEqual(
            descripcion_disparador.escuchar(disparador),
            "regalo: cuando llega Super Chats y regalos desde 5, muestra el "
            "medio fuegos.gif.")

    def test_p5_escuchar_dice_el_regalo(self):
        disparador = _evento(regalo="León", medio="fuegos.gif")
        self.assertEqual(
            descripcion_disparador.escuchar(disparador),
            "regalo: cuando llega el regalo León, muestra el medio "
            "fuegos.gif.")

    def test_cuenta_un_disparador_de_evento_sin_minimo(self):
        disparador = _evento(evento="cofre", tarjeta="Gracias")
        self.assertEqual(
            descripcion_disparador.escuchar(disparador),
            "regalo: cuando llega Cofres, muestra la tarjeta «Gracias».")

    def test_cuenta_solo_la_tarjeta(self):
        disparador = _comando(tarjeta="Gracias")
        self.assertEqual(
            descripcion_disparador.escuchar(disparador),
            "aplauso: cuando alguien escribe !aplauso, muestra la tarjeta "
            "«Gracias».")

    def test_p6_escuchar_dice_el_atajo(self):
        self.assertEqual(
            descripcion_disparador.escuchar(_atajo(medio="fuegos.gif")),
            "botonera: con Ctrl+Alt+Mayús+3, muestra el medio fuegos.gif.")

    def test_marca_los_pausados_al_final(self):
        disparador = _comando(medio="aplauso.gif", activo=False)
        self.assertEqual(
            descripcion_disparador.escuchar(disparador),
            "aplauso: cuando alguien escribe !aplauso, muestra el medio "
            "aplauso.gif. En pausa.")


if __name__ == "__main__":
    unittest.main()
