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

    def escribir(self, carpeta, vistas):
        for nombre, datos in vistas.items():
            (carpeta / (nombre + ".json")).write_text(
                json.dumps(datos), encoding="utf-8")

    def comparar(self):
        return visual.comparar(self.corrida, self.aprobadas)

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
        self.escribir(self.aprobadas, {"01_principal": vista()})
        self.escribir(self.corrida, {"01_principal": vista()})
        resultado = self.resultado("01_principal")
        self.assertEqual(resultado["estado"], "igual")
        self.assertEqual(resultado["cambios"], [])
        codigo, texto = self.correr("comparar", str(self.corrida))
        self.assertEqual(codigo, 0)
        self.assertIn("igual 01_principal", texto)

    def test_cuatro_pixeles_da_igual(self):
        casos = (
            ("posición", vista([control(rect=[14, 20, 100, 24])])),
            ("tamaño del control", vista([control(rect=[10, 20, 104, 24])])),
            ("tamaño de la ventana", vista(tamano=[864, 700])),
            ("tamaño mínimo", vista(tamano_minimo=[644, 480])),
            ("tamaño del texto", vista([control(texto_px=[34, 12])])),
        )
        for nombre, corrida in casos:
            with self.subTest(medida=nombre):
                self.escribir(self.aprobadas, {"01_principal": vista()})
                self.escribir(self.corrida, {"01_principal": corrida})
                resultado = self.resultado("01_principal")
                self.assertEqual(resultado["estado"], "igual")
                self.assertEqual(resultado["cambios"], [])

    def test_cinco_pixeles_da_distinto(self):
        casos = (
            ("posición", vista([control(rect=[15, 20, 100, 24])]),
             "movido de [10, 20] a [15, 20]"),
            ("tamaño del control", vista([control(rect=[10, 20, 105, 24])]),
             "cambió de tamaño de [100, 24] a [105, 24]"),
            ("tamaño de la ventana", vista(tamano=[865, 700]),
             "cambió de tamaño de [860, 700] a [865, 700]"),
            ("tamaño mínimo", vista(tamano_minimo=[645, 480]),
             "cambió de tamaño mínimo de [640, 480] a [645, 480]"),
            ("tamaño del texto", vista([control(texto_px=[35, 12])]),
             "cambió de tamaño del texto de [30, 12] a [35, 12]"),
        )
        for nombre, corrida, mensaje in casos:
            with self.subTest(medida=nombre):
                self.escribir(self.aprobadas, {"01_principal": vista()})
                self.escribir(self.corrida, {"01_principal": corrida})
                resultado = self.resultado("01_principal")
                self.assertEqual(resultado["estado"], "distinta")
                codigo, texto = self.correr("comparar", str(self.corrida))
                self.assertEqual(codigo, 1)
                self.assertIn(mensaje, texto)

    def test_control_nuevo_con_la_misma_geometria_da_distinto(self):
        nuevo = control(nombre="Boton", clase="wxButton")
        self.escribir(self.aprobadas, {"01_principal": vista([control()])})
        self.escribir(self.corrida, {"01_principal": vista([control(), nuevo])})
        resultado = self.resultado("01_principal")
        self.assertEqual(resultado["estado"], "distinta")
        self.assertEqual(self.cambio(resultado, "apareció")["control"], "Boton")

    def test_control_otra_clase_da_distinto(self):
        self.escribir(self.aprobadas, {"01_principal": vista()})
        self.escribir(self.corrida, {"01_principal": vista([
            control(clase="wxButton")])})
        resultado = self.resultado("01_principal")
        self.assertEqual(resultado["estado"], "distinta")
        self.assertIsNotNone(self.cambio(resultado, "apareció"))
        self.assertIsNotNone(self.cambio(resultado, "se fue"))

    def test_control_otro_texto_sin_margen(self):
        self.escribir(self.aprobadas, {"01_principal": vista()})
        self.escribir(self.corrida, {"01_principal": vista([
            control(etiqueta="Texto!")])})
        cambio = self.cambio(self.resultado("01_principal"), "texto")
        self.assertEqual(cambio["antes"], "Texto")
        self.assertEqual(cambio["despues"], "Texto!")

    def test_control_otro_color_sin_margen(self):
        self.escribir(self.aprobadas, {"01_principal": vista()})
        self.escribir(self.corrida, {"01_principal": vista([
            control(fg="#1C262A")])})
        cambio = self.cambio(self.resultado("01_principal"), "fg")
        self.assertEqual(cambio["antes"], "#1C2629")
        self.assertEqual(cambio["despues"], "#1C262A")

    def test_control_se_fue(self):
        self.escribir(self.aprobadas, {"01_principal": vista([
            control(), control(nombre="Boton", clase="wxButton")])})
        self.escribir(self.corrida, {"01_principal": vista([control()])})
        cambio = self.cambio(self.resultado("01_principal"), "se fue")
        self.assertEqual(cambio["control"], "Boton")

    def test_vista_nueva(self):
        self.escribir(self.aprobadas, {"01_principal": vista()})
        self.escribir(self.corrida, {"01_principal": vista(),
                                     "02_nueva": vista()})
        self.assertEqual(self.resultado("02_nueva")["estado"], "nueva")
        codigo, texto = self.correr("comparar", str(self.corrida))
        self.assertEqual(codigo, 1)
        self.assertIn("nueva 02_nueva", texto)

    def test_vista_falta(self):
        self.escribir(self.aprobadas, {"01_principal": vista(),
                                       "02_otra": vista()})
        self.escribir(self.corrida, {"01_principal": vista()})
        self.assertEqual(self.resultado("02_otra")["estado"], "falta")
        codigo, texto = self.correr("comparar", str(self.corrida))
        self.assertEqual(codigo, 1)
        self.assertIn("falta 02_otra", texto)

    def test_empareja_por_nombre_y_clase_no_por_orden(self):
        primero = control(nombre="Uno", clase="wxStaticText")
        segundo = control(nombre="Dos", clase="wxButton", rect=[50, 60, 80, 24])
        self.escribir(self.aprobadas, {"01_principal": vista([primero, segundo])})
        self.escribir(self.corrida, {"01_principal": vista([segundo, primero])})
        resultado = self.resultado("01_principal")
        self.assertEqual(resultado["estado"], "igual")
        self.assertEqual(resultado["cambios"], [])

    def test_numeros_de_ventana_ignorados(self):
        self.escribir(self.aprobadas, {"01_principal": vista([
            control(id=7, padre=3)])})
        self.escribir(self.corrida, {"01_principal": vista([
            control(id=99, padre=42)])})
        resultado = self.resultado("01_principal")
        self.assertEqual(resultado["estado"], "igual")
        self.assertEqual(resultado["cambios"], [])

    def test_maquina_ya_no_se_acepta(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                visual.main(["comparar", str(self.corrida),
                             "--maquina", "oficina"], aprobadas=self.aprobadas)
        codigo, texto = self.correr("comparar", str(self.corrida))
        self.assertEqual(codigo, 3)
        self.assertEqual(texto.strip(), "No hay aprobadas para comparar.")

    def test_comparar_sin_aprobadas(self):
        self.escribir(self.corrida, {"01_principal": vista()})
        codigo, texto = self.correr("comparar", str(self.corrida))
        self.assertEqual(codigo, 3)
        self.assertEqual(texto.strip().splitlines(),
                         ["No hay aprobadas para comparar."])


class TestAprobar(Base):

    def test_copia_todas(self):
        self.escribir(self.corrida, {"01_principal": vista(),
                                     "02_comentarios": vista()})
        codigo, _ = self.correr("aprobar", str(self.corrida))
        self.assertEqual(codigo, 0)
        self.assertEqual(
            sorted(ruta.stem for ruta in self.aprobadas.glob("*.json")),
            ["01_principal", "02_comentarios"])

    def test_copia_solo_la_vista_nombrada(self):
        self.escribir(self.corrida, {"01_principal": vista(),
                                     "02_comentarios": vista()})
        codigo, _ = self.correr("aprobar", str(self.corrida),
                                "--vista", "02_comentarios")
        self.assertEqual(codigo, 0)
        self.assertEqual(
            [ruta.stem for ruta in self.aprobadas.glob("*.json")],
            ["02_comentarios"])

    def test_guarda_la_medida_corrida_sin_redondear(self):
        corrida = vista(tamano=[863, 701],
                        controles=[control(rect=[11, 21, 101, 25],
                                           texto_px=[31, 13])])
        self.escribir(self.corrida, {"01_principal": corrida})
        codigo, _ = self.correr("aprobar", str(self.corrida))
        self.assertEqual(codigo, 0)
        self.assertEqual(json.loads(
            (self.aprobadas / "01_principal.json").read_text(encoding="utf-8")),
            corrida)


class TestGeometriaUnica(unittest.TestCase):

    def test_una_sola_carpeta_y_leeme(self):
        self.assertEqual(len(list(visual.APROBADAS.glob("*.json"))), 94)
        self.assertEqual(list(visual.APROBADAS.glob("*/*.json")), [])
        texto = (visual.APROBADAS / "LEEME.txt").read_text(encoding="utf-8")
        self.assertIn("una sola", texto)
        self.assertIn("todas las PC", texto)
        self.assertIn("4 píxeles", texto)
        self.assertIn("24/11/2026", texto)
        self.assertIn("Aumentar el margen", texto)


class TestCorridasReales(unittest.TestCase):

    @unittest.skipUnless(CORRIDA_UNO.is_dir() and CORRIDA_DOS.is_dir(),
                         "faltan las dos corridas seguidas en el worktree")
    def test_dos_corridas_seguidas_comparan_iguales(self):
        resultados = visual.comparar(CORRIDA_UNO, CORRIDA_DOS)
        self.assertEqual(len(resultados), 94)
        self.assertTrue(all(r["estado"] == "igual" for r in resultados))
        self.assertEqual(sum(len(r["cambios"]) for r in resultados), 0)


if __name__ == "__main__":
    unittest.main()
