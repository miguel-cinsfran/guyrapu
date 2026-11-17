# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de las tipografías de Windows y del corte de avisos en líneas."""

import unittest

from guyrapu.obs import fuentes_windows


def _diez(texto):
    """Cada carácter mide diez píxeles."""
    return len(texto) * 10


class TestFamilias(unittest.TestCase):
    def test_incluye_segoe_ui_sin_verticales_y_una_vez_cada_una(self):
        familias = fuentes_windows.familias()
        self.assertIn("Segoe UI", familias)
        self.assertEqual([], [nombre for nombre in familias
                              if nombre.startswith("@")])
        self.assertEqual(len(familias), len(set(familias)))


class TestMedidor(unittest.TestCase):
    def test_mide_con_la_familia_el_tamano_y_el_peso(self):
        normal = fuentes_windows.medidor("Segoe UI", 54, False)
        negrita = fuentes_windows.medidor("Segoe UI", 54, True)
        corto = normal("Hola")
        largo = normal("Hola a todos")
        self.assertGreater(corto, 0)
        self.assertLess(corto, largo)
        self.assertGreaterEqual(negrita("Hola"), corto)

    def test_quinientos_medidores_no_rompen_el_siguiente(self):
        for _ in range(500):
            fuentes_windows.medidor("Segoe UI", 54, False)
        siguiente = fuentes_windows.medidor("Segoe UI", 54, False)
        self.assertGreater(siguiente("Hola"), 0)


class TestPartirEnLineas(unittest.TestCase):
    def test_un_texto_que_entra_en_una_linea(self):
        self.assertEqual(
            fuentes_windows.partir_en_lineas("uno dos", 70, _diez),
            ["uno dos"])

    def test_llena_la_linea_con_dos_palabras_enteras(self):
        self.assertEqual(
            fuentes_windows.partir_en_lineas(
                "uno dos tres cuatro", 110, _diez),
            ["uno dos", "tres cuatro"])

    def test_respeta_un_salto_de_linea_del_texto(self):
        self.assertEqual(
            fuentes_windows.partir_en_lineas("uno\ndos tres", 80, _diez),
            ["uno", "dos tres"])

    def test_conserva_la_linea_en_blanco_del_texto(self):
        self.assertEqual(
            fuentes_windows.partir_en_lineas("uno\n\ndos", 70, _diez),
            ["uno", "", "dos"])

    def test_parte_por_caracteres_una_palabra_que_no_entra(self):
        self.assertEqual(
            fuentes_windows.partir_en_lineas("a" * 30, 100, _diez),
            ["a" * 10, "a" * 10, "a" * 10])

    def test_ancho_menor_o_igual_a_cero_se_toma_como_uno(self):
        self.assertEqual(
            fuentes_windows.partir_en_lineas("uno dos", 0, lambda _texto: 1),
            ["uno dos"])

    def test_sin_espacios_en_los_bordes_y_mismas_palabras(self):
        lineas = fuentes_windows.partir_en_lineas(
            "  uno  dos tres   cuatro  ", 70, _diez)
        for linea in lineas:
            self.assertEqual(linea, linea.strip())
        self.assertEqual(" ".join(lineas).split(),
                         "uno dos tres cuatro".split())
        partida = fuentes_windows.partir_en_lineas("b" * 30, 100, _diez)
        for linea in partida:
            self.assertEqual(linea, linea.strip())


if __name__ == "__main__":
    unittest.main()
