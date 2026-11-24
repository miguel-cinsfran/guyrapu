# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas del flujo de `qa/nvda/correr.py` con dobles, sin NVDA ni ventanas.

Se prueban la guardia, el corte, el respaldo y el paso del canario por las
funciones que los usan, con `seguridad`, `nvda_local`, `perfil`, `devolver`
y el cliente sustituidos. No se abre ninguna ventana ni se toca una tarea
programada.
"""

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from qa import foco_ventanas
from qa.nvda import (canario, correr, devolver, nvda_local, seguridad,
                     trampas, ventanas_app)

INSTALADO = r"C:\Program Files\NVDA\nvda.exe"
SONDAS = [nombre for nombre, datos in trampas.VENTANAS.items()
          if datos.get("sonda")]


class TestGuardia(unittest.TestCase):

    def _ejecutar(self, decisiones, segundos):
        carpeta = tempfile.TemporaryDirectory()
        self.addCleanup(carpeta.cleanup)
        args = SimpleNamespace(sin_espera=False, una_pc=False,
                               respaldo_minutos=45, canario=True)
        with (
            mock.patch.object(correr.seguridad,
                              "segundos_desde_ultima_entrada",
                              side_effect=segundos) as reloj,
            mock.patch.object(correr.seguridad, "decidir_guardia",
                              side_effect=decisiones) as decidir,
            mock.patch.object(correr.seguridad, "leer_fin_limpio",
                              return_value=None),
            mock.patch.object(correr.time, "sleep") as esperar,
            mock.patch.object(
                correr, "_elegir_copia",
                return_value=(Path("copia"), INSTALADO, "usar")),
            mock.patch.object(correr.perfil, "version_esperada",
                              return_value="2026.3.1"),
            mock.patch.object(correr.perfil, "ruta_estado",
                              return_value=Path(carpeta.name) / "estado.json"),
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
            mock.patch.object(correr.seguridad, "anotar_fin_limpio"),
            mock.patch("builtins.print") as imprimir,
        ):
            codigo = correr.ejecutar(args)
        return SimpleNamespace(
            codigo=codigo, reloj=reloj, decidir=decidir, esperar=esperar,
            imprimir=imprimir, escribir=escribir, cerrar=cerrar,
            crear=crear, devolver=devolver_mock)

    def test_una_guardia_que_se_niega_siempre_sale_a_la_decima(self):
        resultado = self._ejecutar([(False, "rechazo")] * 10, [10] * 10)
        self.assertEqual(resultado.codigo, correr.COD_PRESENCIA)
        self.assertEqual(resultado.decidir.call_count, 10)
        self.assertEqual(resultado.reloj.call_count, 10)
        self.assertEqual(resultado.esperar.call_args_list,
                         [mock.call(20.0)] * 9)
        mensaje = resultado.imprimir.call_args.args[0]
        self.assertIn("entrada física", mensaje)
        self.assertIn("10 veces seguidas", mensaje)
        self.assertIn("preguntá qué pasa", mensaje)
        resultado.escribir.assert_not_called()
        resultado.cerrar.assert_not_called()
        resultado.crear.assert_not_called()
        resultado.devolver.assert_not_called()

    def test_si_se_niega_dos_veces_y_despues_permite_sigue(self):
        resultado = self._ejecutar(
            [(False, "rechazo"), (False, "rechazo"), (True, "libre")],
            [10, 20, 31])
        self.assertEqual(resultado.codigo, correr.COD_OK)
        self.assertEqual(resultado.decidir.call_count, 3)
        self.assertEqual(resultado.esperar.call_args_list,
                         [mock.call(20.0), mock.call(10.0)])
        resultado.escribir.assert_called_once()


class TestCortado(unittest.TestCase):

    def _correr_cortado(self, devolucion_ok):
        carpeta = tempfile.TemporaryDirectory()
        self.addCleanup(carpeta.cleanup)
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
                              return_value=Path(carpeta.name) / "estado.json"),
            mock.patch.object(correr.perfil, "ruta_registro",
                              return_value=Path(carpeta.name) / "nvda.log"),
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
                              return_value=Path(carpeta.name) / "informe.txt"),
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

    def test_la_raiz_no_queda_con_informes_de_nvda(self):
        self._correr_cortado(True)
        raiz = Path.cwd()
        restos = sorted(raiz.glob("informe-nvda.log"))
        restos += sorted(raiz.glob("informe-*-nvda.log"))
        self.assertEqual(restos, [])


class TestRespaldo(unittest.TestCase):

    def test_sin_respaldo_no_cierra_el_nvda(self):
        carpeta = tempfile.TemporaryDirectory()
        self.addCleanup(carpeta.cleanup)
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
                              return_value=Path(carpeta.name) / "estado.json"),
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


class TestEsperarFrente(unittest.TestCase):

    def test_espera_a_que_se_vaya_la_notificacion_y_luego_trae_la_ventana(self):
        aviso = {"proceso": "ShellExperienceHost", "titulo": "Notificación",
                 "clase": "Windows.UI.Core.CoreWindow"}
        canario = {"proceso": "guyrapu", "titulo": "Canario del carril",
                   "clase": "wxWindowNR"}
        planos = iter([aviso, aviso, canario])
        intentos = []

        def intentar():
            intentos.append(1)
            return True

        dormir = mock.Mock()
        self.assertTrue(foco_ventanas.esperar_frente(
            intentar, plano=lambda: next(planos), dormir=dormir))
        self.assertEqual(len(intentos), 1)
        self.assertEqual(dormir.call_count, 2)

    def test_no_intenta_el_frente_si_ya_es_del_pid(self):
        intentos = []
        self.assertTrue(foco_ventanas.esperar_frente(
            lambda: intentos.append(1), plano=lambda: {"pid": 100},
            dormir=mock.Mock(), pid=100))
        self.assertEqual(intentos, [])

    def test_no_pulsa_alt_si_el_frente_ya_es_del_pid(self):
        pulsos = []
        self.assertTrue(foco_ventanas.traer_al_frente(
            123, 100, plano=lambda: {"pid": 100},
            pulsar=lambda usuario: pulsos.append(1)))
        self.assertEqual(pulsos, [])

    def test_no_pulsa_alt_si_el_frente_es_del_hijo_del_pid(self):
        pulsos = []
        with mock.patch.object(foco_ventanas, "arbol_de_procesos",
                               return_value={200: 100}):
            self.assertTrue(foco_ventanas.traer_al_frente(
                123, 100, plano=lambda: {"pid": 200},
                pulsar=lambda usuario: pulsos.append(1)))
        self.assertEqual(pulsos, [])

    def test_sin_notificacion_llama_al_primer_intento(self):
        plano = {"proceso": "guyrapu", "titulo": "Canario del carril",
                 "clase": "wxWindowNR"}
        dormir = mock.Mock()
        self.assertTrue(foco_ventanas.esperar_frente(
            lambda: True, plano=lambda: plano, dormir=dormir))
        dormir.assert_not_called()


class UsuarioFalso:
    """user32 falso: la ventana pedida es del hijo del pid lanzador."""

    def __init__(self, dueno):
        self.dueno = dueno
        self.f24 = 0
        self.levantadas = 0
        self.foreground = 999

    def FindWindowW(self, clase, titulo):
        return 123

    def GetWindowThreadProcessId(self, hwnd, puntero):
        puntero._obj.value = self.dueno

    def GetForegroundWindow(self):
        return self.foreground

    def keybd_event(self, *args):
        self.f24 += 1

    def SetForegroundWindow(self, hwnd):
        self.foreground = hwnd
        self.levantadas += 1


class TestFrenteCanario(unittest.TestCase):

    def _correr(self, al_frente, frente_ok=True):
        cliente = mock.Mock()
        cliente.desde.return_value = [
            {"tipo": "habla", "texto": "Canario listo"}]
        llamadas = []
        with (
            mock.patch.object(correr.subprocess, "Popen") as popen,
            mock.patch.object(correr.canario, "al_frente",
                              side_effect=lambda pid: (
                                  llamadas.append("al_frente") or frente_ok)),
            mock.patch.object(
                correr, "_esperar_foco",
                side_effect=lambda *a, **k: llamadas.append("esperar_foco")),
            mock.patch.object(correr, "_paso_canario", return_value="paso"),
            mock.patch.object(
                correr.canario, "motivo_sin_frente",
                return_value="no se pudo traer al frente: primer plano "
                             "'ShellExperienceHost' «Notificación»"),
        ):
            resultado = al_frente(cliente, mock.Mock(cortado=False))
        popen.return_value.wait.assert_called_once()
        return cliente, llamadas, resultado

    def test_acepta_la_ventana_del_hijo_del_pid_lanzador(self):
        usuario = UsuarioFalso(200)
        plano = lambda: {"proceso": "guyrapu", "titulo": "Canario del carril"}
        with (
            mock.patch.object(correr.canario.ctypes, "windll",
                              SimpleNamespace(user32=usuario)),
            mock.patch.object(foco_ventanas, "arbol_de_procesos",
                              return_value={200: 100}),
        ):
            self.assertTrue(canario.al_frente(
                100, plano=plano, dormir=mock.Mock()))
        self.assertEqual(usuario.levantadas, 1)

    def test_rechaza_una_ventana_de_otro_arbol_de_procesos(self):
        self.assertFalse(foco_ventanas.es_proceso_o_descendiente(
            200, 100, arbol={200: 300, 300: 400}))
        self.assertTrue(foco_ventanas.es_proceso_o_descendiente(
            200, 100, arbol={200: 100}))

    def test_trae_el_canario_al_frente_antes_de_esperar_el_foco(self):
        _cliente, llamadas, _resultado = self._correr(correr._canario)
        self.assertEqual(llamadas, ["al_frente", "esperar_foco"])

    def test_si_al_frente_falla_lo_dice_y_no_espera_el_foco(self):
        with self.assertRaises(correr.InstrumentoRoto) as capturado:
            self._correr(correr._canario, frente_ok=False)
        mensaje = str(capturado.exception)
        self.assertIn("frente", mensaje)
        self.assertIn("ShellExperienceHost", mensaje)
        self.assertIn("Notificación", mensaje)


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

    def _recorrer_reglas(self, analizar):
        vistos = []
        lineas = []
        with (
            mock.patch.object(correr.reglas, "leer_catalogo_ingles",
                              return_value=set()),
            mock.patch.object(correr.reglas, "analizar",
                              side_effect=analizar),
            mock.patch.object(
                correr.recorrido, "recorrer",
                side_effect=lambda datos, cliente: (
                    vistos.append(datos["nombre"]) or self._datos(
                        datos["nombre"]))),
        ):
            try:
                lineas = correr._reglas(mock.Mock(), mock.Mock(cortado=False))
            except correr.ReglasFallidas as capturado:
                lineas = capturado.lineas
        return vistos, lineas

    def test_las_cinco_sondas_se_recorren_y_sus_hallazgos_se_escriben(self):
        def analizar(datos, catalogo):
            nombre = datos["ventana"]
            if nombre.startswith("sonda_"):
                return [self._hallazgo(nombre, "nombre_repetido")]
            return []

        vistos, lineas = self._recorrer_reglas(analizar)
        for nombre in SONDAS:
            self.assertIn(nombre, vistos)
        self.assertTrue(any("hallazgo nombre_repetido" in linea
                            for linea in lineas))

    def test_un_nombre_repetido_en_una_sonda_no_entra_en_los_fallos(self):
        hallazgo = self._hallazgo("sonda_lista_box", "nombre_repetido")
        por_ventana = {regla: [self._hallazgo(regla, regla)]
                       for regla in correr.reglas.NIVELES}
        por_ventana["sonda_lista_box"] = [hallazgo]
        self.assertEqual(correr._fallos_de_reglas(por_ventana), [])

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


class AplicacionFalsa:
    """Una aplicación de mentira que anota las órdenes de la sonda."""

    instancias = []

    def __init__(self, carpeta):
        self.carpeta = Path(carpeta)
        self.ordenes = []
        self.arrancada = False
        self.cerrada = False
        AplicacionFalsa.instancias.append(self)

    def arrancar(self):
        self.arrancada = True

    def esperar_lista(self, segundos=60.0):
        return True

    def al_frente(self):
        return True

    def pedir(self, op, **extra):
        self.ordenes.append((op, extra))
        if op == "pid":
            return {"ok": True, "datos": {"pid": 4321}}
        return {"ok": True, "datos": {}}

    def esperar_ventana(self, titulo, segundos=15.0):
        self.pedir("ventanas", titulo=titulo)
        return {"titulo": titulo, "visible": True}

    def cerrar(self):
        self.cerrada = True


class TestApp(unittest.TestCase):

    def setUp(self):
        parche = mock.patch("guyrapu.voice.motores.listar_voces",
                            return_value=["Voz de prueba"])
        parche.start()
        self.addCleanup(parche.stop)

    def _correr(self, aprobar=False, ventana=None, previo=None):
        base = tempfile.TemporaryDirectory()
        self.addCleanup(base.cleanup)
        AplicacionFalsa.instancias = []
        conducidos = []
        analisis = []
        canario = mock.Mock(return_value=["canario"])
        informe = mock.Mock(return_value=Path(base.name) / "informe.txt")

        def conducir(cliente, datos, **_opciones):
            conducidos.append(datos)
            return {"ventana": datos["nombre"], "pid": datos["pid"],
                    "primero": {}, "pasos": []}

        def analizar(datos, catalogo):
            analisis.append(datos)
            return [{"regla": "sin_nombre", "nivel": "aviso",
                     "ventana": datos["ventana"], "paso": 0,
                     "tecla": "tab", "detalle": "x"}]

        for nombre, texto in (previo or {}).items():
            correr.app.transcripcion.escribir(nombre, texto, Path(base.name))

        args = SimpleNamespace(app=True, reglas=False, canario=False,
                               aprobar=aprobar, ventana=ventana,
                               informe=None)
        with (
            mock.patch.object(correr, "_canario", canario),
            mock.patch.object(correr, "_conectar", return_value=mock.Mock()),
            mock.patch.object(correr.nvda_local, "cerrar", return_value=True),
            mock.patch.object(correr.nvda_local, "lanzar"),
            mock.patch.object(correr.perfil, "armar_perfil"),
            mock.patch.object(correr.app, "Aplicacion", AplicacionFalsa),
            mock.patch.object(correr.app.recorrido, "conducir",
                              side_effect=conducir),
            mock.patch.object(correr.app.reglas, "leer_catalogo_ingles",
                              return_value=set()),
            mock.patch.object(correr.app.reglas, "analizar",
                              side_effect=analizar),
            mock.patch.object(correr.app.transcripcion, "CARPETA",
                              Path(base.name)),
            mock.patch.object(correr, "_escribir_informe", informe),
            mock.patch.object(correr, "_copiar_registro"),
            mock.patch("builtins.print"),
        ):
            codigo = correr._con_canario(
                args, mock.Mock(cortado=False), Path("copia"), "usar",
                INSTALADO, None)
        return SimpleNamespace(
            codigo=codigo, app=AplicacionFalsa.instancias[-1],
            conducidos=conducidos, analisis=analisis, canario=canario,
            informe=informe, carpeta=Path(base.name))

    def test_abre_recorre_y_cierra_cada_ventana_de_la_lista(self):
        resultado = self._correr()
        self.assertEqual(resultado.codigo, correr.COD_OK)
        self.assertTrue(resultado.canario.called)
        self.assertTrue(resultado.app.arrancada)
        self.assertTrue(resultado.app.cerrada)
        for entrada in ventanas_app.VENTANAS:
            self.assertIn(("menu_click", {"etiqueta": entrada["menu"],
                                          "tiempo": 10.0}),
                          resultado.app.ordenes)
            titulo_menu = entrada.get("titulo_menu") or entrada["titulo"]
            self.assertIn(("ventanas", {"titulo": titulo_menu}),
                          resultado.app.ordenes)
            self.assertIn(("cerrar_ventana", {"ventana": entrada["titulo"],
                                              "tiempo": 10.0}),
                          resultado.app.ordenes)
        self.assertEqual(
            [datos["nombre"] for datos in resultado.conducidos],
            [entrada["nombre"] for entrada in ventanas_app.VENTANAS])
        self.assertTrue(all(datos["pid"] == 4321
                            for datos in resultado.conducidos))

    def test_aplica_las_reglas_y_sus_hallazgos_salen_en_el_informe(self):
        resultado = self._correr()
        self.assertEqual(len(resultado.analisis), len(ventanas_app.VENTANAS))
        lineas = resultado.informe.call_args.args[0]
        self.assertTrue(any("hallazgo sin_nombre" in linea
                            for linea in lineas))

    def test_una_transcripcion_distinta_sale_con_el_codigo_propio(self):
        resultado = self._correr(previo={"preferencias": "vieja\n"})
        self.assertEqual(resultado.codigo, correr.app.COD_TRANSCRIPCION)
        lineas = resultado.informe.call_args.args[0]
        self.assertTrue(any("transcripción distinta" in linea
                            for linea in lineas))
        self.assertTrue(any("vieja" in linea for linea in lineas))
        self.assertTrue(resultado.app.cerrada)

    def test_aprobar_reemplaza_la_aprobada_y_no_es_diferencia(self):
        resultado = self._correr(aprobar=True,
                                 previo={"preferencias": "vieja\n"})
        self.assertEqual(resultado.codigo, correr.COD_OK)
        self.assertNotEqual(
            correr.app.transcripcion.leer("preferencias", resultado.carpeta),
            "vieja\n")

    def test_ventana_recorre_solo_la_elegida(self):
        resultado = self._correr(ventana=["interaccion"])
        self.assertEqual([datos["nombre"] for datos in resultado.conducidos],
                         ["interaccion"])
        self.assertFalse(any(
            extra.get("etiqueta") == ventanas_app.VENTANAS[0]["menu"]
            for op, extra in resultado.app.ordenes if op == "menu_click"))

    def test_las_opciones_de_la_app_llegan_a_los_argumentos(self):
        with mock.patch.object(correr, "ejecutar", return_value=0) as ejecutar:
            codigo = correr.main(["--app", "--aprobar",
                                  "--ventana", "interaccion"])
        self.assertEqual(codigo, 0)
        args = ejecutar.call_args.args[0]
        self.assertTrue(args.app)
        self.assertTrue(args.aprobar)
        self.assertEqual(args.ventana, ["interaccion"])


class TestPrism(unittest.TestCase):

    def test_sin_prism_termina_con_dos_y_lo_dice_por_stderr(self):
        error = io.StringIO()
        with (
            mock.patch.dict(sys.modules, {"prism": None}),
            mock.patch.object(correr, "ejecutar") as ejecutar,
            contextlib.redirect_stderr(error),
        ):
            codigo = correr.main([])
        self.assertEqual(codigo, 2)
        ejecutar.assert_not_called()
        self.assertEqual(
            error.getvalue().strip(),
            "Falta el paquete prism: corré el carril con uv run python "
            "qa/nvda/correr.py.")
