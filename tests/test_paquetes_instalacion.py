# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de la instalación de paquetes, con un servidor HTTP local."""

import collections
import hashlib
import http.server
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from guyrapu.core import paquetes_instalacion
from guyrapu.core import paths

Uso = collections.namedtuple("Uso", "total used free")


class Servidor(http.server.BaseHTTPRequestHandler):
    archivos = {}
    pedidos = []

    def do_GET(self):
        type(self).pedidos.append(self.path)
        cuerpo = type(self).archivos.get(self.path)
        if cuerpo is None:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    def log_message(self, *args):
        pass


def _servidor(archivos):
    Servidor.archivos = dict(archivos)
    Servidor.pedidos = []
    servidor = http.server.HTTPServer(("127.0.0.1", 0), Servidor)
    hilo = threading.Thread(target=servidor.serve_forever, daemon=True)
    hilo.start()
    return servidor


def _base_url(servidor):
    return f"http://127.0.0.1:{servidor.server_port}"


def _sha256(datos):
    return hashlib.sha256(datos).hexdigest()


def _paquete(base, version=1, archivos=None):
    archivos = archivos or {"uno.bin": b"uno", "dos.bin": b"dos"}
    return {
        "id": "voz-prueba",
        "tipo": "voz",
        "proveedor": "prueba",
        "nombre": "Voz de prueba",
        "idioma": "es-AR",
        "version": version,
        "guyrapu_minima": "2.0.0",
        "licencia": "CC0",
        "licencia_url": "https://ejemplo.com/licencia",
        "origen": "prueba",
        "voces": [],
        "archivos": [{
            "url": f"{base}/{ruta}",
            "bytes": len(datos),
            "sha256": _sha256(datos),
            "ruta": ruta,
        } for ruta, datos in archivos.items()],
    }


def _foto(carpeta):
    if not carpeta.exists():
        return {}
    return {str(ruta.relative_to(carpeta)): ruta.read_bytes()
            for ruta in sorted(carpeta.rglob("*")) if ruta.is_file()}


