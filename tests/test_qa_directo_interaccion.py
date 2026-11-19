# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de qa/directo_interaccion.py, sin red ni ventanas."""

import importlib.util
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

_RAIZ = Path(__file__).resolve().parent.parent
if str(_RAIZ) not in sys.path:
    sys.path.insert(0, str(_RAIZ))

_espec = importlib.util.spec_from_file_location(
    "directo_interaccion_qa", _RAIZ / "qa" / "directo_interaccion.py")
directo_interaccion = importlib.util.module_from_spec(_espec)
_espec.loader.exec_module(di := directo_interaccion)

from guyrapu.interaction import (comandos_guardados, disparadores_guardados,
                                 encuestas_guardadas, metas_guardadas)

_GUARDADOS = {
    "comandos": comandos_guardados,
    "disparadores": disparadores_guardados,
    "encuestas": encuestas_guardadas,
    "metas": metas_guardadas,
}


class _Anotador:
    def __init__(self):
        self.pasos = []

    def __call__(self, nombre, bien, detalle=""):
        self.pasos.append((nombre, bien, detalle))
        return bien


def _anuncios(*textos):
    """El archivo crece: la marca ve lo viejo y cada lectura lo nuevo."""
    turnos = iter([valor for texto in textos for valor in ("", texto)])
    return lambda ruta: next(turnos, textos[-1])


def _pasos(anotar, **cambios):
    argumentos = dict(
        anotar=anotar, enviar=lambda texto: None, respuesta=lambda: {},
        texto_video=lambda: "", leer_anuncios=lambda ruta: "",
        ruta_anuncios="anuncios.txt", abrir_encuesta=lambda: None,
        cerrar_encuesta=lambda: None, leer_siguiente=lambda: None,
        orden=lambda metodo, *args, **kwargs: {}, segundos=0)
    argumentos.update(cambios)
    return di.Pasos(**argumentos)


class TestDatos(unittest.TestCase):

    def setUp(self):
        self.carpeta = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.carpeta, True)
        self.rutas = {clave: os.path.join(self.carpeta, clave + ".json")
                      for clave in di.DATOS}

    def _escribir_previos(self):
        for clave, ruta in self.rutas.items():
            _GUARDADOS[clave].guardar(ruta, [{"nombre": "previo " + clave}])

    def test_la_preparacion_agrega_lo_de_p1_y_p8(self):
        self._escribir_previos()
        di.Datos(self.rutas).preparar()
        comandos = comandos_guardados.cargar(self.rutas["comandos"])
        nuevo = next(c for c in comandos if di.MARCA in c["respuesta"])
        self.assertEqual(nuevo["destino"], "ambos")
        from guyrapu.interaction import comandos
        encontrado = comandos.buscar(
            [comandos_guardados.a_comando(c) for c in comandos_guardados.cargar(
                self.rutas["comandos"])],
            comandos.leer("!prueba"))
        self.assertIsNotNone(encontrado)
        self.assertEqual(encontrado.respuesta, di.RESPUESTA_PRUEBA)
        disparadores = disparadores_guardados.cargar(
            self.rutas["disparadores"])
        disparador = next(d for d in disparadores if di.MARCA in d["nombre"])
        self.assertEqual(disparador["cuando"], "comando")
        self.assertIn("risa", disparador["comandos"])
        self.assertTrue(disparador["tarjeta"])
        encuestas = encuestas_guardadas.cargar(self.rutas["encuestas"])
        encuesta = next(e for e in encuestas if di.MARCA in e["pregunta"])
        self.assertEqual(len(encuesta["opciones"]), 2)
        self.assertEqual(encuesta["destino"], "chat")
        metas = metas_guardadas.cargar(self.rutas["metas"])
        meta = next(m for m in metas if di.MARCA in m["nombre"])
        self.assertEqual(meta["que_cuenta"], "super_chat")
        self.assertEqual(meta["objetivo"], 1)
        self.assertTrue(meta["en_video"])

    def test_la_restauracion_devuelve_los_bytes_previos(self):
        self._escribir_previos()
        antes = {clave: Path(ruta).read_bytes()
                 for clave, ruta in self.rutas.items()}
        datos = di.Datos(self.rutas)
        datos.preparar()
        datos.restaurar()
        for clave, ruta in self.rutas.items():
            with self.subTest(clave=clave):
                self.assertEqual(Path(ruta).read_bytes(), antes[clave])

    def test_la_restauracion_quitta_lo_que_no_existia(self):
        datos = di.Datos(self.rutas)
        datos.preparar()
        for ruta in self.rutas.values():
            self.assertTrue(os.path.exists(ruta))
        datos.restaurar()
        for ruta in self.rutas.values():
            with self.subTest(ruta=ruta):
                self.assertFalse(os.path.exists(ruta))

    def test_si_la_preparacion_falla_restaurara_lo_ya_respaldado(self):
        self._escribir_previos()
        antes = Path(self.rutas["comandos"]).read_bytes()
        rutas = dict(self.rutas)
        rutas["metas"] = os.path.join(self.carpeta, "sin-carpeta", "metas.json")
        with self.assertRaises(OSError):
            di.Datos(rutas).preparar()
        self.assertEqual(Path(self.rutas["comandos"]).read_bytes(), antes)


