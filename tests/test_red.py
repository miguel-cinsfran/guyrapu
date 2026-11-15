# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas del módulo de red común, con un servidor HTTP local."""

import http.server
import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError

from guyrapu.core import red
from guyrapu.core.config import USER_AGENT


class Servidor(http.server.BaseHTTPRequestHandler):
    contenido = b""
    con_longitud = True
    cabecera = None
    agente = None
    codigo = 200
    metodo = None
    cuerpo = None

    def _responder(self):
        cuerpo = type(self).contenido
        type(self).cabecera = self.headers.get("X-Prueba")
        type(self).agente = self.headers.get("User-Agent")
        type(self).metodo = self.command
        largo = int(self.headers.get("Content-Length") or 0)
        type(self).cuerpo = self.rfile.read(largo) if largo else b""
        self.send_response(type(self).codigo)
        if type(self).con_longitud:
            self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    def do_GET(self):
        self._responder()

    def do_POST(self):
        self._responder()

    def log_message(self, *args):
        pass


def _servidor():
    Servidor.codigo = 200
    servidor = http.server.HTTPServer(("127.0.0.1", 0), Servidor)
    hilo = threading.Thread(target=servidor.serve_forever, daemon=True)
    hilo.start()
    return servidor


class TestDescargarArchivo(unittest.TestCase):

    def _arrancar(self):
        servidor = _servidor()
        # LIFO: primero se apaga el bucle y después se cierra el socket.
        self.addCleanup(servidor.server_close)
        self.addCleanup(servidor.shutdown)
        return f"http://127.0.0.1:{servidor.server_port}/x"

    def test_escribe_el_archivo_y_avisa_el_progreso(self):
        Servidor.contenido = b"datos de prueba"
        Servidor.con_longitud = True
        url = self._arrancar()
        avisos = []
        with tempfile.TemporaryDirectory() as tmp:
            destino = Path(tmp) / "x.bin"
            red.descargar_archivo(url, destino, aviso=avisos.append)
            self.assertEqual(destino.read_bytes(), b"datos de prueba")
        self.assertEqual(avisos[-1], 100)

    def test_sin_longitud_avisa_none(self):
        Servidor.contenido = b"datos"
        Servidor.con_longitud = False
        url = self._arrancar()
        avisos = []
        with tempfile.TemporaryDirectory() as tmp:
            red.descargar_archivo(url, Path(tmp) / "x.bin", aviso=avisos.append)
        self.assertEqual(avisos, [None])

    def test_cancelar_levanta_descarga_cancelada(self):
        Servidor.contenido = b"datos"
        Servidor.con_longitud = True
        url = self._arrancar()
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(red.DescargaCancelada):
                red.descargar_archivo(
                    url, Path(tmp) / "x.bin", cancelar=lambda: True)

    def test_agrega_las_cabeceras_a_la_peticion(self):
        Servidor.contenido = b"datos"
        Servidor.con_longitud = True
        url = self._arrancar()
        with tempfile.TemporaryDirectory() as tmp:
            red.descargar_archivo(url, Path(tmp) / "x.bin",
                                  cabeceras={"X-Prueba": "valor"})
        self.assertEqual(Servidor.cabecera, "valor")


class TestPedirTexto(unittest.TestCase):

    def test_devuelve_el_texto_en_utf8(self):
        Servidor.contenido = "ñandú".encode("utf-8")
        Servidor.con_longitud = True
        servidor = _servidor()
        self.addCleanup(servidor.server_close)
        self.addCleanup(servidor.shutdown)
        url = f"http://127.0.0.1:{servidor.server_port}/x"
        self.assertEqual(red.pedir_texto(url), "ñandú")


class TestPedirJson(unittest.TestCase):

    def _arrancar(self):
        servidor = _servidor()
        self.addCleanup(servidor.server_close)
        self.addCleanup(servidor.shutdown)
        return f"http://127.0.0.1:{servidor.server_port}/x"

    def test_devuelve_el_json_servido_y_manda_el_user_agent(self):
        Servidor.contenido = json.dumps({"clave": ["valor"]}).encode("utf-8")
        Servidor.con_longitud = True
        url = self._arrancar()
        self.assertEqual(red.pedir_json(url), {"clave": ["valor"]})
        self.assertEqual(Servidor.agente, USER_AGENT)

    def test_un_404_sale_como_http_error(self):
        url = self._arrancar()
        Servidor.codigo = 404
        Servidor.contenido = b""
        Servidor.con_longitud = True
        with self.assertRaises(HTTPError):
            red.pedir_json(url)


class TestPedir(unittest.TestCase):

    def _arrancar(self):
        servidor = _servidor()
        self.addCleanup(servidor.server_close)
        self.addCleanup(servidor.shutdown)
        return f"http://127.0.0.1:{servidor.server_port}/x"

    def test_un_post_llega_con_cuerpo_y_cabecera_y_vuelve_en_bytes(self):
        Servidor.contenido = b"respuesta"
        Servidor.con_longitud = True
        url = self._arrancar()
        bruto = red.pedir(url, datos=b'{"texto":"hola"}',
                          cabeceras={"X-Prueba": "valor"},
                          metodo="POST", tiempo=5)
        self.assertEqual(bruto, b"respuesta")
        self.assertEqual(Servidor.metodo, "POST")
        self.assertEqual(Servidor.cuerpo, b'{"texto":"hola"}')
        self.assertEqual(Servidor.cabecera, "valor")
        self.assertEqual(Servidor.agente, USER_AGENT)

    def test_un_401_sale_como_http_error(self):
        url = self._arrancar()
        Servidor.codigo = 401
        Servidor.contenido = b""
        Servidor.con_longitud = True
        with self.assertRaises(HTTPError):
            red.pedir(url)
