# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""El ítem de voz de un mensaje del chat: datos, marcas y modo de lectura."""

import queue
import unittest
from unittest import mock

from guyrapu.capture import item_lectura
from guyrapu.core.config import (
    TIPO_TEXTO, TIPO_SUPERCHAT, TIPO_STICKER, TIPO_MIEMBRO, TIPO_COFRE,
    TIPO_ENTRADA,
)
from guyrapu.core.sonidos_eventos import ROL_PROPIETARIO, ROL_MODERADOR
from main import Stats, procesar_entrante


class TestArmar(unittest.TestCase):

    def test_texto_comun(self):
        self.assertEqual(
            item_lectura.armar("Ana: hola", "Ana", TIPO_TEXTO, "", None),
            {"texto_tts": "Ana: hola", "autor": "Ana"})

    def test_eventos_con_aporte_son_importantes(self):
        for tipo in (TIPO_SUPERCHAT, TIPO_STICKER, TIPO_MIEMBRO, TIPO_COFRE):
            with self.subTest(tipo=tipo):
                self.assertEqual(
                    item_lectura.armar("texto", "Ana", tipo, "", None),
                    {"texto_tts": "texto", "autor": "Ana",
                     "importante": True})

    def test_propietario_y_moderador_son_importantes(self):
        for rol in (ROL_PROPIETARIO, ROL_MODERADOR):
            with self.subTest(rol=rol):
                self.assertEqual(
                    item_lectura.armar("texto", "Ana", TIPO_TEXTO, rol, None),
                    {"texto_tts": "texto", "autor": "Ana",
                     "importante": True})

    def test_modo_con_voz_secundaria_lleva_la_marca(self):
        self.assertEqual(
            item_lectura.armar("texto", "Ana", TIPO_TEXTO, "", "secundaria"),
            {"texto_tts": "texto", "autor": "Ana", "secundaria": True})

    def test_con_pedido_suma_el_pedido_y_el_texto_limpio(self):
        pedido = object()
        with mock.patch.object(item_lectura.traduccion_chat, "pedir",
                               return_value=pedido) as pedir:
            item = item_lectura.armar("texto", "Ana", TIPO_TEXTO, "", None,
                                      "hola", "limpio")
        pedir.assert_called_once_with("hola")
        self.assertEqual(item, {"texto_tts": "texto", "autor": "Ana",
                                "pedido": pedido, "ml": "limpio"})

    def test_un_evento_no_pide_traduccion(self):
        with mock.patch.object(item_lectura.traduccion_chat, "pedir") as pedir:
            item = item_lectura.armar("texto", "Ana", TIPO_ENTRADA, "",
                                      None, "hola", "limpio")
        pedir.assert_not_called()
        self.assertEqual(item, {"texto_tts": "texto", "autor": "Ana"})


class TestProcesarEntranteUsaItemLectura(unittest.TestCase):

    def _cfg(self):
        return {
            "usuarios_silenciados": [],
            "palabras_silenciadas": [],
            "silenciados_ocultar": set(),
            "silenciados_runtime": set(),
            "silenciar_lectura": False,
            "limpiar_emojis": True,
            "eliminar_urls": False,
            "max_longitud_mensaje": 200,
            "umbral_solo_nombre": 0,
            "formato_prefijo": "nombre_mensaje",
            "estrategia": "todas",
            "tamanio_maximo": 10,
        }

    def test_procesar_entrante_encola_lo_que_arma_item_lectura(self):
        item = {"texto_tts": "Ana: hola", "autor": "Ana"}
        cola = queue.Queue()
        with mock.patch.object(item_lectura, "armar",
                               return_value=item) as armar:
            procesar_entrante("Ana", "hola", TIPO_TEXTO, "", "canal", cola,
                              self._cfg(), Stats())
        armar.assert_called_once()
        self.assertIs(cola.get_nowait(), item)


if __name__ == "__main__":
    unittest.main()
