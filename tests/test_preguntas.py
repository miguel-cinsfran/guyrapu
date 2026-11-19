# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Las preguntas del público de la sesión: cómo entran, se ordenan y salen."""

import random
import unittest

from guyrapu.interaction import preguntas
from guyrapu.interaction.evento import desde_entrante


def _evento(autor="Ana", autor_id="A", plataforma="youtube"):
    return desde_entrante(autor, "", "texto", "", autor_id, "", plataforma)


class Base(unittest.TestCase):

    def setUp(self):
        self.cola = preguntas.ColaPreguntas()
        self.ahora = 0.0

    def _sumar(self, texto, autor="Ana", autor_id="A", plataforma="youtube",
               bloqueadas=()):
        self.ahora += 1.0
        invocacion = preguntas.leer(texto)
        self.assertIsNotNone(invocacion)
        return self.cola.agregar(
            _evento(autor, autor_id, plataforma), invocacion.argumentos,
            bloqueadas, self.ahora)


class TestLeer(unittest.TestCase):

    def test_reconoce_pregunta_y_q_sin_importar_mayusculas(self):
        for texto in ("!pregunta Hola", "!PREGUNTA Hola", "!q Hola",
                      "!Q Hola"):
            with self.subTest(texto=texto):
                invocacion = preguntas.leer(texto)
                self.assertIsNotNone(invocacion)
                self.assertEqual(invocacion.argumentos, "Hola")

    def test_otro_comando_o_un_texto_no_son_pregunta(self):
        for texto in ("!discord Hola", "Hola", ""):
            with self.subTest(texto=texto):
                self.assertIsNone(preguntas.leer(texto))


class TestAgregar(Base):

    def test_guarda_plataforma_autor_texto_e_instante(self):
        self.assertEqual(
            self._sumar("!pregunta ¿Hay sorteo?", "Ana", "A1", "tiktok"),
            preguntas.SUMADA)
        pregunta, = self.cola.pendientes()
        self.assertGreater(pregunta.id, 0)
        self.assertEqual(
            (pregunta.plataforma, pregunta.autor_id, pregunta.autor,
             pregunta.texto, pregunta.instante),
            ("tiktok", "A1", "Ana", "¿Hay sorteo?", self.ahora))

    def test_sin_texto_no_suma(self):
        self.assertEqual(self._sumar("!pregunta"),
                         preguntas.IGNORADA)
        self.assertEqual(self.cola.pendientes(), [])

    def test_un_texto_casi_todo_de_simbolos_no_suma(self):
        self.assertEqual(self._sumar("!pregunta !!!!!!!!!!!!!"),
                         preguntas.IGNORADA)
        self.assertEqual(self.cola.pendientes(), [])

    def test_tapa_el_nombre_y_el_texto_con_las_bloqueadas(self):
        self._sumar("!pregunta Hola tonto", autor="Tonto", autor_id="A",
                    bloqueadas=["tonto"])
        pregunta, = self.cola.pendientes()
        self.assertEqual(pregunta.autor, "***")
        self.assertEqual(pregunta.texto, "Hola ***")

    def test_corta_el_texto_en_300_y_termina_en_puntos_suspensivos(self):
        self._sumar("!pregunta " + "a" * 301)
        pregunta, = self.cola.pendientes()
        self.assertEqual(len(pregunta.texto), 300)
        self.assertEqual(pregunta.texto, "a" * 299 + "…")

    def test_un_texto_de_300_queda_igual(self):
        self._sumar("!pregunta " + "b" * 300, autor_id="B")
        pregunta, = self.cola.pendientes()
        self.assertEqual(pregunta.texto, "b" * 300)


class TestUnaPorPersona(Base):

    def test_la_segunda_reemplaza_el_texto_y_conserva_su_lugar(self):
        self._sumar("!pregunta Primera", "Ana", "A")
        self._sumar("!pregunta Segunda", "Beto", "B")
        self._sumar("!pregunta Tercera", "Carla", "C")
        primera = self.cola.pendientes()[0]
        self.assertEqual(
            self._sumar("!pregunta Cambio", "Ana", "A"), preguntas.SUMADA)
        pendientes = self.cola.pendientes()
        self.assertEqual([pregunta.texto for pregunta in pendientes],
                         ["Cambio", "Segunda", "Tercera"])
        self.assertEqual(pendientes[0].id, primera.id)

    def test_la_misma_persona_en_otra_plataforma_es_otra(self):
        self._sumar("!pregunta Una", "Ana", "A", "youtube")
        self._sumar("!pregunta Dos", "Ana", "A", "tiktok")
        self.assertEqual(len(self.cola.pendientes()), 2)


