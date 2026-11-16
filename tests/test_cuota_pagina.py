# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de la tabla de costos que publica Google para la API de YouTube."""

import datetime as dt
import http.server
import json
import os
import socket
import tempfile
import threading
import unittest
import urllib.error
from unittest import mock

from guyrapu.core import paths
from guyrapu.youtube import cuota, cuota_pagina
from tests.rutas_temporales import redirigir_rutas


# Forma medida de la página: el recurso en un <h3> solo en la primera fila
# del grupo, el método en el segundo <td> y el costo en «quota-cost».
FRAGMENTO = (
    '<tr><td><h3 id="videos">videos</h3></td><td></td><td></td></tr>'
    '<tr><td></td><td>list</td><td class="quota-cost">1</td></tr>'
    '<tr><td></td><td>update</td><td class="quota-cost">50</td></tr>'
    '<tr><td><h3 id="liveChatMessages">liveChatMessages</h3></td>'
    '<td></td><td></td></tr>'
    '<tr><td></td><td>insert</td><td class="quota-cost">20</td></tr>'
    "<p>Last updated 2026-11-12</p>"
)

COSTOS_DEL_FRAGMENTO = {
    "videos.list": 1,
    "videos.update": 50,
    "liveChatMessages.insert": 20,
}


def _pagina(costos, fecha="2026-11-12"):
    """La página de prueba con todos los métodos de `costos`."""
    filas, recurso = [], None
    for clave, costo in costos.items():
        nombre_recurso, metodo = clave.split(".", 1)
        if nombre_recurso != recurso:
            filas.append(f'<tr><td><h3 id="{nombre_recurso}">'
                         f'{nombre_recurso}</h3></td><td></td><td></td></tr>')
            recurso = nombre_recurso
        filas.append(f'<tr><td></td><td>{metodo}</td>'
                     f'<td class="quota-cost">{costo}</td></tr>')
    return f"<p>Last updated {fecha}</p>" + "".join(filas)


def _guardado(leida, costos=None):
    return {"fecha": "12/11/2026", "leida": leida,
            "costos": costos if costos is not None else {}}


class TestLector(unittest.TestCase):

    def test_lee_los_costos_y_la_fecha_del_fragmento(self):
        costos, fecha = cuota_pagina.tabla_de_la_pagina(FRAGMENTO)
        self.assertEqual(costos, COSTOS_DEL_FRAGMENTO)
        self.assertEqual(fecha, "12/11/2026")


class TestCuadra(unittest.TestCase):

    def test_cuadra_con_fecha_y_todos_los_metodos(self):
        self.assertTrue(cuota_pagina.cuadra(
            COSTOS_DEL_FRAGMENTO, "12/11/2026", COSTOS_DEL_FRAGMENTO))

    def test_no_cuadra_si_falta_un_metodo(self):
        self.assertFalse(cuota_pagina.cuadra(
            COSTOS_DEL_FRAGMENTO, "12/11/2026",
            list(COSTOS_DEL_FRAGMENTO) + ["search.list"]))

    def test_no_cuadra_sin_fecha(self):
        self.assertFalse(cuota_pagina.cuadra(
            COSTOS_DEL_FRAGMENTO, "", COSTOS_DEL_FRAGMENTO))


class TestTocaLeer(unittest.TestCase):

    AHORA = dt.date(2026, 11, 16)

    def test_sin_lectura_previa_toca(self):
        self.assertTrue(cuota_pagina.toca_leer(None, self.AHORA))

    def test_con_seis_dias_no_toca(self):
        guardado = _guardado((self.AHORA - dt.timedelta(days=6)).isoformat())
        self.assertFalse(cuota_pagina.toca_leer(guardado, self.AHORA))

    def test_con_ocho_dias_toca(self):
        guardado = _guardado((self.AHORA - dt.timedelta(days=8)).isoformat())
        self.assertTrue(cuota_pagina.toca_leer(guardado, self.AHORA))


class _Manejador(http.server.BaseHTTPRequestHandler):

    cuerpo = b""
    cabeceras = {}

    def do_GET(self):
        _Manejador.cabeceras = dict(self.headers)
        self.send_response(200)
        self.send_header("Content-Length", str(len(self.cuerpo)))
        self.end_headers()
        self.wfile.write(self.cuerpo)

    def log_message(self, *args):
        pass


class TestDescargar(unittest.TestCase):

    def _servir(self, texto):
        _Manejador.cuerpo = texto.encode("utf-8")
        _Manejador.cabeceras = {}
        servidor = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Manejador)
        threading.Thread(target=servidor.serve_forever, daemon=True).start()
        self.addCleanup(servidor.server_close)
        self.addCleanup(servidor.shutdown)
        return f"http://127.0.0.1:{servidor.server_address[1]}/"

    def test_trae_el_texto_de_un_servidor_local(self):
        url = self._servir(FRAGMENTO)
        self.assertEqual(cuota_pagina.descargar(url, 5), FRAGMENTO)

    def test_manda_el_agente_de_la_app(self):
        url = self._servir(FRAGMENTO)
        cuota_pagina.descargar(url, 5)
        self.assertEqual(_Manejador.cabeceras.get("User-Agent"), "guyrapu")

    def test_vence_el_tope_si_el_servidor_no_contesta(self):
        escucha = socket.socket()
        escucha.bind(("127.0.0.1", 0))
        escucha.listen(1)
        self.addCleanup(escucha.close)
        puerto = escucha.getsockname()[1]
        aceptadas = []
        threading.Thread(
            target=lambda: aceptadas.append(escucha.accept()[0]),
            daemon=True).start()
        try:
            with self.assertRaises((urllib.error.URLError, TimeoutError)):
                cuota_pagina.descargar(f"http://127.0.0.1:{puerto}/", 0.3)
        finally:
            for conexion in aceptadas:
                conexion.close()


