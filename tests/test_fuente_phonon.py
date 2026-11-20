# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de scripts/fuente_phonon.py, con respuestas de Hugging Face falsas."""

import unittest
from unittest import mock

from guyrapu.core import paquetes_catalogo
from guyrapu.core.config import APP_VERSION
from scripts import armar_catalogo
from scripts import fuente_phonon


class TestMuestras(unittest.TestCase):

    def test_la_muestra_es_el_clip_mas_largo(self):
        arbol = {
            f"audios/voz_noa/{nombre}.ogg": {"size": tamano}
            for nombre, tamano in (
                ("exclamation_02", 14586),
                ("happy_01", 17958),
                ("question_01", 18774),
                ("support_01", 16737),
                ("support_04", 26207),
            )
        }
        self.assertEqual(fuente_phonon._muestras(arbol),
                          {"noa": "audios/voz_noa/support_04.ogg"})

    def test_a_igual_tamano_gana_el_primer_nombre(self):
        arbol = {
            f"audios/voz_noa/{nombre}.ogg": {"size": 100}
            for nombre in ("support_04", "exclamation_02")
        }
        self.assertEqual(fuente_phonon._muestras(arbol),
                          {"noa": "audios/voz_noa/exclamation_02.ogg"})


class TestPaquetesArmados(unittest.TestCase):

    def _phonon(self):
        archivo = {"url": "https://ejemplo.com/phonon.onnx", "bytes": 1,
                   "sha256": "b" * 64, "ruta": "phonon.onnx"}
        metadatos = {ruta: {} for ruta in fuente_phonon.ARCHIVOS_MODELO}
        with mock.patch.object(armar_catalogo, "preparar_archivo",
                               return_value=archivo):
            return fuente_phonon._paquete_phonon(
                "es", fuente_phonon.PHONON["es"], [], metadatos, {}, {})

    def test_los_paquetes_de_phonon_conservan_su_enlace(self):
        paquete = self._phonon()
        self.assertEqual(paquete["licencia_url"],
                         "https://huggingface.co/gradium/phonon-40m-es")

    def test_cada_licencia_url_pasa_la_validacion_del_catalogo(self):
        paquete = self._phonon()
        validos, descartes = paquetes_catalogo.leer(
            {"formato": 1, "paquetes": [paquete]}, APP_VERSION,
            {"voz"}, {"piper", "phonon"})
        self.assertEqual(descartes, [])
        self.assertEqual(validos, [paquete])
