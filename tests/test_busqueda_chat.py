# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de la búsqueda pura en los mensajes del chat."""

import unittest

from guyrapu.core.config import TIPO_SUPERCHAT, TIPO_TEXTO
from guyrapu.ui.busqueda_chat import buscar
from guyrapu.ui.lista_chat import MensajeChat


def _mensaje(autor, texto, hora="12:00", tipo=TIPO_TEXTO):
    return MensajeChat(plataforma="youtube", autor=autor, identificador="C",
                       texto=texto, hora=hora, tipo=tipo, monto="", rol="")


SIN_OCULTOS = lambda autor: False


class TestBuscarEnChat(unittest.TestCase):

    def test_coincide_en_el_texto(self):
        mensajes = [_mensaje("Ana", "Hola mundo", "10:00"),
                    _mensaje("Beto", "otra cosa", "10:01")]
        self.assertEqual(buscar(mensajes, "mundo", SIN_OCULTOS),
                         [mensajes[0]])

    def test_coincide_en_el_autor(self):
        mensajes = [_mensaje("Ana", "hola", "10:00"),
                    _mensaje("Beto", "chau", "10:01")]
        self.assertEqual(buscar(mensajes, "beto", SIN_OCULTOS),
                         [mensajes[1]])

    def test_no_distingue_mayusculas_ni_tildes(self):
        mensajes = [_mensaje("Ana", "canción nueva", "10:00"),
                    _mensaje("Beto", "cancion vieja", "10:01")]
        self.assertEqual(buscar(mensajes, "CANCION", SIN_OCULTOS),
                         [mensajes[1], mensajes[0]])
        self.assertEqual(buscar(mensajes, "canción", SIN_OCULTOS),
                         [mensajes[1], mensajes[0]])

    def test_devuelve_del_mas_nuevo_al_mas_viejo(self):
        mensajes = [_mensaje("Ana", "uno", "10:00"),
                    _mensaje("Ana", "dos", "10:01"),
                    _mensaje("Ana", "tres", "10:02")]
        self.assertEqual(buscar(mensajes, "ana", SIN_OCULTOS),
                         [mensajes[2], mensajes[1], mensajes[0]])

    def test_excluye_los_autores_ocultos(self):
        mensajes = [_mensaje("Ana", "hola", "10:00"),
                    _mensaje("Beto", "hola", "10:01")]
        resultado = buscar(mensajes, "hola", lambda autor: autor == "Ana")
        self.assertEqual(resultado, [mensajes[1]])

    def test_texto_vacio_no_devuelve_nada(self):
        mensajes = [_mensaje("Ana", "hola", "10:00")]
        self.assertEqual(buscar(mensajes, "", SIN_OCULTOS), [])
        self.assertEqual(buscar(mensajes, "   ", SIN_OCULTOS), [])

    def test_la_busqueda_no_mira_el_tipo(self):
        mensajes = [_mensaje("Ana", "pregunta", "10:00", TIPO_SUPERCHAT)]
        self.assertEqual(buscar(mensajes, "pregunta", SIN_OCULTOS),
                         [mensajes[0]])


if __name__ == "__main__":
    unittest.main()