class TestActualizar(unittest.TestCase):

    def setUp(self):
        self.excepciones = []
        anterior = threading.excepthook
        threading.excepthook = self.excepciones.append
        self.addCleanup(setattr, threading, "excepthook", anterior)

    def test_guarda_cuando_la_lectura_cuadra(self):
        with tempfile.TemporaryDirectory() as tmp, redirigir_rutas(tmp):
            with mock.patch.object(cuota_pagina, "descargar",
                                   return_value=_pagina(cuota.COSTOS)):
                hilo = cuota_pagina.actualizar_en_segundo_plano()
                self.assertIsNotNone(hilo)
                hilo.join(5)
            guardado = json.loads(
                paths.cuota_youtube_pagina().read_text(encoding="utf-8"))
        self.assertFalse(hilo.is_alive())
        self.assertEqual([], self.excepciones)
        self.assertEqual("12/11/2026", guardado["fecha"])
        self.assertEqual(dt.date.today().isoformat(), guardado["leida"])
        self.assertEqual(cuota.COSTOS, guardado["costos"])

    def test_no_lee_si_la_ultima_lectura_es_reciente(self):
        with tempfile.TemporaryDirectory() as tmp, redirigir_rutas(tmp):
            paths.cuota_youtube_pagina().write_text(
                json.dumps(_guardado(dt.date.today().isoformat())),
                encoding="utf-8")
            with mock.patch.object(cuota_pagina, "descargar") as descargar:
                self.assertIsNone(
                    cuota_pagina.actualizar_en_segundo_plano())
        descargar.assert_not_called()

    def test_lee_si_la_ultima_lectura_tiene_mas_de_siete_dias(self):
        with tempfile.TemporaryDirectory() as tmp, redirigir_rutas(tmp):
            vieja = (dt.date.today() - dt.timedelta(days=8)).isoformat()
            paths.cuota_youtube_pagina().write_text(
                json.dumps(_guardado(vieja)), encoding="utf-8")
            with mock.patch.object(cuota_pagina, "descargar",
                                   return_value=_pagina(cuota.COSTOS)) as descargar:
                hilo = cuota_pagina.actualizar_en_segundo_plano()
                hilo.join(5)
        self.assertFalse(hilo.is_alive())
        descargar.assert_called_once()

    def test_sin_red_deja_registro_y_no_cambia_el_archivo(self):
        with tempfile.TemporaryDirectory() as tmp, redirigir_rutas(tmp):
            ruta = paths.cuota_youtube_pagina()
            leida = (dt.date.today() - dt.timedelta(days=30)).isoformat()
            antes = json.dumps(_guardado(leida, {"videos.list": 3}))
            ruta.write_text(antes, encoding="utf-8")
            with mock.patch.object(cuota_pagina, "descargar",
                                   side_effect=OSError("sin red")):
                with self.assertLogs(cuota_pagina.logger,
                                     level="WARNING") as registros:
                    hilo = cuota_pagina.actualizar_en_segundo_plano()
                    hilo.join(5)
            despues = ruta.read_text(encoding="utf-8")
        self.assertFalse(hilo.is_alive())
        self.assertEqual([], self.excepciones)
        self.assertEqual(antes, despues)
        self.assertTrue(any("costos" in linea for linea in registros.output))

    def test_pagina_cambiada_deja_registro_y_no_cambia_el_archivo(self):
        with tempfile.TemporaryDirectory() as tmp, redirigir_rutas(tmp):
            ruta = paths.cuota_youtube_pagina()
            leida = (dt.date.today() - dt.timedelta(days=30)).isoformat()
            antes = json.dumps(_guardado(leida, {"videos.list": 3}))
            ruta.write_text(antes, encoding="utf-8")
            with mock.patch.object(cuota_pagina, "descargar",
                                   return_value=FRAGMENTO):
                with self.assertLogs(cuota_pagina.logger,
                                     level="WARNING") as registros:
                    hilo = cuota_pagina.actualizar_en_segundo_plano()
                    hilo.join(5)
            despues = ruta.read_text(encoding="utf-8")
        self.assertFalse(hilo.is_alive())
        self.assertEqual([], self.excepciones)
        self.assertEqual(antes, despues)
        self.assertTrue(any("no cuadra" in linea for linea in registros.output))


@unittest.skipUnless(os.environ.get("GUYRAPU_PRUEBAS_CON_RED") == "1",
                     "la página real necesita GUYRAPU_PRUEBAS_CON_RED=1")
class TestPaginaReal(unittest.TestCase):

    def test_la_lectura_cuadra_con_la_tabla_de_hoy(self):
        texto = cuota_pagina.descargar(cuota_pagina.PAGINA, 15)
        costos, fecha = cuota_pagina.tabla_de_la_pagina(texto)
        self.assertTrue(cuota_pagina.cuadra(costos, fecha, cuota.COSTOS))


if __name__ == "__main__":
    unittest.main()
