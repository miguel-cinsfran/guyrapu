# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Reglas de una colección con nombre: copia, movimiento y combinación."""

import unittest

from guyrapu.interaction import coleccion


class TestNombreDeCopia(unittest.TestCase):
    def test_sin_choque_usa_la_copia_simple(self):
        self.assertEqual(coleccion.nombre_de_copia("Saludo", ["Otro"]),
                         "Saludo (copia)")

    def test_suma_numeros_mientras_el_nombre_exista(self):
        existentes = ["Saludo", "Saludo (copia)", "Saludo (copia 2)"]
        self.assertEqual(coleccion.nombre_de_copia("Saludo", existentes),
                         "Saludo (copia 3)")

    def test_compara_sin_mayusculas_ni_espacios_en_los_extremos(self):
        existentes = ["  saludo (COPIA) "]
        self.assertEqual(coleccion.nombre_de_copia("Saludo", existentes),
                         "Saludo (copia 2)")

    def test_acepta_elementos_con_nombre(self):
        existentes = [{"nombre": "Saludo (copia)"}]
        self.assertEqual(coleccion.nombre_de_copia("Saludo", existentes),
                         "Saludo (copia 2)")


class TestMover(unittest.TestCase):
    def setUp(self):
        self.lista = ["uno", "dos", "tres"]

    def test_mueve_un_lugar_y_devuelve_el_indice_nuevo(self):
        self.assertEqual(coleccion.mover(self.lista, 1, -1), 0)
        self.assertEqual(self.lista, ["dos", "uno", "tres"])

    def test_en_el_primero_no_hace_nada(self):
        self.assertIsNone(coleccion.mover(self.lista, 0, -1))
        self.assertEqual(self.lista, ["uno", "dos", "tres"])

    def test_en_el_ultimo_no_hace_nada(self):
        self.assertIsNone(coleccion.mover(self.lista, 2, 1))
        self.assertEqual(self.lista, ["uno", "dos", "tres"])

    def test_indice_fuera_de_rango(self):
        self.assertIsNone(coleccion.mover(self.lista, 3, -1))


class TestCombinar(unittest.TestCase):
    def setUp(self):
        self.existentes = [
            {"nombre": "Uno", "texto": "viejo"},
            {"nombre": "Dos", "texto": "dos"},
        ]

    def test_sin_reemplazar_agrega_al_final_con_nombre_de_copia(self):
        nuevos = [{"nombre": "Uno", "texto": "nuevo"}]
        resultado = coleccion.combinar(self.existentes, nuevos, False)
        self.assertEqual([m["nombre"] for m in resultado],
                         ["Uno", "Dos", "Uno (copia)"])
        self.assertEqual(resultado[-1]["texto"], "nuevo")
        self.assertEqual(self.existentes[0]["texto"], "viejo")

    def test_sin_reemplazar_compara_sin_mayusculas_ni_espacios(self):
        nuevos = [{"nombre": "  dOs ", "texto": "nuevo"}]
        resultado = coleccion.combinar(self.existentes, nuevos, False)
        self.assertEqual(resultado[-1]["nombre"], "  dOs  (copia)")

    def test_con_reemplazo_pone_cada_nuevo_en_el_lugar_del_que_tiene_su_nombre(self):
        nuevos = [{"nombre": "Dos", "texto": "nuevo"},
                  {"nombre": "Tres", "texto": "tres"}]
        resultado = coleccion.combinar(self.existentes, nuevos, True)
        self.assertEqual([m["nombre"] for m in resultado],
                         ["Uno", "Dos", "Tres"])
        self.assertEqual(resultado[1]["texto"], "nuevo")
        self.assertEqual(resultado[2]["texto"], "tres")

    def test_no_modifica_la_lista_recibida(self):
        original = list(self.existentes)
        coleccion.combinar(self.existentes, [{"nombre": "Tres"}], True)
        self.assertEqual(self.existentes, original)


if __name__ == "__main__":
    unittest.main()
