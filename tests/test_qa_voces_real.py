# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de la lógica pura de qa/voces_real.py, sin red ni ventanas."""

import importlib.util
import unittest
from pathlib import Path

_RUTA = Path(__file__).resolve().parent.parent / "qa" / "voces_real.py"
_paquete = importlib.util.spec_from_file_location("voces_real_qa", _RUTA)
voces_real = importlib.util.module_from_spec(_paquete)
_paquete.loader.exec_module(voces_real)


def _paquete(identificador, tipo="voz", proveedor="piper", bytes_totales=100,
             version_minima="1.0.0"):
    return {
        "id": identificador,
        "tipo": tipo,
        "proveedor": proveedor,
        "nombre": f"Voz {identificador}",
        "idioma": "es-AR",
        "version": 1,
        "guyrapu_minima": version_minima,
        "licencia": "CC0",
        "licencia_url": "https://ejemplo.com/licencia",
        "origen": "prueba",
        "voces": [],
        "archivos": [{
            "url": "https://ejemplo.com/voz.onnx",
            "bytes": bytes_totales,
            "sha256": "a" * 64,
            "ruta": "voz.onnx",
        }],
    }


class TestSeleccionar(unittest.TestCase):

    def test_elige_el_mas_chico_entre_los_compatibles(self):
        catalogo = {"formato": 1, "paquetes": [
            _paquete("voz-grande", bytes_totales=300),
            _paquete("voz-chica", bytes_totales=120),
            _paquete("voz-media", bytes_totales=200),
        ]}
        paquete, descartes = voces_real.seleccionar(
            catalogo, "3.0.0", {"voz"}, ("piper",))
        self.assertEqual(paquete["id"], "voz-chica")
        self.assertEqual(descartes, [])

    def test_ignora_los_paquetes_no_compatibles(self):
        catalogo = {"formato": 1, "paquetes": [
            _paquete("musica-chica", tipo="musica", bytes_totales=1),
            _paquete("voz-desconocida", proveedor="otro", bytes_totales=2),
            _paquete("voz-nueva", version_minima="99.0.0", bytes_totales=3),
            _paquete("voz-chica", bytes_totales=120),
        ]}
        paquete, descartes = voces_real.seleccionar(
            catalogo, "3.0.0", {"voz"}, ("piper",))
        self.assertEqual(paquete["id"], "voz-chica")
        self.assertEqual(len(descartes), 3)

    def test_sin_compatibles_devuelve_none_y_los_motivos(self):
        catalogo = {"formato": 1, "paquetes": [
            _paquete("musica-chica", tipo="musica"),
        ]}
        paquete, descartes = voces_real.seleccionar(
            catalogo, "3.0.0", {"voz"}, ("piper",))
        self.assertIsNone(paquete)
        self.assertTrue(descartes)


class TestTieneAudio(unittest.TestCase):

    def test_todo_cero_no_tiene_audio(self):
        self.assertFalse(voces_real.tiene_audio([]))
        self.assertFalse(voces_real.tiene_audio([[0.0, 0.0], [0.0]]))

    def test_una_muestra_distinta_de_cero_tiene_audio(self):
        self.assertTrue(voces_real.tiene_audio([[0.0, 0.0], [0.0, 0.25]]))


class TestLineaFinal(unittest.TestCase):

    def test_todo_bien_da_codigo_cero(self):
        self.assertEqual(voces_real.linea_final(None, ""),
                         ("VOCES_REAL codigo=0", 0))

    def test_cada_paso_fallido_da_codigo_y_motivo(self):
        for paso in ("catalogo", "paquete", "instalar", "voz"):
            with self.subTest(paso=paso):
                linea, codigo = voces_real.linea_final(paso, "motivo de prueba")
                self.assertEqual(codigo, 1)
                self.assertEqual(linea, f"VOCES_REAL {paso}: motivo de prueba")


if __name__ == "__main__":
    unittest.main()
