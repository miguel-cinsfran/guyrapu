# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de la fila de la lista y de la frase de Escuchar."""

import unittest

from guyrapu.interaction import comandos, descripcion_comando


class TestFila(unittest.TestCase):

    def test_dice_la_palabra_el_destino_y_quien_puede_usarlo(self):
        comando = comandos.Comando("discord", (), "Hola")
        self.assertEqual(descripcion_comando.fila(comando),
                         "!discord, en el vídeo, todos")

    def test_marca_los_pausados(self):
        comando = comandos.Comando("discord", (), "Hola", activo=False)
        self.assertEqual(descripcion_comando.fila(comando),
                         "!discord, en el vídeo, todos, pausado")

    def test_cuenta_el_chat_y_los_moderadores(self):
        comando = comandos.Comando(
            "hola", (), "Hola", destino="chat", permiso="moderadores")
        self.assertEqual(descripcion_comando.fila(comando),
                         "!hola, en el chat, solo moderadores")

    def test_cuenta_los_dos_destinos_y_la_lista_de_nombres(self):
        comando = comandos.Comando(
            "sorteo", (), "Hola", destino="ambos", permiso="lista",
            nombres=("Ana", "Beto"))
        self.assertEqual(
            descripcion_comando.fila(comando),
            "!sorteo, en el vídeo y en el chat, una lista de nombres: Ana, Beto")


    def test_dice_el_medio_despues_de_donde_se_muestra(self):
        comando = comandos.Comando("grito", (), "Hola", medio="fuegos")
        self.assertEqual(descripcion_comando.fila(comando),
                         "!grito, en el vídeo, con el medio fuegos, todos")


class TestEscuchar(unittest.TestCase):

    def test_cuenta_el_comando_entero_con_datos_de_ejemplo(self):
        comando = comandos.Comando(
            "discord", ("dc", "d"),
            "Hola {usuario}, número {contador}, {texto}fin",
            espera_general=5, espera_persona=30, segundos=8)
        self.assertEqual(
            descripcion_comando.escuchar(comando, "Clásico"),
            "Comando !discord, con los alias !dc, !d. "
            "Responde: Hola Ana, número 1, fin. "
            "Se muestra en el vídeo, con el estilo Clásico y 8 segundos en "
            "pantalla. "
            "Puede usarlo: todos. "
            "Espera 5 segundos entre usos y 30 segundos por persona.")

    def test_en_el_chat_no_nombra_estilo_ni_segundos(self):
        comando = comandos.Comando(
            "hola", (), "Hola", destino="chat", permiso="moderadores",
            espera_general=0, espera_persona=15)
        self.assertEqual(
            descripcion_comando.escuchar(comando, "Clásico"),
            "Comando !hola. Responde: Hola. Se muestra en el chat. "
            "Puede usarlo: solo moderadores. "
            "Espera 0 segundos entre usos y 15 segundos por persona.")

    def test_dice_la_lista_de_nombres_y_si_esta_pausado(self):
        comando = comandos.Comando(
            "sorteo", (), "Hola", destino="chat", permiso="lista",
            nombres=("Ana", "Beto"), activo=False)
        self.assertEqual(
            descripcion_comando.escuchar(comando, "Clásico"),
            "Comando !sorteo. Responde: Hola. Se muestra en el chat. "
            "Puede usarlo: una lista de nombres: Ana, Beto. "
            "Espera 5 segundos entre usos y 30 segundos por persona. "
            "Pausado.")


    def test_nombra_el_medio_despues_de_la_respuesta(self):
        comando = comandos.Comando("grito", (), "Hola", medio="fuegos")
        texto = descripcion_comando.escuchar(comando, "Clásico")
        self.assertIn("Responde: Hola. Muestra el medio fuegos.", texto)

    def test_sin_respuesta_no_dice_responde_y_si_dice_el_medio(self):
        comando = comandos.Comando("grito", (), "", medio="fuegos")
        texto = descripcion_comando.escuchar(comando, "Clásico")
        self.assertNotIn("Responde:", texto)
        self.assertIn("Muestra el medio fuegos.", texto)


if __name__ == "__main__":
    unittest.main()
