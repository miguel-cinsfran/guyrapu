# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas del cliente del carril contra un complemento de mentira."""

import json
import socket
import tempfile
import threading
import unittest
from pathlib import Path

from qa.nvda import cliente


class ServidorFalso:

    def __init__(self, respuestas=None):
        self.respuestas = respuestas or {}
        self.recibidos = []
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.bind(("127.0.0.1", 0))
        self._socket.listen(4)
        self._socket.settimeout(5.0)
        self.puerto = self._socket.getsockname()[1]
        self._vivo = True
        self._hilo = threading.Thread(target=self._aceptar, daemon=True)
        self._hilo.start()

    def _aceptar(self):
        while self._vivo:
            try:
                conexion, _ = self._socket.accept()
            except (OSError, socket.timeout):
                return
            with conexion:
                archivo = conexion.makefile("rwb")
                linea = archivo.readline()
                if not linea:
                    continue
                pedido = json.loads(linea.decode("utf-8"))
                self.recibidos.append(pedido)
                respuesta = self.respuestas.get(
                    pedido.get("orden"), {"ok": True})
                if callable(respuesta):
                    respuesta = respuesta(pedido, len(self.recibidos))
                archivo.write(
                    (json.dumps(respuesta) + "\n").encode("utf-8"))
                archivo.flush()

    def cerrar(self):
        self._vivo = False
        self._socket.close()
        self._hilo.join(2.0)


class EstadoTemporal:

    def __init__(self, puerto, clave="abc"):
        self._carpeta = tempfile.TemporaryDirectory()
        self.ruta = Path(self._carpeta.name) / "carril.json"
        self.ruta.write_text(json.dumps(
            {"puerto": puerto, "clave": clave}), encoding="utf-8")

    def cerrar(self):
        self._carpeta.cleanup()


class TestLeerEstado(unittest.TestCase):

    def test_sin_archivo_lo_dice(self):
        with tempfile.TemporaryDirectory() as base:
            with self.assertRaises(cliente.ErrorCliente):
                cliente.leer_estado(Path(base) / "carril.json")

    def test_sin_puerto_o_clave_lo_dice(self):
        with tempfile.TemporaryDirectory() as base:
            ruta = Path(base) / "carril.json"
            ruta.write_text('{"puerto": 1}', encoding="utf-8")
            with self.assertRaises(cliente.ErrorCliente):
                cliente.leer_estado(ruta)


class TestPedidos(unittest.TestCase):

    def setUp(self):
        self.servidor = ServidorFalso({
            "version": {"ok": True, "version": "2026.3.1"},
            "marca": lambda pedido, n: {"ok": True, "indice": 7},
            "tecla": {"ok": True, "indice": 8, "agotado": False,
                      "hora": 1.5},
            "desde": {"ok": True, "eventos": [{"tipo": "habla"}]},
            "foco": {"ok": True, "foco": {"nombre": "Aceptar"},
                     "primer_plano": {"pid": 7, "nombre": "Ventana"}},
        })
        self.estado = EstadoTemporal(self.servidor.puerto)

    def tearDown(self):
        self.servidor.cerrar()
        self.estado.cerrar()

    def test_version_manda_la_clave_del_estado(self):
        self.assertEqual(cliente.Cliente(self.estado.ruta).version(),
                         "2026.3.1")
        self.assertEqual(self.servidor.recibidos[0]["clave"], "abc")

    def test_tecla_pide_espera_y_tope(self):
        respuesta = cliente.Cliente(self.estado.ruta).tecla(
            "tab", silencio_ms=300, tope_ms=5000)
        self.assertFalse(respuesta["agotado"])
        pedido = self.servidor.recibidos[0]
        self.assertEqual(pedido["gesto"], "tab")
        self.assertEqual(pedido["silencio_ms"], 300)
        self.assertEqual(pedido["tope_ms"], 5000)

    def test_paso_devuelve_lo_dicho_desde_la_marca_y_el_foco(self):
        resultado = cliente.Cliente(self.estado.ruta).paso("tab")
        ordenes = [pedido["orden"] for pedido in self.servidor.recibidos]
        self.assertEqual(ordenes, ["marca", "tecla", "desde", "foco"])
        self.assertEqual(resultado["eventos"], [{"tipo": "habla"}])
        self.assertEqual(resultado["foco"], {"nombre": "Aceptar"})
        self.assertEqual(resultado["hora"], 1.5)
        self.assertEqual(self.servidor.recibidos[2]["indice"], 7)

    def test_foco_completo_trae_el_primer_plano(self):
        respuesta = cliente.Cliente(self.estado.ruta).foco_completo()
        self.assertEqual(respuesta["foco"], {"nombre": "Aceptar"})
        self.assertEqual(respuesta["primer_plano"],
                         {"pid": 7, "nombre": "Ventana"})

    def test_una_respuesta_rechazada_levanta_error(self):
        self.servidor.respuestas["version"] = {
            "ok": False, "error": "clave inválida"}
        with self.assertRaises(cliente.ErrorCliente):
            cliente.Cliente(self.estado.ruta).version()


class TestEsperarCliente(unittest.TestCase):

    def test_espera_hasta_que_el_complemento_contesta(self):
        servidor = ServidorFalso({
            "version": {"ok": True, "version": "2026.3.1"}})
        estado = EstadoTemporal(servidor.puerto)
        try:
            armado = cliente.esperar_cliente(
                estado.ruta, tope_s=2.0, dormir=lambda _s: None)
            self.assertEqual(armado.version(), "2026.3.1")
        finally:
            servidor.cerrar()
            estado.cerrar()

    def test_se_cansa_si_no_aparece_el_estado(self):
        with tempfile.TemporaryDirectory() as base:
            with self.assertRaises(cliente.ErrorCliente):
                cliente.esperar_cliente(
                    Path(base) / "carril.json", tope_s=0.2,
                    dormir=lambda _s: None)
