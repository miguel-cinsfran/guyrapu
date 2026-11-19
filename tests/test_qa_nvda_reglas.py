# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas puras de las reglas del carril de NVDA.

Se arman recorridos a mano, con las mismas claves que deja `recorrido.py`, y
se comprueba que cada regla salta con uno que la viola y calla con el que no.
"""

import tempfile
import unittest
from pathlib import Path

from babel.messages import catalog, pofile

from qa.nvda import reglas


def foco(nombre="Aceptar", rol="PUSH_BUTTON", hwnd=1, pid=10,
         atajo="", estados=()):
    return {"nombre": nombre, "rol_nombre": rol, "hwnd": hwnd,
            "pid": pid, "atajo": atajo, "estados": list(estados)}


def paso(foco_paso, tecla="tab", fase="ida", frases=(), agotado=False):
    return {
        "tecla": tecla,
        "fase": fase,
        "foco": foco_paso,
        "habla": [{"texto": frase, "partes": [frase]} for frase in frases],
        "agotado": agotado,
        "ms_habla": 5,
    }


def recorrido(pasos, primero=None, ventana="prueba", pid=10):
    return {
        "ventana": ventana,
        "pid": pid,
        "primero": primero or foco("Nombre:", "EDIT", hwnd=1, pid=pid),
        "pasos": list(pasos),
    }


def _regla(hallazgos, nombre):
    return [h for h in hallazgos if h["regla"] == nombre]


class TestSinNombre(unittest.TestCase):

    def test_salta_con_una_parada_sin_nombre(self):
        datos = recorrido([paso(foco(""), frases=["botón"])])
        self.assertTrue(_regla(reglas.analizar(datos, set()), "sin_nombre"))

    def test_calla_con_una_parada_nombrada(self):
        datos = recorrido([paso(foco("Aceptar"), frases=["Aceptar botón"])])
        self.assertFalse(_regla(reglas.analizar(datos, set()), "sin_nombre"))


class TestRolContenedor(unittest.TestCase):

    def test_salta_con_un_rol_contenedor_en_la_ida(self):
        datos = recorrido([paso(foco("Panel", "PANE"), frases=["Panel panel"])])
        self.assertTrue(_regla(
            reglas.analizar(datos, set()), "rol_contenedor"))

    def test_calla_con_un_control(self):
        datos = recorrido([paso(foco("Aceptar", "PUSH_BUTTON"),
                                frases=["Aceptar botón"])])
        self.assertFalse(_regla(
            reglas.analizar(datos, set()), "rol_contenedor"))

    def test_la_vuelta_no_repite_el_hallazgo(self):
        datos = recorrido([
            paso(foco("Panel", "PANE", hwnd=2), frases=["Panel panel"]),
            paso(foco("Panel", "PANE", hwnd=2), tecla="shift+tab",
                 fase="vuelta", frases=["Panel panel"]),
        ])
        self.assertEqual(len(_regla(
            reglas.analizar(datos, set()), "rol_contenedor")), 1)


class TestNombreRepetido(unittest.TestCase):

    def test_salta_si_el_nombre_suena_dos_veces(self):
        datos = recorrido([paso(
            foco("Volumen"), frases=["Volumen", "Volumen deslizador"])])
        self.assertTrue(_regla(
            reglas.analizar(datos, set()), "nombre_repetido"))

    def test_calla_si_suena_una_vez(self):
        datos = recorrido([paso(
            foco("Volumen"), frases=["Volumen deslizador"])])
        self.assertFalse(_regla(
            reglas.analizar(datos, set()), "nombre_repetido"))

    def test_ignora_nombres_de_menos_de_tres_letras(self):
        datos = recorrido([paso(foco("Vo"), frases=["Vo Vo Vo"])])
        self.assertFalse(_regla(
            reglas.analizar(datos, set()), "nombre_repetido"))


class TestIngles(unittest.TestCase):

    def test_salta_con_un_nombre_del_catalogo(self):
        datos = recorrido([paso(foco("Cancel"), frases=["Cancel botón"])])
        self.assertTrue(_regla(reglas.analizar(datos, {"cancel"}), "ingles"))

    def test_salta_con_una_frase_del_catalogo(self):
        datos = recorrido([paso(
            foco("Seguir"), frases=["Cancel", "Seguir botón"])])
        self.assertTrue(_regla(reglas.analizar(datos, {"cancel"}), "ingles"))

    def test_calla_con_un_nombre_que_solo_contiene_el_texto(self):
        datos = recorrido([paso(
            foco("Cancelar"), frases=["Cancelar botón"])])
        self.assertFalse(_regla(
            reglas.analizar(datos, {"cancel"}), "ingles"))


class TestAtajoRepetido(unittest.TestCase):

    def test_salta_con_la_misma_letra_en_dos_paradas(self):
        datos = recorrido([
            paso(foco("Primera", hwnd=1, atajo="Alt+P")),
            paso(foco("Segunda", hwnd=2, atajo="Alt+p")),
        ])
        self.assertTrue(_regla(
            reglas.analizar(datos, set()), "atajo_repetido"))

    def test_calla_con_letras_distintas(self):
        datos = recorrido([
            paso(foco("Primera", hwnd=1, atajo="Alt+P")),
            paso(foco("Segunda", hwnd=2, atajo="Alt+O")),
        ])
        self.assertFalse(_regla(
            reglas.analizar(datos, set()), "atajo_repetido"))

    def test_calla_con_la_misma_parada_visitada_dos_veces(self):
        datos = recorrido([
            paso(foco("Primera", hwnd=1, atajo="Alt+P")),
            paso(foco("Primera", hwnd=1, atajo="Alt+P"),
                 tecla="shift+tab", fase="vuelta"),
        ])
        self.assertFalse(_regla(
            reglas.analizar(datos, set()), "atajo_repetido"))


class TestPasoMudo(unittest.TestCase):

    def test_salta_con_una_accion_sin_habla(self):
        datos = recorrido([paso(
            foco("Mudo"), tecla="space", fase="accion")])
        self.assertTrue(_regla(reglas.analizar(datos, set()), "paso_mudo"))

    def test_calla_cuando_la_accion_habla(self):
        datos = recorrido([paso(
            foco("Mudo"), tecla="space", fase="accion",
            frases=["Algo distinto"])])
        self.assertFalse(_regla(reglas.analizar(datos, set()), "paso_mudo"))


class TestFocoPerdido(unittest.TestCase):

    def _accion(self, foco_despues):
        return recorrido([paso(
            foco_despues, tecla="space", fase="accion", frases=["listo"])])

    def test_salta_en_un_rol_contenedor(self):
        self.assertTrue(_regla(reglas.analizar(
            self._accion(foco("Panel", "PANE")), set()), "foco_perdido"))

    def test_salta_sin_nombre(self):
        self.assertTrue(_regla(reglas.analizar(
            self._accion(foco("")), set()), "foco_perdido"))

    def test_salta_en_un_control_no_disponible(self):
        self.assertTrue(_regla(reglas.analizar(
            self._accion(foco("Boton", estados=["unavailable"])), set()),
            "foco_perdido"))

    def test_salta_en_otro_proceso(self):
        self.assertTrue(_regla(reglas.analizar(
            self._accion(foco("Otra", pid=99)), set()), "foco_perdido"))

    def test_calla_en_un_control_disponible_de_la_ventana(self):
        self.assertFalse(_regla(reglas.analizar(
            self._accion(foco("Otro control")), set()), "foco_perdido"))


class TestEsperaNoOida(unittest.TestCase):

    def _accion(self, oida, dicho="otra cosa"):
        datos = recorrido([paso(
            foco("Conectar"), tecla="space", fase="accion")])
        paso_datos = datos["pasos"][0]
        paso_datos["espera"] = "el historial está vacío"
        paso_datos["oida"] = oida
        paso_datos["espera_dicho"] = dicho
        return datos

    def test_salta_con_la_frase_y_lo_que_nvda_dijo(self):
        hallazgo = _regla(reglas.analizar(self._accion(False), set()),
                          "espera_no_oida")[0]
        self.assertIn("el historial está vacío", hallazgo["detalle"])
        self.assertIn("otra cosa", hallazgo["detalle"])

    def test_calla_cuando_se_oyó_la_frase(self):
        self.assertFalse(_regla(
            reglas.analizar(self._accion(True), set()), "espera_no_oida"))


class TestRecorrido(unittest.TestCase):

    def _ciclo(self):
        a = foco("Nombre", "EDIT", hwnd=1)
        b = foco("Aceptar", "PUSH_BUTTON", hwnd=2)
        c = foco("Opcion", "CHECK_BOX", hwnd=3)
        return recorrido([
            paso(b, frases=["Aceptar botón"]),
            paso(c, frases=["Opcion casilla"]),
            paso(a, frases=["Nombre edición"]),
            paso(c, tecla="shift+tab", fase="vuelta",
                 frases=["Opcion casilla"]),
            paso(b, tecla="shift+tab", fase="vuelta",
                 frases=["Aceptar botón"]),
            paso(a, tecla="shift+tab", fase="vuelta",
                 frases=["Nombre edición"]),
        ], primero=a)

    def test_calla_con_un_ciclo_completo(self):
        self.assertFalse(_regla(
            reglas.analizar(self._ciclo(), set()), "recorrido"))

    def test_salta_si_la_ida_no_vuelve(self):
        a = foco("Nombre", "EDIT", hwnd=1)
        datos = recorrido([
            paso(foco("Aceptar", hwnd=2)),
            paso(foco("Opcion", hwnd=3)),
        ], primero=a)
        self.assertTrue(_regla(reglas.analizar(datos, set()), "recorrido"))

    def test_salta_si_la_vuelta_no_es_al_reves(self):
        datos = self._ciclo()
        datos["pasos"][3]["foco"] = foco("Aceptar", "PUSH_BUTTON", hwnd=2)
        datos["pasos"][4]["foco"] = foco("Opcion", "CHECK_BOX", hwnd=3)
        self.assertTrue(_regla(reglas.analizar(datos, set()), "recorrido"))


class TestNiveles(unittest.TestCase):

    def test_todas_las_reglas_son_aviso(self):
        self.assertEqual(
            set(reglas.NIVELES),
             {"sin_nombre", "rol_contenedor", "nombre_repetido", "ingles",
              "atajo_repetido", "paso_mudo", "foco_perdido",
              "espera_no_oida", "recorrido"})
        self.assertEqual(set(reglas.NIVELES.values()), {"aviso"})

    def test_el_hallazgo_lleva_regla_nivel_ventana_paso_y_detalle(self):
        datos = recorrido(
            [paso(foco(""), frases=["botón"])], ventana="trampa")
        hallazgo = reglas.analizar(datos, set())[0]
        self.assertEqual(hallazgo["regla"], "sin_nombre")
        self.assertEqual(hallazgo["nivel"], "aviso")
        self.assertEqual(hallazgo["ventana"], "trampa")
        self.assertEqual(hallazgo["paso"], 0)
        self.assertEqual(hallazgo["tecla"], "tab")
        self.assertTrue(hallazgo["detalle"])


def _escribir_po(ruta, entradas):
    catalogo = catalog.Catalog(locale="en", domain="guyrapu")
    for original, traducido in entradas:
        catalogo.add(original, traducido, locations=[("app.py", 1)])
    with ruta.open("wb") as salida:
        pofile.write_po(salida, catalogo)


class TestCatalogoIngles(unittest.TestCase):

    def _leer(self, entradas):
        with tempfile.TemporaryDirectory() as base:
            ruta = Path(base) / "guyrapu.po"
            _escribir_po(ruta, entradas)
            return reglas.leer_catalogo_ingles(ruta)

    def test_solo_cuentan_los_traducidos_distintos_y_de_cuatro_letras(self):
        catalogo = self._leer([
            ("Cancelar", "Cancel"),
            ("Aceptar", "Accept"),
            ("Ir", "Go"),
            ("Guardar", ""),
            ("Igual", "Igual"),
        ])
        self.assertEqual(catalogo, {"cancel", "accept"})

    def test_cancelar_no_salta_por_contener_cancel(self):
        catalogo = self._leer([("Cancelar", "Cancel")])
        datos = recorrido([paso(
            foco("Cancelar"), frases=["Cancelar botón"])])
        self.assertFalse(_regla(reglas.analizar(datos, catalogo), "ingles"))


if __name__ == "__main__":
    unittest.main()