class BasePaquetes(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.raiz = Path(self._tmp.name)
        self.base = self.raiz / "voces"
        parche = mock.patch.object(
            paths, "carpeta_instalacion", return_value=self.raiz)
        parche.start()
        self.addCleanup(parche.stop)

    def _servir(self, archivos):
        servidor = _servidor(archivos)
        # LIFO: primero se apaga el bucle y después se cierra el socket.
        self.addCleanup(servidor.server_close)
        self.addCleanup(servidor.shutdown)
        return servidor

    def _pasos(self):
        return [ruta.name for ruta in self.base.iterdir()
                if ruta.name.startswith(".")]


class TestInstalar(BasePaquetes):

    def test_paquete_bueno_queda_instalado_con_su_ficha(self):
        servidor = self._servir({"/uno.bin": b"uno", "/dos.bin": b"dos"})
        paquete = _paquete(_base_url(servidor))
        resultado = paquetes_instalacion.instalar(paquete)
        self.assertTrue(resultado.correcta, resultado.motivo)
        destino = self.base / "voz-prueba"
        self.assertEqual((destino / "uno.bin").read_bytes(), b"uno")
        self.assertEqual((destino / "dos.bin").read_bytes(), b"dos")
        ficha = json.loads((destino / "paquete.json").read_text(encoding="utf-8"))
        self.assertEqual(ficha["id"], "voz-prueba")
        self.assertEqual(ficha["version"], 1)
        self.assertIn("instalado", ficha)
        self.assertEqual(self._pasos(), [])

    def test_sha_equivocado_deja_todo_como_estaba(self):
        servidor = self._servir({"/uno.bin": b"uno", "/dos.bin": b"dos"})
        paquete = _paquete(_base_url(servidor))
        self.assertTrue(paquetes_instalacion.instalar(paquete).correcta)
        antes = _foto(self.base)
        nuevo = _paquete(_base_url(servidor), version=2)
        nuevo["archivos"][1]["sha256"] = _sha256(b"otra cosa")
        Servidor.archivos["/dos.bin"] = b"distinto"
        resultado = paquetes_instalacion.instalar(nuevo)
        self.assertFalse(resultado.correcta)
        self.assertIn("SHA-256", resultado.motivo)
        self.assertEqual(_foto(self.base), antes)
        self.assertEqual(self._pasos(), [])

    def test_cancelar_en_el_segundo_archivo_no_deja_paso(self):
        servidor = self._servir({"/uno.bin": b"uno", "/dos.bin": b"dos"})
        paquete = _paquete(_base_url(servidor))
        llamadas = []

        def cancelar():
            llamadas.append(1)
            return len(llamadas) >= 3

        resultado = paquetes_instalacion.instalar(paquete, cancelar=cancelar)
        self.assertFalse(resultado.correcta)
        self.assertTrue(resultado.cancelada)
        self.assertFalse((self.base / "voz-prueba").exists())
        self.assertEqual(self._pasos(), [])

    def test_actualizar_deja_solo_la_version_nueva(self):
        servidor = self._servir({"/uno.bin": b"uno", "/dos.bin": b"dos"})
        self.assertTrue(paquetes_instalacion.instalar(
            _paquete(_base_url(servidor))).correcta)
        Servidor.archivos.update({"/uno.bin": b"uno nuevo",
                                  "/dos.bin": b"dos nuevo"})
        nuevo = _paquete(_base_url(servidor), version=2,
                         archivos={"uno.bin": b"uno nuevo",
                                   "dos.bin": b"dos nuevo"})
        self.assertTrue(paquetes_instalacion.instalar(nuevo).correcta)
        destino = self.base / "voz-prueba"
        self.assertEqual((destino / "uno.bin").read_bytes(), b"uno nuevo")
        ficha = json.loads((destino / "paquete.json").read_text(encoding="utf-8"))
        self.assertEqual(ficha["version"], 2)
        self.assertEqual(self._pasos(), [])

    def test_falla_al_renombrar_y_vuelve_la_vieja(self):
        servidor = self._servir({"/uno.bin": b"uno", "/dos.bin": b"dos"})
        self.assertTrue(paquetes_instalacion.instalar(
            _paquete(_base_url(servidor))).correcta)
        antes = _foto(self.base)
        real = paquetes_instalacion.os.replace
        llamadas = []

        def fallar(origen, destino):
            llamadas.append(1)
            if len(llamadas) == 2:
                raise OSError("falla simulada")
            return real(origen, destino)

        nuevo = _paquete(_base_url(servidor), version=2)
        with mock.patch.object(paquetes_instalacion.os, "replace",
                               side_effect=fallar):
            resultado = paquetes_instalacion.instalar(nuevo)
        self.assertFalse(resultado.correcta)
        self.assertEqual(_foto(self.base), antes)
        self.assertEqual(self._pasos(), [])

    def test_sin_espacio_no_baja_nada(self):
        servidor = self._servir({"/uno.bin": b"uno", "/dos.bin": b"dos"})
        paquete = _paquete(_base_url(servidor))
        with mock.patch.object(paquetes_instalacion.shutil, "disk_usage",
                               return_value=Uso(0, 0, 0)):
            resultado = paquetes_instalacion.instalar(paquete)
        self.assertFalse(resultado.correcta)
        self.assertIn("espacio", resultado.motivo)
        self.assertEqual(Servidor.pedidos, [])
        self.assertEqual(_foto(self.base), {})

    def test_borrar_quita_el_paquete(self):
        servidor = self._servir({"/uno.bin": b"uno", "/dos.bin": b"dos"})
        self.assertTrue(paquetes_instalacion.instalar(
            _paquete(_base_url(servidor))).correcta)
        resultado = paquetes_instalacion.borrar("voz-prueba", "voz")
        self.assertTrue(resultado.correcta, resultado.motivo)
        self.assertFalse((self.base / "voz-prueba").exists())


class TestInstalados(BasePaquetes):

    def test_lee_las_fichas_y_limpia_restos(self):
        (self.base / ".vieja.descarga").mkdir(parents=True)
        (self.base / ".vieja.descarga" / "resto.bin").write_bytes(b"x")
        (self.base / ".vieja.vieja").mkdir()
        (self.base / "buena").mkdir()
        (self.base / "buena" / "paquete.json").write_text(
            json.dumps({"id": "buena", "version": 1}), encoding="utf-8")
        (self.base / "sin_ficha").mkdir()
        (self.base / "rota").mkdir()
        (self.base / "rota" / "paquete.json").write_text("{", encoding="utf-8")
        fichas = paquetes_instalacion.instalados("voz")
        self.assertEqual([ficha["id"] for ficha in fichas], ["buena"])
        self.assertFalse((self.base / ".vieja.descarga").exists())
        self.assertFalse((self.base / ".vieja.vieja").exists())
        self.assertTrue((self.base / "sin_ficha").exists())