class TestColaLlena(Base):

    def _llenar(self):
        for numero in range(preguntas.MAXIMO):
            self._sumar(f"!pregunta Pregunta {numero}",
                        f"Persona {numero}", str(numero))

    def test_no_pasa_de_50_y_avisa_una_sola_vez_hasta_que_hay_lugar(self):
        self._llenar()
        self.assertEqual(len(self.cola.pendientes()), preguntas.MAXIMO)
        self.assertEqual(self._sumar("!pregunta Otra", "Extra", "extra"),
                         preguntas.LLENA)
        self.assertTrue(self.cola.avisar_llena())
        self.assertFalse(self.cola.avisar_llena())
        self.cola.descartar(self.cola.pendientes()[0].id)
        self._sumar("!pregunta Nueva", "Nueva", "nueva")
        self.assertEqual(self._sumar("!pregunta Otra más", "Otra", "otra"),
                         preguntas.LLENA)
        self.assertTrue(self.cola.avisar_llena())

    def test_con_la_cola_llena_la_misma_persona_reemplaza(self):
        self._llenar()
        self.assertEqual(self._sumar("!pregunta Cambio", "Persona 7", "7"),
                         preguntas.SUMADA)
        self.assertEqual(self.cola.pendientes()[7].texto, "Cambio")
        self.assertEqual(len(self.cola.pendientes()), preguntas.MAXIMO)


class TestOrden(Base):

    def test_la_siguiente_es_la_mas_vieja_pendiente(self):
        self._sumar("!pregunta Uno", "Ana", "A")
        self._sumar("!pregunta Dos", "Beto", "B")
        self.assertEqual(self.cola.siguiente().texto, "Uno")
        self.cola.responder(self.cola.siguiente().id)
        self.assertEqual(self.cola.siguiente().texto, "Dos")
        self.cola.responder(self.cola.siguiente().id)
        self.assertIsNone(self.cola.siguiente())


class TestAdministrar(Base):

    def test_responder_descartar_y_vaciar_sacan_de_la_cola(self):
        self._sumar("!pregunta Uno", "Ana", "A")
        self._sumar("!pregunta Dos", "Beto", "B")
        self._sumar("!pregunta Tres", "Carla", "C")
        pendientes = self.cola.pendientes()
        self.assertTrue(self.cola.responder(pendientes[0].id))
        self.assertFalse(self.cola.responder(pendientes[0].id))
        self.assertTrue(self.cola.descartar(pendientes[2].id))
        self.assertEqual([pregunta.texto for pregunta in self.cola.pendientes()],
                         ["Dos"])
        self.cola.vaciar()
        self.assertEqual(self.cola.pendientes(), [])
        self.assertIsNone(self.cola.siguiente())

    def test_avisa_a_los_suscritos_cada_vez_que_cambia(self):
        cambios = []
        self.cola.suscribir(lambda: cambios.append(1))
        self._sumar("!pregunta Uno", "Ana", "A")
        self._sumar("!pregunta Cambio", "Ana", "A")
        self._sumar("!pregunta")  # no cambia nada: no avisa
        self.assertEqual(len(cambios), 2)
        self.cola.responder(self.cola.pendientes()[0].id)
        self.assertEqual(len(cambios), 3)
        self._sumar("!pregunta Dos", "Beto", "B")
        self.cola.vaciar()
        self.assertEqual(len(cambios), 5)


class TestPropiedad(Base):

    def test_cualquier_secuencia_respeta_los_topes(self):
        azar = random.Random(7)
        personas = [(f"Persona {numero}", str(numero)) for numero in range(60)]
        for _ in range(400):
            accion = azar.choice(
                ("alta", "alta", "alta", "responder", "descartar", "vaciar"))
            if accion == "alta":
                autor, autor_id = azar.choice(personas)
                self._sumar(f"!pregunta Texto de {autor}", autor, autor_id)
            elif accion == "vaciar":
                self.cola.vaciar()
            else:
                pendientes = self.cola.pendientes()
                if pendientes:
                    getattr(self.cola, accion)(
                        azar.choice(pendientes).id)
            pendientes = self.cola.pendientes()
            self.assertLessEqual(len(pendientes), preguntas.MAXIMO)
            identidades = [pregunta.identidad for pregunta in pendientes]
            self.assertEqual(len(identidades), len(set(identidades)))


if __name__ == "__main__":
    unittest.main()
