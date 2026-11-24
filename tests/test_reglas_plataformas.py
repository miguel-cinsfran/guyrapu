# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Prueba del detector de ids de plataforma escritos como literal."""

import ast
import textwrap
import unittest

from tests.reglas_plataformas import detectar_ids_de_plataforma


def _lineas(codigo, archivo="fragmento.py"):
    arbol = ast.parse(textwrap.dedent(codigo))
    return [hallazgo.linea
            for hallazgo in detectar_ids_de_plataforma(archivo, arbol)]


class TestDetectorDeIdsDePlataforma(unittest.TestCase):

    def test_ids_sueltos_dan_hallazgo(self):
        self.assertEqual([1, 2], _lineas("""\
            youtube_id = "youtube"
            tiktok_id = "tiktok"
            """))

    def test_lo_que_no_es_id_no_da_hallazgo(self):
        self.assertEqual([], _lineas("""\
            otro = "youtube_api"
            desde = plataformas.YOUTUBE
            hasta = plataformas.TIKTOK
            """))

    def test_el_registro_de_plataformas_no_da_hallazgo(self):
        self.assertEqual([], _lineas('identificador = "youtube"',
                                      "guyrapu/core/plataformas.py"))