class TestEsperarTexto(unittest.TestCase):

    def test_coincide_por_fragmento_y_sin_mayusculas(self):
        self.assertTrue(di.coinciden("META CUMPLIDA: PRUEBA", "meta cumplida"))

    def test_no_coincide_si_falta_el_fragmento(self):
        self.assertFalse(di.coinciden("otra cosa", "meta cumplida"))

    def test_devuelve_el_detalle_al_vencer(self):
        bien, detalle = di.esperar_texto(lambda: "lo que se vio", "ausente", 0)
        self.assertFalse(bien)
        self.assertIn("sin «ausente» en 0 s", detalle)
        self.assertIn("lo que se vio", detalle)

    def test_ve_el_texto_cuando_aparece(self):
        bien, detalle = di.esperar_texto(lambda: "Algo META CUMPLIDA hoy",
                                         "meta cumplida", 0)
        self.assertTrue(bien)
        self.assertIn("meta cumplida", detalle)


class TestPasoComando(unittest.TestCase):

    def test_la_respuesta_esta_en_el_chat_y_en_la_tarjeta(self):
        anotar = _Anotador()
        enviados = []
        pasos = _pasos(
            anotar,
            enviar=enviados.append,
            respuesta=lambda: {"items": [{"snippet": {
                "displayMessage": di.RESPUESTA_PRUEBA}}]},
            texto_video=lambda: "tarjeta: " + di.RESPUESTA_PRUEBA)
        self.assertTrue(pasos.comando())
        self.assertEqual(enviados, ["!prueba"])
        self.assertEqual([p[0] for p in anotar.pasos],
                         ["comando !prueba en el chat",
                          "comando !prueba en la tarjeta"])
        self.assertTrue(all(p[1] for p in anotar.pasos))

    def test_sin_respuesta_en_el_chat_anota_el_fallo(self):
        anotar = _Anotador()
        self.assertFalse(_pasos(anotar, respuesta=lambda: {}).comando())
        self.assertFalse(anotar.pasos[0][1])
        self.assertIn("sin «", anotar.pasos[0][2])
        self.assertEqual(len(anotar.pasos), 1)


class TestPasoDisparador(unittest.TestCase):

    def test_la_tarjeta_del_disparador_aparece(self):
        anotar = _Anotador()
        enviados = []
        pasos = _pasos(anotar, enviar=enviados.append,
                       texto_video=lambda: di.TARJETA_RISA.lower())
        self.assertTrue(pasos.disparador())
        self.assertEqual(enviados, ["!risa"])
        self.assertEqual(anotar.pasos[0][0], "disparador !risa en la tarjeta")
        self.assertTrue(anotar.pasos[0][1])

    def test_sin_tarjeta_anota_el_fallo(self):
        anotar = _Anotador()
        self.assertFalse(_pasos(anotar).disparador())
        self.assertFalse(anotar.pasos[0][1])
        self.assertIn("en 0 s", anotar.pasos[0][2])


class TestPasoEncuesta(unittest.TestCase):

    def test_se_abre_se_vota_y_el_resultado_llega_al_chat(self):
        anotar = _Anotador()
        enviados, acciones = [], []
        pasos = _pasos(
            anotar,
            enviar=enviados.append,
            abrir_encuesta=lambda: acciones.append("abrir"),
            cerrar_encuesta=lambda: acciones.append("cerrar"),
            leer_anuncios=_anuncios(di.ANUNCIO_ENCUESTA, di.RESULTADO_UNO),
            respuesta=lambda: {"items": [{"snippet": {
                "displayMessage": di.OPCION_UNO}}]})
        self.assertTrue(pasos.encuesta())
        self.assertEqual(enviados, ["!1"])
        self.assertEqual(acciones, ["abrir", "cerrar"])
        self.assertEqual([p[0] for p in anotar.pasos],
                         ["encuesta abierta", "voto !1 contado",
                          "resultado de la encuesta",
                          "resultado de la encuesta en el chat"])
        self.assertTrue(all(p[1] for p in anotar.pasos))

    def test_sin_anuncio_de_apertura_anota_el_fallo(self):
        anotar = _Anotador()
        acciones = []
        pasos = _pasos(anotar, abrir_encuesta=lambda: acciones.append("abrir"))
        self.assertFalse(pasos.encuesta())
        self.assertEqual(acciones, ["abrir"])
        self.assertEqual(anotar.pasos[0][0], "encuesta abierta")
        self.assertFalse(anotar.pasos[0][1])


