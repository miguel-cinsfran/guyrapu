# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas puras de la seguridad del carril: corte, guardia y devolución."""

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from qa.nvda import correr, devolver, nvda_local, seguridad

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


class TestEjecutarDevolucion(unittest.TestCase):

    def _estado(self, datos):
        carpeta = tempfile.TemporaryDirectory()
        self.addCleanup(carpeta.cleanup)
        ruta = Path(carpeta.name) / "estado-carril.json"
        ruta.write_text(json.dumps(datos), encoding="utf-8")
        return ruta

    def test_cerrar_fallido_devuelve_falso_y_conserva_el_estado(self):
        ruta = self._estado({"habia": False, "ejecutable": None})
        actual = {"pid": 4, "ejecutable": PORTATIL_EXE}
        with (
            mock.patch.object(nvda_local, "nvda_en_marcha",
                              return_value=actual),
            mock.patch.object(nvda_local, "cerrar", return_value=False),
        ):
            self.assertFalse(
                devolver.ejecutar_devolucion(ruta, PORTATIL, INSTALADO))
        self.assertTrue(ruta.exists())

    def test_cerrar_logrado_devuelve_verdadero_y_borra_el_estado(self):
        ruta = self._estado({"habia": False, "ejecutable": None})
        actual = {"pid": 4, "ejecutable": PORTATIL_EXE}
        with (
            mock.patch.object(nvda_local, "nvda_en_marcha",
                              return_value=actual),
            mock.patch.object(nvda_local, "cerrar", return_value=True),
        ):
            self.assertTrue(
                devolver.ejecutar_devolucion(ruta, PORTATIL, INSTALADO))
        self.assertFalse(ruta.exists())

    def test_nada_devuelve_verdadero(self):
        ruta = self._estado({"habia": False, "ejecutable": None})
        with mock.patch.object(nvda_local, "nvda_en_marcha",
                               return_value=None):
            self.assertTrue(
                devolver.ejecutar_devolucion(ruta, PORTATIL, INSTALADO))
        self.assertFalse(ruta.exists())

    def test_lanzar_devuelve_verdadero(self):
        ruta = self._estado({"habia": True, "ejecutable": INSTALADO})
        with (
            mock.patch.object(nvda_local, "nvda_en_marcha",
                              return_value=None),
            mock.patch.object(nvda_local, "lanzar") as lanzar,
        ):
            self.assertTrue(
                devolver.ejecutar_devolucion(ruta, PORTATIL, INSTALADO))
        lanzar.assert_called_once_with(INSTALADO)
        self.assertFalse(ruta.exists())


class TestRespaldoSeConserva(unittest.TestCase):

    def _ejecutar(self, actuales, cerrar_ok):
        carpeta = tempfile.TemporaryDirectory()
        self.addCleanup(carpeta.cleanup)
        ruta_estado = Path(carpeta.name) / "estado-carril.json"
        args = SimpleNamespace(sin_espera=True, una_pc=True,
                               respaldo_minutos=45, canario=False)
        with (
            mock.patch.object(correr, "_guardia", return_value=None),
            mock.patch.object(
                correr, "_elegir_copia",
                return_value=(Path(PORTATIL), INSTALADO, "usar")),
            mock.patch.object(correr.perfil, "ruta_estado",
                              return_value=ruta_estado),
            mock.patch.object(correr.nvda_local, "nvda_en_marcha",
                              side_effect=actuales),
            mock.patch.object(correr.nvda_local, "cerrar",
                              return_value=cerrar_ok),
            mock.patch.object(correr.seguridad, "Vigilante",
                              return_value=mock.Mock(cortado=False)),
            mock.patch.object(correr, "_programar_respaldo",
                              return_value=True),
            mock.patch.object(correr, "_con_canario", return_value=0),
            mock.patch.object(correr.seguridad,
                              "borrar_respaldo") as borrar,
        ):
            codigo = correr.ejecutar(args)
        self.assertEqual(codigo, correr.COD_OK)
        return borrar

    def test_si_no_se_pudo_cerrar_el_portatil_no_borra_el_respaldo(self):
        borrar = self._ejecutar(
            [None, {"pid": 4, "ejecutable": PORTATIL_EXE}], False)
        borrar.assert_not_called()

    def test_si_no_habia_nada_borra_el_respaldo(self):
        borrar = self._ejecutar([None, None], False)
        borrar.assert_called_once_with(seguridad.NOMBRE_RESPALDO)


class TestArranque(unittest.TestCase):

    def test_lanzar_y_crear_portatil_van_por_shell_execute(self):
        with tempfile.TemporaryDirectory() as base:
            with (
                mock.patch.object(nvda_local, "ejecutar_shell",
                                  create=True, side_effect=[0, 3]) as shell,
                mock.patch("subprocess.Popen") as popen,
                mock.patch("subprocess.run") as run,
            ):
                self.assertEqual(
                    nvda_local.lanzar(INSTALADO, ["-c", r"C:\perfil"]), 0)
                self.assertEqual(
                    nvda_local.crear_portatil(INSTALADO, Path(base)), 3)
        popen.assert_not_called()
        run.assert_not_called()
        primera, segunda = shell.call_args_list
        self.assertEqual(primera.args[0], INSTALADO)
        self.assertEqual(primera.args[1], ["-c", r"C:\perfil"])
        self.assertFalse(primera.kwargs.get("esperar", False))
        self.assertEqual(segunda.args[0], INSTALADO)
        self.assertTrue(segunda.kwargs["esperar"])
        self.assertEqual(segunda.kwargs["tope_s"], 600.0)

    def test_shell_execute_de_verdad_devuelve_el_codigo_de_salida(self):
        comando = os.environ.get("COMSPEC",
                                 r"C:\Windows\System32\cmd.exe")
        codigo = nvda_local.ejecutar_shell(
            comando, ["/c", "exit", "3"], esperar=True, tope_s=30.0)
        self.assertEqual(codigo, 3)


class TestDevolverMain(unittest.TestCase):

    def _main(self, devuelto):
        with (
            mock.patch.object(devolver.perfil, "version_esperada",
                              return_value="2026.3.1"),
            mock.patch.object(devolver.perfil, "ruta_portatil",
                              return_value=Path(PORTATIL)),
            mock.patch.object(devolver.perfil, "ruta_estado",
                              return_value=Path("estado.json")),
            mock.patch.object(devolver.nvda_local,
                              "instalado_por_defecto",
                              return_value=INSTALADO),
            mock.patch.object(devolver, "ejecutar_devolucion",
                              return_value=devuelto),
            mock.patch.object(seguridad, "borrar_respaldo") as borrar,
        ):
            codigo = devolver.main()
        self.assertEqual(codigo, 0)
        return borrar

    def test_si_devuelve_borra_la_tarea_de_respaldo(self):
        borrar = self._main(True)
        borrar.assert_called_once_with(seguridad.NOMBRE_RESPALDO)

    def test_si_no_devuelve_deja_la_tarea_de_respaldo(self):
        borrar = self._main(False)
        borrar.assert_not_called()
