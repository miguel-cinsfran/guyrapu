# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de la traducción de una tecla física.

Las de dobles no tocan Windows: usan una API falsa con los teclados
instalados. La última clase llama de verdad a Windows con el teclado
activo, sin abrir ventanas.
"""

import sys
import unittest
from unittest import mock

from guyrapu.core import tecla_fisica
from guyrapu.ui import atajos_captura


LATINOAMERICANO = 0x080A
ESPANA = 0x0C0A
ESTADOS_UNIDOS = 0x0409


class _ApiFalsa:
    """Doble de user32 con los teclados, sus virtuales y sus caracteres."""

    def __init__(self, teclados, virtuales, caracteres, activo=None):
        self.teclados = list(teclados)
        self.virtuales = dict(virtuales)
        self.caracteres = dict(caracteres)
        self.activo = self.teclados[0] if activo is None else activo

    def GetKeyboardLayoutList(self, cantidad, buffer):
        if not buffer:
            return len(self.teclados)
        for indice, teclado in enumerate(self.teclados[:cantidad]):
            buffer[indice] = teclado
        return min(cantidad, len(self.teclados))

    def GetKeyboardLayout(self, _hilo):
        return self.activo

    def MapVirtualKeyExW(self, exploracion, _tipo, teclado):
        return self.virtuales.get((exploracion, teclado), 0)

    def ToUnicodeEx(self, virtual, _exploracion, _estado, buffer, _tamano,
                    _bandera, teclado):
        texto = self.caracteres.get((virtual, teclado), "")
        buffer.value = texto
        return len(texto)


def _api_con_los_tres_teclados(activo=LATINOAMERICANO):
    return _ApiFalsa(
        teclados=[LATINOAMERICANO, ESPANA, ESTADOS_UNIDOS],
        virtuales={
            (0x0C, LATINOAMERICANO): 0xDB, (0x0C, ESPANA): 0xDB,
            (0x0C, ESTADOS_UNIDOS): 0xBD,
            (0x0D, LATINOAMERICANO): 0xDD, (0x0D, ESPANA): 0xDD,
            (0x0D, ESTADOS_UNIDOS): 0xBB,
        },
        caracteres={
            (0xDB, LATINOAMERICANO): "'", (0xDB, ESPANA): "'",
            (0xBD, ESTADOS_UNIDOS): "-",
            (0xDD, LATINOAMERICANO): "¿", (0xDD, ESPANA): "¡",
            (0xBB, ESTADOS_UNIDOS): "=",
        },
        activo=activo)


class TestTecladosDoblados(unittest.TestCase):

    def test_cada_teclado_da_su_tecla_virtual(self):
        api = _api_con_los_tres_teclados()
        self.assertEqual(tecla_fisica.teclas_virtuales(0x0C, api),
                         [0xDB, 0xBD])
        self.assertEqual(tecla_fisica.teclas_virtuales(0x0D, api),
                         [0xDD, 0xBB])

    def test_una_tecla_virtual_repetida_sale_una_sola_vez(self):
        api = _api_con_los_tres_teclados()
        self.assertEqual(tecla_fisica.teclas_virtuales(0x0C, api).count(0xDB),
                         1)

    def test_cada_teclado_da_su_caracter(self):
        api = _api_con_los_tres_teclados()
        self.assertEqual(tecla_fisica.caracter(0x0D, LATINOAMERICANO, api),
                         "¿")
        self.assertEqual(tecla_fisica.caracter(0x0D, ESPANA, api), "¡")
        self.assertEqual(tecla_fisica.caracter(0x0D, ESTADOS_UNIDOS, api),
                         "=")

    def test_el_texto_legible_usa_el_caracter_del_teclado_activo(self):
        api = _api_con_los_tres_teclados(activo=LATINOAMERICANO)
        with mock.patch.object(tecla_fisica, "_obtener_user32",
                               return_value=api):
            self.assertEqual(
                atajos_captura.atajo_legible("ctrl+shift+sc0c"),
                "Ctrl+Mayús+'")
            self.assertEqual(
                atajos_captura.atajo_legible("ctrl+shift+sc0d"),
                "Ctrl+Mayús+¿")

    def test_sin_caracter_legible_usa_el_nombre_de_estados_unidos(self):
        api = _ApiFalsa(
            teclados=[ESTADOS_UNIDOS],
            virtuales={(0x0D, ESTADOS_UNIDOS): 0xBB},
            caracteres={},
            activo=ESTADOS_UNIDOS)
        self.assertEqual(tecla_fisica.texto_tecla(0x0D, api), "=")


@unittest.skipUnless(sys.platform == "win32",
                     "las teclas virtuales solo existen en Windows")
class TestTecladoReal(unittest.TestCase):

    def test_las_dos_teclas_fisicas_dan_teclas_virtuales(self):
        for exploracion in (0x0C, 0x0D):
            with self.subTest(exploracion=exploracion):
                codigos = tecla_fisica.teclas_virtuales(exploracion)
                self.assertTrue(codigos)
                self.assertTrue(all(codigos))


if __name__ == "__main__":
    unittest.main()
