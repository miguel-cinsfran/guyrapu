# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas del módulo de red de httpx, con un servidor HTTP local."""

import http.server
import threading
import time
import unittest

import httpx

from guyrapu.core import red_httpx


class Servidor(http.server.BaseHTTPRequestHandler):
    estado = 200
    cuerpo = b""
    demora = 0.0

    def do_GET(self):
        if type(self).demora:
            time.sleep(type(self).demora)
        cuerpo = type(self).cuerpo
        try:
            self.send_response(type(self).estado)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(cuerpo)))
            self.end_headers()
            self.wfile.write(cuerpo)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def log_message(self, *args):
        pass


class TestRedHttpx(unittest.TestCase):

    def _servidor(self, estado=200, cuerpo=b"", demora=0.0):
        Servidor.estado = estado
        Servidor.cuerpo = cuerpo
        Servidor.demora = demora
        servidor = http.server.HTTPServer(("127.0.0.1", 0), Servidor)
        hilo = threading.Thread(target=servidor.serve_forever, daemon=True)
        hilo.start()
        self.addCleanup(servidor.server_close)
        self.addCleanup(servidor.shutdown)
        return servidor

    def test_un_get_vuelve_su_estado_y_su_texto(self):
        servidor = self._servidor(estado=201, cuerpo=b"hola")
        with red_httpx.cliente() as cliente:
            respuesta = cliente.get(
                f"http://127.0.0.1:{servidor.server_port}/x", timeout=10)
        self.assertEqual(respuesta.status_code, 201)
        self.assertEqual(respuesta.text, "hola")

    def test_sin_respuesta_a_tiempo_es_tiempo_agotado(self):
        servidor = self._servidor(cuerpo=b"tarde", demora=1.5)
        with red_httpx.cliente() as cliente:
            with self.assertRaises(red_httpx.TiempoAgotado):
                cliente.get(
                    f"http://127.0.0.1:{servidor.server_port}/x", timeout=0.2)

    def test_el_cliente_no_usa_http2(self):
        with red_httpx.cliente() as cliente:
            self.assertIsInstance(cliente, httpx.Client)
            # httpx no expone http2 en el cliente: queda en el pool de httpcore.
            self.assertFalse(cliente._transport._pool._http2)

    def test_las_excepciones_son_las_de_httpx(self):
        self.assertIs(red_httpx.TiempoAgotado, httpx.TimeoutException)
        self.assertIs(red_httpx.ErrorTransporte, httpx.TransportError)
        self.assertIs(red_httpx.ErrorHTTP, httpx.HTTPError)


if __name__ == "__main__":
    unittest.main()
