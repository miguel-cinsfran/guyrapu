# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de la tabla de atributos que publican los motores de voz."""

import unittest

from guyrapu.core import atributos_voz


class TestTabla(unittest.TestCase):

    def test_calidad_va_en_la_fila_y_en_detalles(self):
        atributos = {"calidad": "high"}
        self.assertEqual(atributos_voz.textos_fila(atributos),
                         ["calidad alta"])
        self.assertEqual(
            atributos_voz.lineas_detalles(atributos, "Piper"),
            ["Calidad según Piper: alta."])

    def test_edad_solo_va_en_detalles(self):
        atributos = {"edad": "Young Adult"}
        self.assertEqual(atributos_voz.textos_fila(atributos), [])
        self.assertEqual(
            atributos_voz.lineas_detalles(atributos, "Phonon"),
            ["Edad según Phonon: adulto joven."])

    def test_descarta_un_atributo_y_un_valor_que_no_conoce(self):
        atributos = {"calidad": "altísima", "inventado": "algo"}
        self.assertEqual(atributos_voz.textos_fila(atributos), [])
        self.assertEqual(atributos_voz.lineas_detalles(atributos, "Piper"), [])

    def test_todos_los_valores_publicados_tienen_texto(self):
        casos = (
            ("calidad", "x_low", "muy baja"),
            ("calidad", "low", "baja"),
            ("calidad", "medium", "media"),
            ("calidad", "high", "alta"),
            ("edad", "Young", "joven"),
            ("edad", "Young Adult", "adulto joven"),
            ("edad", "Adult", "adulto"),
            ("edad", "Middle-age", "mediana edad"),
            ("edad", "Older Adult", "adulto mayor"),
        )
        for clave, valor, texto in casos:
            with self.subTest(valor=valor):
                self.assertEqual(
                    atributos_voz.lineas_detalles({clave: valor}, "Motor"),
                    [f"{clave.capitalize()} según Motor: {texto}."])
