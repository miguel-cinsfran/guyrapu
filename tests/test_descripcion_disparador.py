# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de la fila de la lista y de la frase de Escuchar de un disparador."""

import unittest

from guyrapu.interaction import descripcion_disparador, disparadores


def _evento(**cambios):
    datos = {"nombre": "regalo", "cuando": "evento", "evento": "superchat"}
    datos.update(cambios)
    return disparadores.Disparador(**datos)


class TestFila(unittest.TestCase):

    def test_cuenta_el_evento_con_su_minimo(self):
        self.assertEqual(
            descripcion_disparador.fila(_evento(minimo=5)),
            "regalo, cuando llega Super Chats y regalos desde 5, en el vídeo")

    def test_p5_la_fila_dice_el_regalo_con_su_minimo(self):
        self.assertEqual(
            descripcion_disparador.fila(_evento(regalo="Lion", minimo=5)),
            "regalo, cuando llega el regalo Lion desde 5, en el vídeo")

    def test_p6_la_fila_dice_donde_se_muestra_con_las_palabras_del_comando(self):
        self.assertEqual(
            descripcion_disparador.fila(_evento(destino="ambos")),
            "regalo, cuando llega Super Chats y regalos, en el vídeo y en el chat")

    def test_marca_los_pausados(self):
        self.assertEqual(
            descripcion_disparador.fila(_evento(activo=False)),
            "regalo, cuando llega Super Chats y regalos, en el vídeo, pausado")


class TestEscuchar(unittest.TestCase):

    def test_cuenta_un_disparador_de_evento_con_minimo(self):
        disparador = _evento(minimo=5, medio="fuegos.gif")
        self.assertEqual(
            descripcion_disparador.escuchar(disparador),
            "regalo: cuando llega Super Chats y regalos desde 5, muestra el "
            "medio fuegos.gif. Se muestra en el vídeo.")

    def test_p5_escuchar_dice_el_regalo(self):
        disparador = _evento(regalo="León", medio="fuegos.gif")
        self.assertEqual(
            descripcion_disparador.escuchar(disparador),
            "regalo: cuando llega el regalo León, muestra el medio "
            "fuegos.gif. Se muestra en el vídeo.")

    def test_cuenta_un_disparador_de_evento_sin_minimo(self):
        disparador = _evento(evento="cofre", tarjeta="Gracias")
        self.assertEqual(
            descripcion_disparador.escuchar(disparador),
            "regalo: cuando llega Cofres, muestra la tarjeta «Gracias». "
            "Se muestra en el vídeo.")

    def test_cuenta_solo_la_tarjeta(self):
        disparador = _evento(tarjeta="Gracias")
        self.assertEqual(
            descripcion_disparador.escuchar(disparador),
            "regalo: cuando llega Super Chats y regalos, muestra la tarjeta "
            "«Gracias». Se muestra en el vídeo.")

    def test_p6_escuchar_dice_donde_se_muestra_con_las_palabras_del_comando(self):
        self.assertEqual(
            descripcion_disparador.escuchar(_evento(destino="chat", tarjeta="Gracias")),
            "regalo: cuando llega Super Chats y regalos, muestra la tarjeta "
            "«Gracias». Se muestra en el chat.")

    def test_marca_los_pausados_al_final(self):
        disparador = _evento(medio="aplauso.gif", activo=False)
        self.assertEqual(
            descripcion_disparador.escuchar(disparador),
            "regalo: cuando llega Super Chats y regalos, muestra el medio "
            "aplauso.gif. Se muestra en el vídeo. En pausa.")


if __name__ == "__main__":
    unittest.main()
