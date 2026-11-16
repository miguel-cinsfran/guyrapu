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
            mock.patch.object(correr.seguridad, "leer_fin_limpio",
                              return_value=None),
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
            mock.patch.object(correr.seguridad, "anotar_fin_limpio"),
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
            mock.patch.object(correr.seguridad, "anotar_fin_limpio"),
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
            mock.patch.object(correr.seguridad, "anotar_fin_limpio"),
        ):
            codigo = correr.ejecutar(
                SimpleNamespace(sin_espera=False, una_pc=False,
                                respaldo_minutos=45, canario=True))
        self.assertEqual(codigo, correr.COD_OK)
        self.assertTrue(ruta_corrida.exists())
        borrar.assert_not_called()


class TestReglas(unittest.TestCase):

    def _datos(self, ventana):
        return {"ventana": ventana, "pid": 1, "primero": {}, "pasos": []}

    def _reglas(self, analizar):
        with (
            mock.patch.object(correr.reglas, "leer_catalogo_ingles",
                              return_value=set()),
            mock.patch.object(correr.reglas, "analizar",
                              side_effect=analizar),
            mock.patch.object(
                correr.recorrido, "recorrer",
                side_effect=lambda datos, cliente: self._datos(
                    datos["nombre"])),
        ):
            with self.assertRaises(correr.ReglasFallidas) as capturado:
                correr._reglas(mock.Mock(), mock.Mock(cortado=False))
        return capturado.exception

    def _hallazgo(self, ventana, regla, paso=0):
        return {"regla": regla, "nivel": "aviso", "ventana": ventana,
                "paso": paso, "tecla": "tab", "detalle": "x"}

    def test_una_regla_que_no_salta_en_su_trampa_nombra_la_regla(self):
        def analizar(datos, catalogo):
            if datos["ventana"] in ("limpia", "ingles"):
                return []
            return [self._hallazgo(datos["ventana"], datos["ventana"])]

        error = self._reglas(analizar)
        self.assertIn("ingles", str(error))
        self.assertTrue(any("ingles" in linea for linea in error.lineas))

    def test_una_regla_que_salta_en_la_limpia_nombra_regla_y_paso(self):
        def analizar(datos, catalogo):
            if datos["ventana"] == "limpia":
                return [self._hallazgo("limpia", "sin_nombre", 2)]
            return []

        error = self._reglas(analizar)
        self.assertIn("sin_nombre", str(error))
        self.assertIn("paso 2", str(error))

    def test_un_primer_plano_ajeno_corta_y_el_informe_lo_dice(self):
        args = SimpleNamespace(canario=True)
        with (
            mock.patch.object(
                correr, "_corrida",
                side_effect=correr.InstrumentoRoto(
                    "tomó el primer plano «Otra» (proceso 9)")),
            mock.patch.object(correr, "_escribir_informe",
                              return_value=Path("informe")) as escribir,
        ):
            codigo = correr._con_canario(
                args, mock.Mock(cortado=False), Path("copia"), "usar",
                INSTALADO, None)
        self.assertEqual(codigo, correr.COD_INSTRUMENTO)
        lineas = escribir.call_args[0][0]
        self.assertTrue(any("Otra" in linea for linea in lineas))


class TestInformeDeTiempos(unittest.TestCase):

    def test_cada_paso_lleva_sus_milisegundos_y_el_maximo(self):
        datos = {
            "ventana": "prueba",
            "pasos": [
                {"tecla": "tab", "fase": "ida",
                 "foco": {"nombre": "Uno", "rol_nombre": "EDIT"},
                 "habla": [{"texto": "Uno"}], "agotado": False,
                 "ms_habla": 120},
                {"tecla": "tab", "fase": "ida",
                 "foco": {"nombre": "Dos", "rol_nombre": "EDIT"},
                 "habla": [{"texto": "Dos"}], "agotado": False,
                 "ms_habla": 80},
            ],
        }
        texto = "\n".join(correr._lineas_de_ventana("prueba", datos, []))
        self.assertIn("ms_habla=120", texto)
        self.assertIn("ms_habla=80", texto)
        self.assertIn("máximo de la última habla: 120 ms", texto)


class TestRegistro(unittest.TestCase):

    def test_copiar_registro_usa_el_nombre_del_informe(self):
        with tempfile.TemporaryDirectory() as base:
            origen = Path(base) / "nvda.log"
            origen.write_text("depuración", encoding="utf-8")
            informe = Path(base) / "informe-1.txt"
            with mock.patch.object(correr.perfil, "ruta_registro",
                                   return_value=origen):
                correr._copiar_registro(informe)
            destino = Path(base) / "informe-1-nvda.log"
            self.assertEqual(destino.read_text(encoding="utf-8"),
                             "depuración")

    def _ejecutar(self, codigo):
        carpeta = tempfile.TemporaryDirectory()
        self.addCleanup(carpeta.cleanup)
        args = SimpleNamespace(sin_espera=False, una_pc=False,
                               respaldo_minutos=45, canario=True,
                               informe=Path("informe.txt"))
        with (
            mock.patch.object(correr, "_guardia", return_value=None),
            mock.patch.object(
                correr, "_elegir_copia",
                return_value=(Path("copia"), INSTALADO, "usar")),
            mock.patch.object(correr.perfil, "version_esperada",
                              return_value="2026.3.1"),
            mock.patch.object(correr.perfil, "ruta_estado",
                              return_value=Path(carpeta.name) / "estado.json"),
            mock.patch.object(correr.nvda_local, "nvda_en_marcha",
                              return_value=None),
            mock.patch.object(
                correr.seguridad, "Vigilante",
                return_value=mock.Mock(cortado=False)),
            mock.patch.object(correr, "_programar_respaldo",
                              return_value=True),
            mock.patch.object(correr, "_con_canario", return_value=codigo),
            mock.patch.object(correr.devolver, "ejecutar_devolucion",
                              return_value=True),
            mock.patch.object(correr.seguridad, "borrar_respaldo"),
            mock.patch.object(correr.seguridad, "anotar_fin_limpio"),
            mock.patch.object(correr, "_copiar_registro") as copiar,
        ):
            devuelto = correr.ejecutar(args)
        self.assertEqual(devuelto, codigo)
        return copiar

    def test_el_registro_se_copia_solo_si_el_codigo_no_es_cero(self):
        self.assertFalse(self._ejecutar(correr.COD_OK).called)
        self.assertTrue(self._ejecutar(correr.COD_INSTRUMENTO).called)
