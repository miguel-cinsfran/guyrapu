# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Texto que la voz lee de un ítem con traducción del chat."""

import unittest

from guyrapu.translation.proveedores.base import Traduccion
from guyrapu.voice import lectura_traducida


def _config(forma="completo"):
    return {"limpiar_emojis": True, "eliminar_urls": True,
            "max_longitud_mensaje": 200,
            "traducir_idioma_original": forma}


def _item(resultado, texto_tts="Ana: hola", ml="hola", destino="es",
          espera=2.0):
    pedido = PedidoFalso(resultado, destino, espera)
    return {"texto_tts": texto_tts, "autor": "Ana", "ml": ml,
            "pedido": pedido}


class PedidoFalso:
    def __init__(self, resultado, destino="es", espera=2.0):
        self.resultado = resultado
        self.destino = destino
        self.segundos = None
        self._espera = espera

    def esperar(self, segundos):
        self.segundos = segundos
        return self.resultado


class TestSinTraduccion(unittest.TestCase):

    def test_sin_pedido_lee_el_texto_de_siempre(self):
        item = {"texto_tts": "Ana: hola", "autor": "Ana"}
        self.assertEqual(lectura_traducida.texto(item, _config()), "Ana: hola")

    def test_sin_resultado_lee_el_original(self):
        item = _item(None)
        self.assertEqual(lectura_traducida.texto(item, _config()), "Ana: hola")

    def test_si_el_origen_es_el_destino_lee_como_hoy(self):
        item = _item(Traduccion("hola", "es"))
        self.assertEqual(lectura_traducida.texto(item, _config()), "Ana: hola")

    def test_un_origen_sin_codigo_lee_el_original(self):
        item = _item(Traduccion("HELLO", None))
        self.assertEqual(lectura_traducida.texto(item, _config()), "Ana: hola")


class TestTraduccion(unittest.TestCase):

    def test_reemplaza_el_mensaje_y_suma_el_idioma_completo(self):
        item = _item(Traduccion("HELLO", "en"))
        self.assertEqual(lectura_traducida.texto(item, _config()),
                         "Ana: HELLO, del inglés")

    def test_abreviado_entre_parentesis(self):
        item = _item(Traduccion("HELLO", "en"))
        self.assertEqual(lectura_traducida.texto(item, _config("abreviado")),
                         "Ana: HELLO (EN)")

    def test_no_decirlo_deja_solo_la_traduccion(self):
        item = _item(Traduccion("HELLO", "en"))
        self.assertEqual(lectura_traducida.texto(item, _config("no")),
                         "Ana: HELLO")

    def test_un_codigo_desconocido_se_dice_abreviado(self):
        item = _item(Traduccion("HELLO", "xx"))
        self.assertEqual(lectura_traducida.texto(item, _config()),
                         "Ana: HELLO (XX)")

    def test_limpia_la_traduccion_con_la_configuracion(self):
        item = _item(Traduccion("HELLO 😀 https://ejemplo.test", "en"))
        self.assertEqual(lectura_traducida.texto(item, _config("no")),
                         "Ana: HELLO")

    def test_la_espera_se_cuenta_desde_que_la_voz_lee(self):
        item = _item(None)
        item["pedido"].edad = lambda: 1.5
        lectura_traducida.texto(item, _config())
        self.assertEqual(item["pedido"].segundos, 2.0)

    def test_solo_reemplaza_el_mensaje_y_conserva_el_resto(self):
        item = _item(Traduccion("HELLO", "en"),
                     texto_tts="Ana dijo: hola, en el chat")
        self.assertEqual(lectura_traducida.texto(item, _config("no")),
                         "Ana dijo: HELLO, en el chat")


if __name__ == "__main__":
    unittest.main()
