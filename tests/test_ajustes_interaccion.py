# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Los ajustes generales de la interacción y cómo se combinan con los medios."""

import json
import tempfile
import unittest
from pathlib import Path

from guyrapu.interaction import ajustes_interaccion


class BaseAjustes(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.ruta = Path(self.tmp.name) / "interaccion.json"


class TestVolumenGuardado(BaseAjustes):

    def test_sin_archivo_da_cien(self):
        self.assertEqual(
            ajustes_interaccion.cargar_volumen(self.ruta), 100)

    def test_archivo_roto_da_cien(self):
        self.ruta.write_text("{roto", encoding="utf-8")
        self.assertEqual(
            ajustes_interaccion.cargar_volumen(self.ruta), 100)

    def test_valor_fuera_de_rango_da_cien(self):
        for valor in (-1, 101):
            with self.subTest(valor=valor):
                self.ruta.write_text(
                    json.dumps({"volumen_medios": valor}), encoding="utf-8")
                self.assertEqual(
                    ajustes_interaccion.cargar_volumen(self.ruta), 100)

    def test_guarda_bajo_la_clave_y_lo_vuelve_a_leer(self):
        ajustes_interaccion.guardar_volumen(self.ruta, 40)
        self.assertEqual(
            json.loads(self.ruta.read_text(encoding="utf-8")),
            {"volumen_medios": 40})
        self.assertEqual(
            ajustes_interaccion.cargar_volumen(self.ruta), 40)


class TestGananciaTotal(unittest.TestCase):

    def test_con_cien_por_ciento_conserva_la_ganancia(self):
        self.assertAlmostEqual(
            ajustes_interaccion.ganancia_total(-6.0, 100), -6.0)

    def test_sin_ganancia_con_cien_por_ciento_da_cero(self):
        self.assertAlmostEqual(
            ajustes_interaccion.ganancia_total(None, 100), 0.0)

    def test_con_cincuenta_por_ciento_resta_seis_db(self):
        self.assertAlmostEqual(
            ajustes_interaccion.ganancia_total(-6.0, 50), -12.0206,
            places=4)

    def test_con_cero_por_ciento_da_menos_cien(self):
        self.assertEqual(
            ajustes_interaccion.ganancia_total(-6.0, 0), -100.0)
