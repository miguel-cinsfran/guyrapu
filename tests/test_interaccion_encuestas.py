# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de las encuestas que se votan con `!` desde cualquier chat."""

import random
import unittest

from guyrapu.core import plataformas
from guyrapu.core.config import TIPO_TEXTO
from guyrapu.interaction.encuestas import Encuesta, validar_encuesta
from guyrapu.interaction.evento import EventoDirecto


def _evento(texto, autor_id="1", plataforma=plataformas.YOUTUBE):
    return EventoDirecto(
        plataforma=plataforma,
        autor_id=autor_id,
        autor="Ana",
        roles=frozenset(),
        tipo=TIPO_TEXTO,
        texto=texto,
        monto="")


def _encuesta(opciones=("pizza", "sushi", "tacos"), segundos=None,
              pregunta="¿Qué?"):
    encuesta = Encuesta(pregunta, opciones, segundos=segundos)
    encuesta.abrir(0)
    return encuesta


class TestVotar(unittest.TestCase):

    def test_el_primer_voto_de_cada_persona_es_el_que_cuenta(self):
        encuesta = _encuesta()
        self.assertEqual(1, encuesta.votar(_evento("!1", "1"), 1))
        self.assertIsNone(encuesta.votar(_evento("!2", "1"), 2))
        self.assertEqual([1, 0, 0], encuesta.votos())
        self.assertEqual(1, encuesta.total())

    def test_cuenta_el_numero_aunque_siga_texto(self):
        encuesta = _encuesta()
        self.assertEqual(2, encuesta.votar(_evento("!2 si", "1"), 1))

    def test_no_cuentan_los_numeros_que_no_son_opcion(self):
        encuesta = _encuesta()
        textos = ("!0", "!10", "!a", "sin comando", "!", "! 1")
        for indice, texto in enumerate(textos):
            with self.subTest(texto=texto):
                self.assertIsNone(
                    encuesta.votar(_evento(texto, str(indice + 1)), indice + 2))
        self.assertEqual(0, encuesta.total())

    def test_de_dos_a_nueve_opciones(self):
        self.assertTrue(validar_encuesta("¿Qué?", ["uno"]))
        self.assertTrue(validar_encuesta(
            "¿Qué?", [str(numero) for numero in range(10)]))
        self.assertEqual("", validar_encuesta("¿Qué?", ["uno", "dos"]))
        self.assertEqual("", validar_encuesta(
            "¿Qué?", [str(numero) for numero in range(9)]))

    def test_pregunta_y_opciones_no_pueden_estar_vacias(self):
        self.assertTrue(validar_encuesta("  ", ["uno", "dos"]))
        self.assertTrue(validar_encuesta("¿Qué?", ["uno", "  "]))
        self.assertEqual("", validar_encuesta("¿Qué?", ["uno", "dos"]))


class TestPropiedadDelTotal(unittest.TestCase):

    def test_el_total_nunca_supera_las_personas_distintas(self):
        azar = random.Random(940)
        for _ in range(200):
            encuesta = _encuesta(("a", "b", "c", "d"))
            personas = set()
            for _ in range(30):
                autor_id = str(azar.randrange(12))
                plataforma = azar.choice(
                    (plataformas.YOUTUBE, plataformas.TIKTOK))
                personas.add((plataforma, autor_id))
                texto = "!" + str(azar.randrange(0, 6))
                encuesta.votar(
                    _evento(texto, autor_id, plataforma), azar.random() * 10)
            self.assertLessEqual(encuesta.total(), len(personas))


class TestVotosEntrePlataformas(unittest.TestCase):

    def test_el_mismo_id_en_dos_plataformas_son_dos_personas(self):
        encuesta = _encuesta()
        self.assertEqual(1, encuesta.votar(
            _evento("!1", "7", plataformas.YOUTUBE), 1))
        self.assertEqual(1, encuesta.votar(
            _evento("!1", "7", plataformas.TIKTOK), 2))
        self.assertEqual([2, 0, 0], encuesta.votos())
        self.assertEqual(2, encuesta.total())

    def test_los_votos_de_ambas_plataformas_suman_en_la_opcion(self):
        encuesta = _encuesta()
        encuesta.votar(_evento("!2", "1", plataformas.YOUTUBE), 1)
        encuesta.votar(_evento("!2", "1", plataformas.TIKTOK), 2)
        self.assertEqual([0, 2, 0], encuesta.votos())


class TestCierre(unittest.TestCase):

    def test_cerrada_no_acepta_votos(self):
        encuesta = _encuesta()
        encuesta.cerrar()
        self.assertFalse(encuesta.abierta(1))
        self.assertIsNone(encuesta.votar(_evento("!1", "1"), 1))

    def test_vencida_no_acepta_votos(self):
        encuesta = _encuesta(segundos=60)
        self.assertTrue(encuesta.abierta(59))
        self.assertEqual(1, encuesta.votar(_evento("!1", "1"), 59))
        self.assertFalse(encuesta.abierta(60))
        self.assertIsNone(encuesta.votar(_evento("!2", "2"), 61))


class TestResumen(unittest.TestCase):

    def test_resumen_con_votos_y_tiempo(self):
        encuesta = _encuesta(("pizza", "sushi"), segundos=60)
        for autor_id, ahora in (("1", 1), ("2", 2), ("3", 3)):
            encuesta.votar(_evento("!1", autor_id), ahora)
        encuesta.votar(_evento("!2", "4"), 4)
        self.assertEqual(
            "Encuesta: ¿Qué?. 1, pizza: 3 votos. 2, sushi: 1 voto. "
            "Total: 4 votos. Quedan 56 segundos.",
            encuesta.resumen(4))

    def test_resumen_cerrado(self):
        encuesta = _encuesta(("pizza", "sushi"))
        encuesta.votar(_evento("!1", "1"), 1)
        encuesta.cerrar()
        self.assertEqual(
            "Encuesta: ¿Qué?. 1, pizza: 1 voto. 2, sushi: 0 votos. "
            "Total: 1 voto. Cerrada.",
            encuesta.resumen(2))

    def test_sin_tiempo_no_dice_cuanto_queda(self):
        resumen = _encuesta(("pizza", "sushi")).resumen(9999)
        self.assertNotIn("Quedan", resumen)
        self.assertTrue(resumen.endswith("Total: 0 votos."), resumen)


class TestGanadoras(unittest.TestCase):

    def test_sin_votos_no_hay_ganadoras(self):
        self.assertEqual([], _encuesta().ganadoras())

    def test_devuelve_todas_las_empatadas(self):
        encuesta = _encuesta()
        encuesta.votar(_evento("!1", "1"), 1)
        encuesta.votar(_evento("!1", "2"), 2)
        encuesta.votar(_evento("!3", "3"), 3)
        encuesta.votar(_evento("!3", "4"), 4)
        self.assertEqual([1, 3], encuesta.ganadoras())


if __name__ == "__main__":
    unittest.main()
