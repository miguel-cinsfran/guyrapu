# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas del flujo de `qa/nvda/correr.py` con dobles, sin NVDA ni ventanas.

Se prueban la guardia, el corte, el respaldo y el paso del canario por las
funciones que los usan, con `seguridad`, `nvda_local`, `perfil`, `devolver`
y el cliente sustituidos. No se abre ninguna ventana ni se toca una tarea
programada.
"""

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from qa.nvda import correr, devolver, nvda_local, seguridad

INSTALADO = r"C:\Program Files\NVDA\nvda.exe"


class TestGuardia(unittest.TestCase):

    def test_entrada_fisica_reciente_no_toca_nada(self):
        args = SimpleNamespace(sin_espera=False, una_pc=False,
                               respaldo_minutos=45, canario=True)
        with (
            mock.patch.object(correr.seguridad,
                              "segundos_desde_ultima_entrada",
                              return_value=60),
            mock.patch.object(
                correr, "_elegir_copia",
                return_value=(Path("copia"), INSTALADO, "usar")),
            mock.patch.object(correr.perfil, "version_esperada",
                              return_value="2026.3.1"),
            mock.patch.object(correr.perfil, "ruta_estado",
                              return_value=Path("estado.json")),
            mock.patch.object(correr.nvda_local, "nvda_en_marcha",
                              return_value=None),
            mock.patch.object(correr.nvda_local, "cerrar") as cerrar,
            mock.patch.object(correr.seguridad,
                              "escribir_estado") as escribir,
            mock.patch.object(
                correr.seguridad, "Vigilante",
                return_value=mock.Mock(cortado=False)),
            mock.patch.object(correr.seguridad, "crear_respaldo",
                              return_value=(True, "")) as crear,
            mock.patch.object(correr.seguridad, "borrar_respaldo"),
            mock.patch.object(
                correr.devolver, "ejecutar_devolucion",
                return_value=True) as devolver_mock,
            mock.patch.object(correr, "_con_canario", return_value=0),
        ):
            codigo = correr.ejecutar(args)
        self.assertEqual(codigo, correr.COD_PRESENCIA)
        escribir.assert_not_called()
        cerrar.assert_not_called()
        crear.assert_not_called()
        devolver_mock.assert_not_called()


class TestCortado(unittest.TestCase):

    def _correr_cortado(self, devolucion_ok):
        args = SimpleNamespace(sin_espera=False, una_pc=False,
                               respaldo_minutos=45, canario=True)
        vigilante = mock.Mock(cortado=False)

        def cerrar(_actual):
            vigilante.cortado = True
            return True

        with (
            mock.patch.object(correr, "_guardia", return_value=None),
            mock.patch.object(
                correr, "_elegir_copia",
                return_value=(Path("copia"), INSTALADO, "usar")),
            mock.patch.object(correr.perfil, "version_esperada",
                              return_value="2026.3.1"),
            mock.patch.object(correr.perfil, "ruta_estado",
                              return_value=Path("estado.json")),
            mock.patch.object(correr.nvda_local, "nvda_en_marcha",
                              return_value=None),
            mock.patch.object(correr.nvda_local, "cerrar",
                              side_effect=cerrar),
            mock.patch.object(correr.seguridad, "escribir_estado"),
            mock.patch.object(correr.seguridad, "Vigilante",
                              return_value=vigilante),
            mock.patch.object(correr.seguridad, "crear_respaldo",
                              return_value=(True, "")),
            mock.patch.object(correr.seguridad,
                              "borrar_respaldo") as borrar,
            mock.patch.object(
                correr.devolver, "ejecutar_devolucion",
                return_value=devolucion_ok) as devolver_mock,
            mock.patch.object(correr, "_escribir_informe",
                              return_value=Path("informe")),
        ):
            codigo = correr.ejecutar(args)
        return codigo, borrar, devolver_mock

    def test_cortado_devuelve_corte_y_borra_solo_si_devuelve(self):
        codigo, borrar, devolver_mock = self._correr_cortado(True)
        self.assertEqual(codigo, correr.COD_CORTE)
        devolver_mock.assert_called_once()
        borrar.assert_called_once_with(seguridad.NOMBRE_RESPALDO)
        codigo, borrar, devolver_mock = self._correr_cortado(False)
        self.assertEqual(codigo, correr.COD_CORTE)
        devolver_mock.assert_called_once()
        borrar.assert_not_called()


class TestRespaldo(unittest.TestCase):

    def test_sin_respaldo_no_cierra_el_nvda(self):
        args = SimpleNamespace(sin_espera=False, una_pc=False,
                               respaldo_minutos=45, canario=True)
        with (
            mock.patch.object(correr, "_guardia", return_value=None),
            mock.patch.object(
                correr, "_elegir_copia",
                return_value=(Path("copia"), INSTALADO, "usar")),
            mock.patch.object(correr.perfil, "version_esperada",
                              return_value="2026.3.1"),
            mock.patch.object(correr.perfil, "ruta_estado",
                              return_value=Path("estado.json")),
            mock.patch.object(correr.nvda_local, "nvda_en_marcha",
                              return_value=None),
            mock.patch.object(correr.nvda_local, "cerrar") as cerrar,
            mock.patch.object(correr.seguridad, "escribir_estado"),
            mock.patch.object(
                correr.seguridad, "Vigilante",
                return_value=mock.Mock(cortado=False)),
            mock.patch.object(correr.seguridad, "crear_respaldo",
                              return_value=(False, "sin tarea")),
            mock.patch.object(correr.seguridad, "borrar_respaldo"),
            mock.patch.object(correr.devolver, "ejecutar_devolucion",
                              return_value=True),
        ):
            codigo = correr.ejecutar(args)
        self.assertEqual(codigo, correr.COD_RESPALDO)
        cerrar.assert_not_called()


class TestPasoCanario(unittest.TestCase):

    def test_cortado_justo_despues_de_la_tecla_no_pide_habla_ni_foco(self):
        vigilante = SimpleNamespace(cortado=False)
        cliente = mock.Mock()
        cliente.marca.return_value = 3
        cliente.desde.return_value = []
        cliente.foco.return_value = {}
        cliente.tecla.side_effect = lambda _gesto: setattr(
            vigilante, "cortado", True)
        with self.assertRaises(correr.Cortado):
            correr._paso_canario(
                cliente, "tab", "Opción de prueba", "casilla", vigilante)
        cliente.tecla.assert_called_once_with("tab")
        cliente.desde.assert_not_called()
        cliente.foco.assert_not_called()


class TestDevolucionFallida(unittest.TestCase):

    def test_si_lanzar_falla_no_borra_el_estado_ni_el_respaldo(self):
        carpeta = tempfile.TemporaryDirectory()
        self.addCleanup(carpeta.cleanup)
        ruta_estado = Path(carpeta.name) / "estado-carril.json"
        ruta_estado.write_text(
            json.dumps({"habia": True, "ejecutable": INSTALADO}),
            encoding="utf-8")
        with (
            mock.patch.object(nvda_local, "nvda_en_marcha",
                              return_value=None),
            mock.patch.object(
                nvda_local, "lanzar",
                side_effect=OSError(740, "requiere elevación")),
        ):
            self.assertFalse(devolver.ejecutar_devolucion(
                ruta_estado, Path("copia"), INSTALADO))
        self.assertTrue(ruta_estado.exists())

        ruta_corrida = Path(carpeta.name) / "estado-corrida.json"
        with (
            mock.patch.object(correr, "_guardia", return_value=None),
            mock.patch.object(
                correr, "_elegir_copia",
                return_value=(Path("copia"), INSTALADO, "usar")),
            mock.patch.object(correr.perfil, "version_esperada",
                              return_value="2026.3.1"),
            mock.patch.object(correr.perfil, "ruta_estado",
                              return_value=ruta_corrida),
            mock.patch.object(
                correr.nvda_local, "nvda_en_marcha",
                side_effect=[
                    {"pid": 1, "ejecutable": INSTALADO}, None]),
            mock.patch.object(
                correr.nvda_local, "lanzar",
                side_effect=OSError(740, "requiere elevación")),
            mock.patch.object(
                correr.seguridad, "Vigilante",
                return_value=mock.Mock(cortado=False)),
            mock.patch.object(correr.seguridad, "crear_respaldo",
                              return_value=(True, "")),
            mock.patch.object(correr.seguridad,
                              "borrar_respaldo") as borrar,
            mock.patch.object(correr, "_con_canario", return_value=0),
        ):
            codigo = correr.ejecutar(
                SimpleNamespace(sin_espera=False, una_pc=False,
                                respaldo_minutos=45, canario=True))
        self.assertEqual(codigo, correr.COD_OK)
        self.assertTrue(ruta_corrida.exists())
        borrar.assert_not_called()
