# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de los escalones de la prueba del equipo, sin OBS ni ventanas."""

import unittest
from dataclasses import replace

from guyrapu.obs import ajustes_perfil, escalones_equipo


def _ajustes(**cambios):
    base = ajustes_perfil.AjustesPerfil(
        ancho_lienzo=1920, alto_lienzo=1080,
        ancho_salida=1920, alto_salida=1080,
        fps=60, codificador="x264", preset="veryfast")
    return replace(base, **cambios)


class TestOrden(unittest.TestCase):

    def test_con_grafica_baja_codificador_despues_fps_y_despues_720(self):
        pasos = escalones_equipo.escalones(_ajustes(), ("qsv", "x264"))
        self.assertEqual(
            [(paso.codificador, paso.fps, paso.ancho_salida, paso.alto_salida)
             for paso in pasos],
            [("x264", 60, 1920, 1080),
             ("qsv", 60, 1920, 1080),
             ("qsv", 30, 1920, 1080),
             ("qsv", 30, 1280, 720)])

    def test_sin_grafica_baja_fps_y_despues_720(self):
        pasos = escalones_equipo.escalones(_ajustes(), ("x264",))
        self.assertEqual(
            [(paso.codificador, paso.fps, paso.ancho_salida, paso.alto_salida)
             for paso in pasos],
            [("x264", 60, 1920, 1080),
             ("x264", 30, 1920, 1080),
             ("x264", 30, 1280, 720)])

    def test_en_vertical_el_escalon_de_720_es_vertical(self):
        pasos = escalones_equipo.escalones(
            _ajustes(ancho_lienzo=1080, alto_lienzo=1920,
                     ancho_salida=1080, alto_salida=1920), ("x264",))
        self.assertEqual((pasos[-1].ancho_salida, pasos[-1].alto_salida),
                         (720, 1280))

    def test_ningun_escalon_sube_un_ajuste(self):
        actual = _ajustes()
        siguiente = escalones_equipo.siguiente(actual, ("qsv", "x264"))
        while siguiente is not None:
            self.assertLessEqual(siguiente.fps, actual.fps)
            self.assertLessEqual(siguiente.alto_salida, actual.alto_salida)
            if actual.codificador == "x264":
                self.assertIn(siguiente.codificador, ("qsv", "x264"))
            else:
                self.assertEqual(siguiente.codificador, actual.codificador)
            actual, siguiente = siguiente, escalones_equipo.siguiente(
                siguiente, ("qsv", "x264"))


class TestAguanta(unittest.TestCase):

    def test_el_limite_de_dos_por_ciento_aguanta(self):
        self.assertTrue(escalones_equipo.aguanta(2, 100, 2, 100))

    def test_pasarse_del_dos_por_ciento_no_aguanta(self):
        self.assertFalse(escalones_equipo.aguanta(3, 100, 0, 100))
        self.assertFalse(escalones_equipo.aguanta(0, 100, 3, 100))

    def test_sin_fotogramas_no_aguanta(self):
        self.assertFalse(escalones_equipo.aguanta(0, 0, 0, 100))
        self.assertFalse(escalones_equipo.aguanta(0, 100, 0, 0))


class TestDescripciones(unittest.TestCase):

    def test_describe_los_ajustes_y_las_diferencias(self):
        antes = _ajustes()
        despues = replace(antes, codificador="qsv", fps=30,
                          ancho_salida=1280, alto_salida=720)
        frase = escalones_equipo.describir(antes)
        self.assertIn("Procesador (x264)", frase)
        self.assertIn("60 fotogramas", frase)
        self.assertIn("1920 por 1080", frase)
        cambios = escalones_equipo.diferencias(antes, despues)
        self.assertIn("Gráfica Intel (QuickSync)", cambios)
        self.assertIn("30", cambios)
        self.assertIn("1280 por 720", cambios)
        self.assertEqual(escalones_equipo.diferencias(antes, antes),
                         "Sin cambios.")


if __name__ == "__main__":
    unittest.main()