class TestPasoPregunta(unittest.TestCase):

    def test_la_pregunta_entra_y_se_lee_desde_la_app(self):
        anotar = _Anotador()
        enviados, acciones = [], []
        pasos = _pasos(
            anotar, enviar=enviados.append,
            leer_siguiente=lambda: acciones.append("leer"),
            leer_anuncios=_anuncios("Miguel pregunta: " + di.TEXTO_PREGUNTA))
        self.assertTrue(pasos.pregunta())
        self.assertEqual(enviados, ["!pregunta " + di.TEXTO_PREGUNTA])
        self.assertEqual(acciones, ["leer"])
        self.assertEqual(anotar.pasos[0][0], "leer siguiente pregunta")
        self.assertTrue(anotar.pasos[0][1])

    def test_sin_el_texto_anuncia_el_fallo(self):
        anotar = _Anotador()
        self.assertFalse(_pasos(anotar).pregunta())
        self.assertFalse(anotar.pasos[0][1])
        self.assertIn(di.TEXTO_PREGUNTA, anotar.pasos[0][2])


class TestPasoMeta(unittest.TestCase):

    def _pasos_meta(self, anotar, orden, **cambios):
        argumentos = dict(
            orden=orden,
            leer_anuncios=_anuncios("Meta cumplida: " + di.NOMBRE_META),
            texto_video=lambda: di.NOMBRE_META + ": meta cumplida")
        argumentos.update(cambios)
        return _pasos(anotar, **argumentos)

    def test_el_super_chat_cuenta_y_sale_en_el_anuncio_y_la_tarjeta(self):
        anotar = _Anotador()
        llamadas = []

        def orden(metodo, *args, **kwargs):
            llamadas.append((metodo, args, kwargs))

        self.assertTrue(self._pasos_meta(anotar, orden).meta())
        self.assertEqual(llamadas[0][0], "agregar_mensaje_chat")
        self.assertEqual(llamadas[0][1][3], "superchat")
        self.assertEqual(llamadas[0][2], {"plataforma": "youtube"})
        self.assertEqual([p[0] for p in anotar.pasos],
                         ["meta de superchat cumplida",
                          "meta de superchat en la tarjeta"])
        self.assertTrue(all(p[1] for p in anotar.pasos))

    def test_sin_la_meta_no_anota_bien(self):
        anotar = _Anotador()
        pasos = self._pasos_meta(anotar, lambda *a, **k: {},
                                 leer_anuncios=lambda ruta: "",
                                 texto_video=lambda: "")
        self.assertFalse(pasos.meta())
        self.assertFalse(anotar.pasos[0][1])
        self.assertIn("en 0 s", anotar.pasos[0][2])


class TestSinInteraccion(unittest.TestCase):

    def test_no_toca_nada_ni_instala_la_sonda(self):
        anotar = _Anotador()
        inter = di.Interaccion(False, "tmp", anotar)
        self.assertEqual(inter.entorno(), {})
        self.assertIn("import main", inter.arranque)
        inter.preparar()
        inter.pasar(object(), "chat", object(), lambda r: "", "anuncios.txt",
                    object(), lambda *a: None)
        inter.restaurar()
        self.assertEqual(anotar.pasos, [])


class TestPreparacionConSonda(unittest.TestCase):

    def test_si_falla_la_sonda_restaurara_las_colecciones(self):
        from contextlib import ExitStack
        from unittest import mock
        from guyrapu.core import paths

        carpeta = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, carpeta, True)
        rutas = {clave: os.path.join(carpeta, clave + ".json")
                 for clave in di.DATOS}
        for clave, ruta in rutas.items():
            _GUARDADOS[clave].guardar(ruta, [{"nombre": "previo " + clave}])
        antes = {clave: Path(ruta).read_bytes()
                 for clave, ruta in rutas.items()}
        with ExitStack() as pila:
            for clave, ruta in rutas.items():
                pila.enter_context(mock.patch.object(
                    paths, clave, lambda ruta=ruta: Path(ruta)))
            with self.assertRaises(OSError):
                di.Interaccion(
                    True, os.path.join(carpeta, "sin-carpeta"),
                    lambda *a: None).preparar()
        for clave, ruta in rutas.items():
            with self.subTest(clave=clave):
                self.assertEqual(Path(ruta).read_bytes(), antes[clave])


class TestArranqueConSonda(unittest.TestCase):

    def test_instala_la_sonda_y_lleva_los_anuncios_al_registro(self):
        from qa import directo_real
        inter = di.Interaccion(True, "tmp", lambda *a: None)
        fuente = directo_real._LANZADOR.format(
            repo="C:/x", arranque=inter.arranque)
        compile(fuente, "lanzador", "exec")
        self.assertIn("sonda.arrancar_aplicacion", fuente)
        self.assertIn("_acc.anunciar = _anunciar", fuente)
        self.assertEqual(inter.entorno(), {
            di.VAR_ANUNCIOS: os.path.join("tmp", "anuncios-sonda.jsonl"),
            di.VAR_ORDENES: os.path.join("tmp", "ordenes.jsonl"),
            di.VAR_RESULTADOS: os.path.join("tmp", "resultados.jsonl")})


class TestAyudaDelDirecto(unittest.TestCase):

    def test_el_directo_tiene_la_opcion_interaccion(self):
        from qa import directo_real
        ayuda = directo_real._ayuda()
        self.assertIsNotNone(ayuda.parse_args(["--interaccion"]).interaccion)
        self.assertFalse(ayuda.parse_args([]).interaccion)


if __name__ == "__main__":
    unittest.main()
