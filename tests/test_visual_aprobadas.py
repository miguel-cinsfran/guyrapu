# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas puras de la comparación de geometrías aprobadas de la galería."""

import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

_RAIZ = Path(__file__).resolve().parent.parent
_RUTA = _RAIZ / "qa" / "visual_aprobadas.py"
for _carpeta in (str(_RAIZ), str(_RAIZ / "qa")):
    if _carpeta not in sys.path:
        sys.path.insert(0, _carpeta)
_especificacion = importlib.util.spec_from_file_location(
    "visual_aprobadas_qa", _RUTA)
visual = importlib.util.module_from_spec(_especificacion)
_especificacion.loader.exec_module(visual)

FUENTE = {"cara": "Segoe UI", "puntos": 9, "px": 12, "peso": 400}
CORRIDA_UNO = _RAIZ / "qa" / "salida" / "galeria" / "2026-11-23_23-21"
CORRIDA_DOS = _RAIZ / "qa" / "salida" / "galeria" / "2026-11-24_00-23"
CORRIDA_APROBADA = _RAIZ / "qa" / "salida" / "galeria" / "2026-11-24_00-41"


def control(nombre="Etiqueta", clase="wxStaticText", **cambios):
    """Control con geometría fija, listo para cambiar un solo campo."""
    datos = {
        "id": 7, "padre": None, "clase": clase, "nombre": nombre,
        "etiqueta": "Texto", "rect": [10, 20, 100, 24], "visible": True,
        "habilitado": True, "enfocable": True, "fg": "#1C2629",
        "bg": "#F3F6F6", "fuente": dict(FUENTE), "texto_px": [30, 12],
    }
    datos.update(cambios)
    return datos


def vista(controles=None, **cambios):
    """Venta con geometría fija, con un control por omisión."""
    datos = {
        "muestra": "principal", "clase": "VentanaPrincipal",
        "variante": "con_chat", "pagina": "Chat del directo",
        "png": "01_principal.png", "tamano": [860, 700],
        "cliente": [844, 660], "tamano_minimo": [640, 480],
        "pantalla": [1600, 900],
        "controles": [control()] if controles is None else controles,
    }
    datos.update(cambios)
    return datos


class Base(unittest.TestCase):

    def setUp(self):
        self._temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self._temporal.cleanup)
        self.raiz = Path(self._temporal.name)
        self.corrida = self.raiz / "corrida"
        self.aprobadas = self.raiz / "aprobadas"
        self.corrida.mkdir()
        self.aprobadas.mkdir()
        (self.aprobadas / "casa").mkdir()
        (self.aprobadas / "oficina").mkdir()

    def escribir(self, carpeta, vistas):
        for nombre, datos in vistas.items():
            (carpeta / (nombre + ".json")).write_text(
                json.dumps(datos), encoding="utf-8")

    def comparar(self, maquina="oficina"):
        return visual.comparar(self.corrida, self.aprobadas / maquina)

    def resultado(self, nombre):
        return next(r for r in self.comparar() if r["vista"] == nombre)

    def cambio(self, resultado, tipo):
        return next((c for c in resultado["cambios"]
                     if c["tipo"] == tipo), None)

    def correr(self, *argumentos):
        salida = io.StringIO()
        with contextlib.redirect_stdout(salida):
            codigo = visual.main(list(argumentos), aprobadas=self.aprobadas)
        return codigo, salida.getvalue()


