# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas puras de la seguridad del carril: corte, guardia y devolución."""

import json
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

from qa.nvda import devolver, nvda_local, seguridad

INSTALADO = r"C:\Program Files\NVDA\nvda.exe"
PORTATIL = r"C:\Local\guyrapu-qa\nvda-2026.3.1"
PORTATIL_EXE = PORTATIL + r"\nvda.exe"


class TestCorte(unittest.TestCase):

    def test_teclado_sin_marca_de_inyectado_corta(self):
        self.assertTrue(seguridad.es_fisico("teclado", 0))

    def test_teclado_inyectado_no_corta(self):
        self.assertFalse(seguridad.es_fisico(
            "teclado", seguridad.LLKHF_INJECTED))

    def test_raton_sin_marca_de_inyectado_corta(self):
        self.assertTrue(seguridad.es_fisico("raton", 0))

    def test_raton_inyectado_no_corta(self):
        self.assertFalse(seguridad.es_fisico(
            "raton", seguridad.LLMHF_INJECTED))

    def test_un_tipo_desconocido_es_un_error(self):
        with self.assertRaises(ValueError):
            seguridad.es_fisico("braille", 0)


class TestGuardia(unittest.TestCase):

    def test_con_entrada_hace_nueve_minutos_se_niega(self):
        permitido, motivo = seguridad.decidir_guardia(9 * 60)
        self.assertFalse(permitido)
        self.assertIn("540", motivo)
        self.assertIn("10 minutos", motivo)

    def test_sin_entrada_hace_once_minutos_permite(self):
        permitido, _ = seguridad.decidir_guardia(11 * 60)
        self.assertTrue(permitido)

    def test_sin_espera_exige_el_modo_de_una_sola_pc(self):
        with self.assertRaises(seguridad.ModoRequerido):
            seguridad.decidir_guardia(10, sin_espera=True)
        permitido, _ = seguridad.decidir_guardia(
            10, sin_espera=True, una_pc=True)
        self.assertTrue(permitido)


class TestEstado(unittest.TestCase):

    def test_anota_cuando_habia_uno(self):
        self.assertEqual(
            seguridad.estado_inicial(
                {"pid": 3, "ejecutable": INSTALADO}),
            {"habia": True, "ejecutable": INSTALADO, "pid": 3})

    def test_anota_cuando_no_habia(self):
        self.assertEqual(seguridad.estado_inicial(None),
                         {"habia": False, "ejecutable": None})

    def test_escribe_el_estado_en_json(self):
        with tempfile.TemporaryDirectory() as base:
            ruta = Path(base) / "estado-carril.json"
            seguridad.escribir_estado(ruta, {"habia": False})
            self.assertEqual(json.loads(ruta.read_text(encoding="utf-8")),
                             {"habia": False})


class TestRespaldo(unittest.TestCase):

    def test_el_momento_suma_los_minutos(self):
        ahora = datetime(2026, 11, 16, 12, 0)
        self.assertEqual(seguridad.momento_respaldo(45, ahora), datetime(
            2026, 11, 16, 12, 45))
        self.assertEqual(seguridad.momento_respaldo(2, ahora), datetime(
            2026, 11, 16, 12, 2))

    def test_linea_comando_entrecomilla_las_dos_rutas(self):
        self.assertEqual(
            seguridad.linea_comando(r"C:\py\python.exe", r"C:\qa\devolver.py"),
            '"C:\\py\\python.exe" "C:\\qa\\devolver.py"')

    def test_crea_la_tarea_sin_pedir_contrasena(self):
        momento = datetime(2026, 11, 16, 12, 45)
        with mock.patch("qa.nvda.seguridad.subprocess.run") as correr:
            correr.return_value.returncode = 0
            correr.return_value.stdout = "ok"
            correr.return_value.stderr = ""
            creado, _ = seguridad.crear_respaldo(
                "GuyrapuCarrilNVDA", momento, '"python" "devolver.py"')
        self.assertTrue(creado)
        argumentos = correr.call_args[0][0]
        self.assertIn("GuyrapuCarrilNVDA", argumentos)
        self.assertIn("ONCE", argumentos)
        self.assertIn("12:45", argumentos)
        self.assertIn("/IT", argumentos)


class TestWindows(unittest.TestCase):

    def test_la_version_de_un_ejecutable_real_se_lee(self):
        kernel32 = Path(sys.executable).anchor + r"Windows\System32\kernel32.dll"
        leida = nvda_local.version_de_ejecutable(kernel32)
        self.assertRegex(leida, r"^\d+\.\d+")

    def test_la_fecha_local_lleva_el_anio(self):
        fecha = seguridad.fecha_local(datetime(2026, 11, 16, 12, 45))
        self.assertIn("2026", fecha)

    def test_el_tiempo_desde_la_ultima_entrada_no_es_negativo(self):
        self.assertGreaterEqual(
            seguridad.segundos_desde_ultima_entrada(), 0.0)


class TestVersionPortatil(unittest.TestCase):

    def test_normaliza_a_tres_numeros(self):
        self.assertEqual(
            nvda_local.normalizar_version("2026.3.1.55980"), "2026.3.1")

    def test_usa_la_copia_si_ya_existe(self):
        self.assertEqual(
            nvda_local.decidir_copia(True, "2026.1.1", "2026.3.1"), "usar")

    def test_arma_la_copia_si_la_instalada_es_la_misma(self):
        self.assertEqual(
            nvda_local.decidir_copia(False, "2026.3.1.55980", "2026.3.1"),
            "armar")

    def test_se_niega_diciendo_las_dos_versiones(self):
        with self.assertRaises(nvda_local.VersionInvalida) as capturado:
            nvda_local.decidir_copia(False, "2026.1.1.55980", "2026.3.1")
        self.assertIn("2026.3.1", str(capturado.exception))
        self.assertIn("2026.1.1", str(capturado.exception))


class TestDevolucion(unittest.TestCase):

    def test_sin_estado_no_hace_nada(self):
        self.assertEqual(
            devolver.decidir_devolucion(None, None, PORTATIL, INSTALADO),
            ("nada", None))

    def test_si_habia_uno_arranca_el_anotado(self):
        estado = {"habia": True, "ejecutable": INSTALADO}
        self.assertEqual(
            devolver.decidir_devolucion(estado, None, PORTATIL, INSTALADO),
            ("lanzar", INSTALADO))

    def test_si_no_habia_cierra_la_copia_portatil(self):
        estado = {"habia": False, "ejecutable": None}
        actual = {"pid": 4, "ejecutable": PORTATIL_EXE}
        self.assertEqual(
            devolver.decidir_devolucion(
                estado, actual, PORTATIL, INSTALADO),
            ("cerrar", None))

    def test_si_lo_anotado_era_el_portatil_arranca_el_instalado(self):
        estado = {"habia": True, "ejecutable": PORTATIL_EXE}
        self.assertEqual(
            devolver.decidir_devolucion(estado, None, PORTATIL, INSTALADO),
            ("lanzar", INSTALADO))

    def test_si_ya_esta_devuelto_no_hace_nada(self):
        estado = {"habia": True, "ejecutable": INSTALADO}
        actual = {"pid": 4, "ejecutable": INSTALADO}
        self.assertEqual(
            devolver.decidir_devolucion(
                estado, actual, PORTATIL, INSTALADO),
            ("nada", None))
