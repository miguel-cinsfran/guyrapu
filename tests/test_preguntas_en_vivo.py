# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Las preguntas del público puestas en la app: aviso, página y vídeo."""

import types
import unittest
from unittest import mock

from guyrapu.interaction.evento import desde_entrante
from guyrapu.ui import preguntas_en_vivo


def _evento(texto, autor="Ana", autor_id="A"):
    return desde_entrante(autor, texto, "texto", "", autor_id, "", "youtube")


class _Capa:
    """Capa de prueba: anota las piezas que le suman."""

    def __init__(self):
        self.agregadas = []

    def agregar_pieza(self, pieza):
        self.agregadas.append(pieza)


class Base(unittest.TestCase):

    def setUp(self):
        self.frame = types.SimpleNamespace()
        self.capa = _Capa()
        self.anuncios = []
        parches = (
            mock.patch.object(preguntas_en_vivo, "_capa",
                              return_value=self.capa),
            mock.patch.object(
                preguntas_en_vivo, "_avisar",
                side_effect=lambda texto, sonido: self.anuncios.append(
                    (texto, sonido))),
        )
        for parche in parches:
            parche.start()
            self.addCleanup(parche.stop)
        self.ahora = 0.0

    def _recibir(self, texto, autor="Ana", autor_id="A"):
        self.ahora += 1.0
        return preguntas_en_vivo.recibir(
            self.frame, _evento(texto, autor, autor_id), self.ahora)

    def _llenar(self, desde=0, hasta=50):
        for numero in range(desde, hasta):
            self._recibir(f"!pregunta Pregunta {numero}",
                          f"Persona {numero}", str(numero))


class TestRecibir(Base):

    def test_un_texto_que_no_es_pregunta_no_se_atiende(self):
        self.assertFalse(self._recibir("!discord Hola"))
        self.assertEqual(
            preguntas_en_vivo.pendientes(self.frame), [])

    def test_un_mensaje_de_pregunta_se_atiende_aunque_no_sume(self):
        self.assertTrue(self._recibir("!pregunta"))
        self.assertEqual(
            preguntas_en_vivo.pendientes(self.frame), [])


class TestColaLlena(Base):

    def test_avisa_una_sola_vez_y_vuelve_tras_liberar_lugar(self):
        self._llenar()
        self.assertEqual(self.anuncios, [])
        self.assertTrue(self._recibir("!pregunta Otra", "Extra", "extra"))
        self.assertEqual(len(self.anuncios), 1)
        texto, sonido = self.anuncios[0]
        self.assertEqual(texto, "La cola de preguntas está llena.")
        self.assertEqual(sonido, "preguntas_llena")
        self._recibir("!pregunta Otra más", "Otra", "otra")
        self.assertEqual(len(self.anuncios), 1)
        primera = preguntas_en_vivo.siguiente(self.frame)
        preguntas_en_vivo.descartar(self.frame, primera.id)
        self._recibir("!pregunta Nueva", "Nueva", "nueva")
        self._recibir("!pregunta Última", "Última", "ultima")
        self.assertEqual(len(self.anuncios), 2)


class TestPagina(Base):

    def test_avisa_a_los_suscritos_cada_vez_que_la_cola_cambia(self):
        cambios = []
        preguntas_en_vivo.suscribir(self.frame, lambda: cambios.append(1))
        self._recibir("!pregunta Uno", "Ana", "A")
        self._recibir("!pregunta Dos", "Beto", "B")
        self.assertEqual(len(cambios), 2)
        primera = preguntas_en_vivo.siguiente(self.frame)
        preguntas_en_vivo.responder(self.frame, primera.id)
        self.assertEqual(len(cambios), 3)
        preguntas_en_vivo.vaciar(self.frame)
        self.assertEqual(len(cambios), 4)


class TestVideo(Base):

    def test_muestra_la_pregunta_con_su_texto_sus_segundos_y_su_estilo(self):
        self._recibir("!pregunta Hola", "Ana", "A")
        pregunta = preguntas_en_vivo.siguiente(self.frame)
        self.assertTrue(preguntas_en_vivo.mostrar(self.frame, pregunta.id))
        pieza, = self.capa.agregadas
        self.assertEqual(pieza.tipo, "pregunta")
        self.assertEqual(pieza.texto, "Ana pregunta: Hola")
        self.assertEqual(pieza.segundos, 15)
        self.assertEqual(pieza.datos["estilo"], "")
        self.assertEqual(
            [actual.id for actual in
             preguntas_en_vivo.pendientes(self.frame)],
            [pregunta.id])

    def test_mostrar_una_que_ya_no_esta_no_suma_nada(self):
        self.assertFalse(preguntas_en_vivo.mostrar(self.frame, 99))
        self.assertEqual(self.capa.agregadas, [])


if __name__ == "__main__":
    unittest.main()
