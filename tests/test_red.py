# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas del módulo de red común, con un servidor HTTP local."""

import http.server
import tempfile
import threading
import unittest
from pathlib import Path

from guyrapu.core import red


class Servidor(http.server.BaseHTTPRequestHandler):
    contenido = b""
    con_longitud = True

    def do_GET(self):
        cuerpo = type(self).contenido
        self.send_response(200)
        if type(self).con_longitud:
            self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    def log_message(self, *args):
        pass


def _servidor():
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


class TestPedirTexto(unittest.TestCase):

    def test_devuelve_el_texto_en_utf8(self):
        Servidor.contenido = "ñandú".encode("utf-8")
        Servidor.con_longitud = True
        servidor = _servidor()
        self.addCleanup(servidor.server_close)
        self.addCleanup(servidor.shutdown)
        url = f"http://127.0.0.1:{servidor.server_port}/x"
        self.assertEqual(red.pedir_texto(url), "ñandú")
