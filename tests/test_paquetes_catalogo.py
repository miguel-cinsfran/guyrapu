# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas del formato del catálogo de paquetes, sin red ni disco."""

import json
import unittest

from guyrapu.core import paquetes_catalogo

VERSION_APP = "2.5.0"


def _paquete():
    return {
        "id": "piper-es-ar-daniela-high",
        "tipo": "voz",
        "proveedor": "piper",
        "nombre": "Piper Daniela",
        "idioma": "es-AR",
        "version": 1,
        "guyrapu_minima": "2.0.0",
        "licencia": "CC BY-SA 4.0",
        "licencia_url": "https://huggingface.co/rhasspy/piper-voices",
        "origen": "Piper, rhasspy/piper-voices",
        "voces": [{
            "nombre": "Daniela",
            "idioma": "es-AR",
            "genero": None,
            "muestra": "https://ejemplo.com/muestra.mp3",
            "archivo": "es_AR-daniela-high.onnx",
        }],
        "archivos": [{
            "url": "https://ejemplo.com/daniela.onnx",
            "bytes": 10,
            "sha256": "a" * 64,
            "ruta": "es_AR-daniela-high.onnx",
        }],
    }


def _catalogo(*paquetes):
    return json.dumps({"formato": 1, "paquetes": list(paquetes)})


def _leer(paquete=None):
    return paquetes_catalogo.leer(
        _catalogo(paquete or _paquete()), VERSION_APP, {"voz"}, {"piper"})


class TestLeer(unittest.TestCase):

    def test_un_paquete_valido_se_lee(self):
        paquetes, descartes = _leer()
        self.assertEqual(descartes, [])
        self.assertEqual([paquete["id"] for paquete in paquetes],
                         ["piper-es-ar-daniela-high"])

    def test_formato_mas_nuevo_da_catalogo_vacio(self):
        texto = json.dumps({"formato": 2, "paquetes": [_paquete()]})
        paquetes, descartes = paquetes_catalogo.leer(
            texto, VERSION_APP, {"voz"}, {"piper"})
        self.assertEqual(paquetes, [])
        self.assertEqual(
            descartes, ["el catálogo es de una versión más nueva de Guyrapu"])

    def test_rutas_invalidas_descartan_el_paquete(self):
        for mala in ("../fuera.bin", "/absoluta.bin", "C:/disco.bin",
                     "carpeta\\archivo.bin"):
            with self.subTest(ruta=mala):
                paquete = _paquete()
                paquete["archivos"][0]["ruta"] = mala
                paquetes, descartes = _leer(paquete)
                self.assertEqual(paquetes, [])
                self.assertEqual(len(descartes), 1)
                self.assertIn("ruta", descartes[0])

    def test_sha_corto_descarta(self):
        paquete = _paquete()
        paquete["archivos"][0]["sha256"] = "a" * 63
        paquetes, descartes = _leer(paquete)
        self.assertEqual(paquetes, [])
        self.assertIn("SHA-256", descartes[0])

    def test_url_http_descarta(self):
        paquete = _paquete()
        paquete["archivos"][0]["url"] = "http://ejemplo.com/a.onnx"
        paquetes, descartes = _leer(paquete)
        self.assertEqual(paquetes, [])
        self.assertIn("https", descartes[0])

    def test_id_repetido_invalida_los_dos(self):
        paquetes, descartes = paquetes_catalogo.leer(
            _catalogo(_paquete(), _paquete()), VERSION_APP,
            {"voz"}, {"piper"})
        self.assertEqual(paquetes, [])
        self.assertEqual(len(descartes), 2)
        self.assertTrue(all("repetido" in motivo for motivo in descartes))

    def test_tipo_o_proveedor_desconocido_no_aparece(self):
        casos = (("tipo", "otro"), ("proveedor", "otro"))
        for campo, valor in casos:
            with self.subTest(campo=campo):
                paquete = _paquete()
                paquete[campo] = valor
                paquetes, descartes = _leer(paquete)
                self.assertEqual(paquetes, [])
                self.assertIn(campo, descartes[0])

    def test_version_de_guyrapu_mas_nueva_lo_esconde(self):
        paquete = _paquete()
        paquete["guyrapu_minima"] = "9.0.0"
        paquetes, descartes = _leer(paquete)
        self.assertEqual(paquetes, [])
        self.assertIn("más nueva", descartes[0])


class TestEstado(unittest.TestCase):

    def test_sin_instalar(self):
        self.assertEqual(
            paquetes_catalogo.estado(_paquete(), None), "sin_descargar")

    def test_instalado(self):
        self.assertEqual(
            paquetes_catalogo.estado(_paquete(), {"version": 1}), "instalado")

    def test_actualizable(self):
        self.assertEqual(
            paquetes_catalogo.estado(_paquete(), {"version": 0}),
            "actualizable")

    def test_fuera_del_catalogo(self):
        self.assertEqual(
            paquetes_catalogo.estado(None, {"version": 1}),
            "fuera_del_catalogo")