class TestComparar(Base):

    def test_igual(self):
        self.escribir(self.aprobadas / "oficina", {"01_principal": vista()})
        self.escribir(self.corrida, {"01_principal": vista()})
        resultado = self.resultado("01_principal")
        self.assertEqual(resultado["estado"], "igual")
        self.assertEqual(resultado["cambios"], [])
        codigo, texto = self.correr("comparar", str(self.corrida),
                                    "--maquina", "oficina")
        self.assertEqual(codigo, 0)
        self.assertIn("igual 01_principal", texto)

    def test_control_movido_cuatro_pixeles(self):
        self.escribir(self.aprobadas / "oficina", {"01_principal": vista()})
        self.escribir(self.corrida, {"01_principal": vista([
            control(rect=[14, 20, 100, 24])])})
        resultado = self.resultado("01_principal")
        self.assertEqual(resultado["estado"], "distinta")
        movido = self.cambio(resultado, "movido")
        self.assertEqual(movido["antes"], [10, 20])
        self.assertEqual(movido["despues"], [14, 20])
        codigo, texto = self.correr("comparar", str(self.corrida),
                                    "--maquina", "oficina")
        self.assertEqual(codigo, 1)
        self.assertIn("movido de [10, 20] a [14, 20]", texto)

    def test_control_cambio_de_tamano(self):
        self.escribir(self.aprobadas / "oficina", {"01_principal": vista()})
        self.escribir(self.corrida, {"01_principal": vista([
            control(rect=[10, 20, 104, 24])])})
        cambio = self.cambio(self.resultado("01_principal"), "tamaño")
        self.assertEqual(cambio["antes"], [100, 24])
        self.assertEqual(cambio["despues"], [104, 24])

    def test_control_otro_texto(self):
        self.escribir(self.aprobadas / "oficina", {"01_principal": vista()})
        self.escribir(self.corrida, {"01_principal": vista([
            control(etiqueta="Otro texto")])})
        cambio = self.cambio(self.resultado("01_principal"), "texto")
        self.assertEqual(cambio["antes"], "Texto")
        self.assertEqual(cambio["despues"], "Otro texto")

    def test_control_otro_color(self):
        self.escribir(self.aprobadas / "oficina", {"01_principal": vista()})
        self.escribir(self.corrida, {"01_principal": vista([
            control(fg="#FFFFFF")])})
        cambio = self.cambio(self.resultado("01_principal"), "fg")
        self.assertEqual(cambio["antes"], "#1C2629")
        self.assertEqual(cambio["despues"], "#FFFFFF")

    def test_control_aparece(self):
        self.escribir(self.aprobadas / "oficina", {"01_principal": vista([control()])})
        self.escribir(self.corrida, {"01_principal": vista([
            control(), control(nombre="Boton", clase="wxButton")])})
        cambio = self.cambio(self.resultado("01_principal"), "apareció")
        self.assertEqual(cambio["control"], "Boton")

    def test_control_se_fue(self):
        self.escribir(self.aprobadas / "oficina", {"01_principal": vista([
            control(), control(nombre="Boton", clase="wxButton")])})
        self.escribir(self.corrida, {"01_principal": vista([control()])})
        cambio = self.cambio(self.resultado("01_principal"), "se fue")
        self.assertEqual(cambio["control"], "Boton")

    def test_vista_nueva(self):
        self.escribir(self.aprobadas / "oficina", {"01_principal": vista()})
        self.escribir(self.corrida, {"01_principal": vista(),
                                     "02_nueva": vista()})
        self.assertEqual(self.resultado("02_nueva")["estado"], "nueva")
        codigo, texto = self.correr("comparar", str(self.corrida),
                                    "--maquina", "oficina")
        self.assertEqual(codigo, 1)
        self.assertIn("nueva 02_nueva", texto)

    def test_vista_falta(self):
        self.escribir(self.aprobadas / "oficina", {"01_principal": vista(),
                                                   "02_otra": vista()})
        self.escribir(self.corrida, {"01_principal": vista()})
        self.assertEqual(self.resultado("02_otra")["estado"], "falta")
        codigo, texto = self.correr("comparar", str(self.corrida),
                                    "--maquina", "oficina")
        self.assertEqual(codigo, 1)
        self.assertIn("falta 02_otra", texto)

    def test_empareja_por_nombre_y_clase_no_por_orden(self):
        primero = control(nombre="Uno", clase="wxStaticText")
        segundo = control(nombre="Dos", clase="wxButton", rect=[50, 60, 80, 24])
        self.escribir(self.aprobadas / "oficina", {"01_principal": vista([primero, segundo])})
        self.escribir(self.corrida, {"01_principal": vista([segundo, primero])})
        resultado = self.resultado("01_principal")
        self.assertEqual(resultado["estado"], "igual")
        self.assertEqual(resultado["cambios"], [])

    def test_numeros_de_ventana_ignorados(self):
        self.escribir(self.aprobadas / "oficina", {"01_principal": vista([
            control(id=7, padre=3)])})
        self.escribir(self.corrida, {"01_principal": vista([
            control(id=99, padre=42)])})
        resultado = self.resultado("01_principal")
        self.assertEqual(resultado["estado"], "igual")
        self.assertEqual(resultado["cambios"], [])

    def test_maquina_obligatoria_y_solo_casa_u_oficina(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                visual.main(["comparar", str(self.corrida)],
                            aprobadas=self.aprobadas)
            with self.assertRaises(SystemExit):
                visual.main(["comparar", str(self.corrida),
                             "--maquina", "otra"], aprobadas=self.aprobadas)

    def test_comparar_no_mira_la_otra_maquina(self):
        self.escribir(self.aprobadas / "oficina", {"01_principal": vista()})
        self.escribir(self.aprobadas / "casa", {"01_principal": vista([
            control(rect=[90, 20, 100, 24])])})
        self.escribir(self.corrida, {"01_principal": vista()})
        codigo, texto = self.correr("comparar", str(self.corrida),
                                    "--maquina", "oficina")
        self.assertEqual(codigo, 0)
        self.assertIn("igual 01_principal", texto)
        self.assertNotIn("movido", texto)

    def test_comparar_sin_aprobadas_de_la_maquina(self):
        self.escribir(self.aprobadas / "oficina", {"01_principal": vista()})
        self.escribir(self.corrida, {"01_principal": vista()})
        codigo, texto = self.correr("comparar", str(self.corrida),
                                    "--maquina", "casa")
        self.assertNotEqual(codigo, 0)
        self.assertEqual(texto.strip().splitlines(),
                         ["No hay aprobadas de casa para comparar."])


class TestAprobar(Base):

    def test_copia_todas(self):
        self.escribir(self.corrida, {"01_principal": vista(),
                                     "02_comentarios": vista()})
        codigo, _ = self.correr("aprobar", str(self.corrida),
                                "--maquina", "oficina")
        self.assertEqual(codigo, 0)
        self.assertEqual(
            sorted(ruta.stem for ruta in
                   (self.aprobadas / "oficina").glob("*.json")),
            ["01_principal", "02_comentarios"])

    def test_copia_solo_la_vista_nombrada(self):
        self.escribir(self.corrida, {"01_principal": vista(),
                                     "02_comentarios": vista()})
        codigo, _ = self.correr("aprobar", str(self.corrida),
                                "--maquina", "oficina",
                                "--vista", "02_comentarios")
        self.assertEqual(codigo, 0)
        self.assertEqual(
            [ruta.stem for ruta in
             (self.aprobadas / "oficina").glob("*.json")],
            ["02_comentarios"])

    def test_aprobar_escribe_solo_en_la_maquina_nombrada(self):
        self.escribir(self.corrida, {"01_principal": vista()})
        codigo, _ = self.correr("aprobar", str(self.corrida),
                                "--maquina", "casa")
        self.assertEqual(codigo, 0)
        self.assertEqual(
            [ruta.stem for ruta in (self.aprobadas / "casa").glob("*.json")],
            ["01_principal"])
        self.assertEqual(list((self.aprobadas / "oficina").glob("*.json")), [])


class TestCorridasReales(unittest.TestCase):

    @unittest.skipUnless(CORRIDA_UNO.is_dir() and CORRIDA_DOS.is_dir(),
                         "faltan las dos corridas seguidas en el worktree")
    def test_dos_corridas_seguidas_comparan_iguales(self):
        resultados = visual.comparar(CORRIDA_UNO, CORRIDA_DOS)
        self.assertEqual(len(resultados), 94)
        self.assertTrue(all(r["estado"] == "igual" for r in resultados))
        self.assertEqual(sum(len(r["cambios"]) for r in resultados), 0)

    def test_aprobadas_de_oficina_son_la_corrida_aprobada(self):
        resultados = visual.comparar(CORRIDA_APROBADA,
                                     visual.APROBADAS / "oficina")
        self.assertEqual(len(resultados), 94)
        self.assertTrue(all(r["estado"] == "igual" for r in resultados))
        self.assertEqual(sum(len(r["cambios"]) for r in resultados), 0)


if __name__ == "__main__":
    unittest.main()
