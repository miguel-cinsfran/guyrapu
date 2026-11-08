# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas puras de la lista de canciones que se edita, sin interfaz."""

import random
import unittest

from guyrapu.music.edicion_lista import ListaEnEdicion
from guyrapu.music.modelo import Tema


A = Tema("C:/Musica/a.mp3", "A")
B = Tema("C:/Musica/b.mp3", "B")
C = Tema("C:/Musica/c.mp3", "C")


class TestCrear(unittest.TestCase):

    def test_guarda_el_orden(self):
        lista = ListaEnEdicion((B, A, C))
        self.assertEqual(lista.temas, (B, A, C))

    def test_con_repetidas_queda_la_primera_aparicion(self):
        lista = ListaEnEdicion((B, A, B, C, A))
        self.assertEqual(lista.temas, (B, A, C))

    def test_sin_temas_queda_vacia(self):
        self.assertEqual(ListaEnEdicion().temas, ())

    def test_contiene_compara_por_origen(self):
        copia = Tema(A.origen, "Otro título")
        lista = ListaEnEdicion((A,))
        self.assertTrue(lista.contiene(copia))
        self.assertFalse(lista.contiene(B))


class TestAgregar(unittest.TestCase):

    def test_agrega_al_final(self):
        lista = ListaEnEdicion((A,))
        self.assertTrue(lista.agregar(B))
        self.assertEqual(lista.temas, (A, B))

    def test_una_que_ya_esta_devuelve_false_y_no_cambia(self):
        lista = ListaEnEdicion((A, B))
        self.assertFalse(lista.agregar(Tema(A.origen, "Otra")))
        self.assertEqual(lista.temas, (A, B))


class TestQuitar(unittest.TestCase):

    def test_quitar_devuelve_el_indice(self):
        lista = ListaEnEdicion((A, B, C))
        self.assertEqual(lista.quitar(B), 1)
        self.assertEqual(lista.temas, (A, C))

    def test_quitar_una_que_no_esta_devuelve_none(self):
        lista = ListaEnEdicion((A,))
        self.assertIsNone(lista.quitar(B))
        self.assertEqual(lista.temas, (A,))

    def test_quitar_en_devuelve_el_tema(self):
        lista = ListaEnEdicion((A, B, C))
        self.assertEqual(lista.quitar_en(1), B)
        self.assertEqual(lista.temas, (A, C))

    def test_quitar_en_fuera_de_rango_devuelve_none(self):
        lista = ListaEnEdicion((A,))
        for indice in (-1, 1, 99):
            with self.subTest(indice=indice):
                self.assertIsNone(lista.quitar_en(indice))
        self.assertEqual(lista.temas, (A,))

    def test_despues_de_quitar_se_puede_volver_a_agregar(self):
        lista = ListaEnEdicion((A, B))
        lista.quitar(A)
        self.assertTrue(lista.agregar(A))
        self.assertEqual(lista.temas, (B, A))


class TestMover(unittest.TestCase):

    def test_mueve_un_lugar(self):
        lista = ListaEnEdicion((A, B, C))
        self.assertEqual(lista.mover(0, 1), 1)
        self.assertEqual(lista.temas, (B, A, C))
        self.assertEqual(lista.mover(1, -1), 0)
        self.assertEqual(lista.temas, (A, B, C))

    def test_en_el_borde_de_arriba_no_mueve(self):
        lista = ListaEnEdicion((A, B))
        self.assertEqual(lista.mover(0, -1), 0)
        self.assertEqual(lista.temas, (A, B))

    def test_en_el_borde_de_abajo_no_mueve(self):
        lista = ListaEnEdicion((A, B))
        self.assertEqual(lista.mover(1, 1), 1)
        self.assertEqual(lista.temas, (A, B))


class TestNuncaSeRepite(unittest.TestCase):

    def test_cualquier_secuencia_deja_origenes_unicos(self):
        azar = random.Random(20261107)
        canciones = (A, B, C)
        for _caso in range(200):
            lista = ListaEnEdicion(azar.sample(canciones, azar.randint(0, 3)))
            for _paso in range(20):
                operacion = azar.randint(0, 3)
                if operacion == 0:
                    lista.agregar(azar.choice(canciones))
                elif operacion == 1:
                    lista.quitar(azar.choice(canciones))
                elif operacion == 2:
                    lista.quitar_en(azar.randint(-1, 3))
                else:
                    lista.mover(azar.randint(-1, 3), azar.choice((-1, 1)))
                origenes = [tema.origen for tema in lista.temas]
                self.assertEqual(len(origenes), len(set(origenes)), origenes)


if __name__ == "__main__":
    unittest.main()
