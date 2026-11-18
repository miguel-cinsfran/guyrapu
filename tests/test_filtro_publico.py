# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Qué parte del texto del público puede mostrarse.

Puro y sin captura.
"""

import tempfile
import unittest
from pathlib import Path

from guyrapu.interaction import filtro_publico


class TestTapar(unittest.TestCase):

    def test_tapa_la_palabra_entera_sin_distinguir_mayusculas(self):
        self.assertEqual(
            filtro_publico.tapar("Ese TONTO es tonto", ["tonto"]),
            "Ese *** es ***")

    def test_no_toca_una_palabra_que_solo_empieza_igual(self):
        self.assertEqual(
            filtro_publico.tapar("Es un tontolín", ["tonto"]),
            "Es un tontolín")

    def test_no_distingue_tildes(self):
        self.assertEqual(
            filtro_publico.tapar("Canta una CANCION", ["canción"]),
            "Canta una ***")

    def test_la_ene_es_distinta(self):
        self.assertEqual(
            filtro_publico.tapar("Un ano y un año", ["ano"]),
            "Un *** y un año")
        self.assertEqual(
            filtro_publico.tapar("Un ano y un año", ["año"]),
            "Un ano y un ***")

    def test_una_entrada_de_varias_palabras_se_busca_como_frase(self):
        self.assertEqual(
            filtro_publico.tapar("Eso es una mala palabra", ["mala palabra"]),
            "Eso es una ***")
        self.assertEqual(
            filtro_publico.tapar("Eso es una mala palabra", ["mala"]),
            "Eso es una *** palabra")

    def test_sin_bloqueadas_deja_el_texto_igual(self):
        self.assertEqual(filtro_publico.tapar("Hola mundo", []), "Hola mundo")


class TestSimbolos(unittest.TestCase):

    def test_menos_de_ocho_caracteres_no_cuenta(self):
        self.assertFalse(filtro_publico.es_casi_todo_simbolos("!!!!!!!"))

    def test_ocho_caracteres_o_mas_casi_todos_simbolos(self):
        self.assertTrue(filtro_publico.es_casi_todo_simbolos("!!!!!!!a"))

    def test_justo_en_el_sesenta_por_ciento_no_cuenta(self):
        self.assertFalse(filtro_publico.es_casi_todo_simbolos("abcd!!!!!!"))

    def test_por_encima_del_sesenta_por_ciento_cuenta(self):
        self.assertTrue(filtro_publico.es_casi_todo_simbolos("abc!!!!!!!"))

    def test_los_espacios_no_cuentan(self):
        self.assertTrue(filtro_publico.es_casi_todo_simbolos("       a!!!!!!!"))

    def test_los_emojis_cuentan_como_simbolos(self):
        self.assertTrue(filtro_publico.es_casi_todo_simbolos("😀😀😀😀😀😀abc"))

    def test_letras_y_cifras_no_son_simbolos(self):
        self.assertFalse(filtro_publico.es_casi_todo_simbolos("texto12345"))


class TestArchivo(unittest.TestCase):

    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)
        self.ruta = Path(self.temporal.name) / "palabras_bloqueadas.json"

    def test_un_archivo_roto_da_lista_vacia(self):
        self.ruta.write_text("{roto", encoding="utf-8")
        self.assertEqual(filtro_publico.cargar(self.ruta), [])

    def test_un_archivo_ausente_da_lista_vacia(self):
        self.assertEqual(filtro_publico.cargar(self.ruta), [])

    def test_guarda_y_carga_la_lista(self):
        filtro_publico.guardar(self.ruta, ["tonto", "mala palabra"])
        self.assertEqual(filtro_publico.cargar(self.ruta),
                         ["tonto", "mala palabra"])


if __name__ == "__main__":
    unittest.main()
