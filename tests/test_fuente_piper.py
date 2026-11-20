# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de scripts/fuente_piper.py, con respuestas de Hugging Face falsas."""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from guyrapu.core import paquetes_catalogo
from guyrapu.core.config import APP_VERSION
from scripts import armar_catalogo
from scripts import fuente_piper


def _tarjeta(licencia):
    return ("# Model card\n\n## Dataset\n\n"
            f"* URL: https://ejemplo.com/datos\n* License: {licencia}\n")


class TestNombrePiper(unittest.TestCase):

    def test_el_nombre_de_jenny_es_el_pedido(self):
        self.assertEqual(fuente_piper.nombre_piper("jenny_dioco"),
                         "Jenny (Dioco)")
        self.assertEqual(fuente_piper.nombre_piper("davefx"), "Davefx")


class TestPaquetesArmados(unittest.TestCase):

    def _piper(self, nombre, licencia,
               tarjeta="es/es_ES/voz/medium/MODEL_CARD",
               entrenamiento="Trained from scratch on train-clean-360.",
               hablantes=None):
        entrada = {
            "language": {"family": "es", "code": "es_ES"},
            "name": nombre,
            "quality": "medium",
            "key": "es/es_ES/voz/medium",
            "files": {tarjeta: {}, "voz.onnx": {}, "voz.onnx.json": {}},
        }
        if hablantes is not None:
            entrada["speaker_id_map"] = hablantes
        archivo = {"url": "https://ejemplo.com/voz.onnx", "bytes": 1,
                   "sha256": "a" * 64, "ruta": "voz.onnx"}
        texto = _tarjeta(licencia) + f"\n## Training\n\n{entrenamiento}\n"
        with mock.patch.object(armar_catalogo, "pedir_texto",
                               return_value=texto), \
             mock.patch.object(armar_catalogo, "preparar_archivo",
                               return_value=archivo):
            return fuente_piper._paquete_piper(
                ("es_ES", nombre), entrada,
                {"voz.onnx": {}, "voz.onnx.json": {}},
                "rhasspy/piper-voices", "rev")

    def test_una_voz_de_piper_enlaza_su_model_card(self):
        paquete = self._piper("daniela", "CC BY 4.0",
                              "es/es_ES/daniela/medium/MODEL_CARD")
        self.assertEqual(
            paquete["licencia_url"],
            "https://huggingface.co/rhasspy/piper-voices/blob/rev/"
            "es/es_ES/daniela/medium/MODEL_CARD")

    def test_jenny_lleva_su_licencia_y_su_enlace(self):
        paquete = self._piper("jenny_dioco", "See URL")
        self.assertEqual(
            paquete["licencia"],
            "Licencia propia de Dioco: uso comercial permitido, "
            "citando la voz como Jenny (Dioco)")
        self.assertEqual(paquete["licencia_url"],
                         "https://github.com/dioco-group/jenny-tts-dataset")

    def test_cada_licencia_url_pasa_la_validacion_del_catalogo(self):
        paquetes = (self._piper("daniela", "CC BY 4.0"),
                    self._piper("jenny_dioco", "See URL"))
        for paquete in paquetes:
            with self.subTest(paquete=paquete["id"]):
                validos, descartes = paquetes_catalogo.leer(
                    {"formato": 1, "paquetes": [paquete]}, APP_VERSION,
                    {"voz"}, {"piper", "phonon"})
                self.assertEqual(descartes, [])
                self.assertEqual(validos, [paquete])

    def test_todas_las_voces_entran_aunque_tengan_restricciones(self):
        casos = (
            ("daniela", "Attribution-ShareAlike 4.0 International",
             "Finetuned from U.S. English lessac voice (high quality)."),
            ("mls_10246", "CC BY 4.0",
             "Finetuned from U.S. English Ryan voice (low quality)."),
            ("claude", "apache-2.0", "See URL above"),
            ("amy", "See URL", "Trained from scratch on train-clean-360."),
        )
        for nombre, licencia, entrenamiento in casos:
            with self.subTest(voz=nombre):
                self.assertIsNotNone(self._piper(
                    nombre, licencia, entrenamiento=entrenamiento))

    def test_la_restriccion_lleva_uso_y_version_minima(self):
        paquete = self._piper(
            "daniela", "Attribution-ShareAlike 4.0 International",
            entrenamiento="Finetuned from U.S. English lessac voice (high quality).")
        self.assertEqual(paquete["uso"], "investigacion")
        self.assertEqual(paquete["guyrapu_minima"], "3.0.0-beta.6")
        libre = self._piper("davefx", "CC BY 4.0")
        self.assertEqual(libre["uso"], "libre")
        self.assertEqual(libre["guyrapu_minima"], APP_VERSION)

    def test_un_modelo_con_varios_hablantes_da_una_voz_por_hablante(self):
        casos = (
            ({"M": 0, "F": 1},
             [("Sharvard", "male", 0), ("Sharvard", "female", 1)]),
            ({"Prudence": 2, "Lucie": 0},
             [("Semaine Lucie", None, 0), ("Semaine Prudence", None, 2)]),
            ({f"V{n}": n for n in range(26)},
             [("Semaine", None, None)]),
        )
        for hablantes, esperado in casos:
            with self.subTest(hablantes=len(hablantes)):
                nombre = "sharvard" if hablantes.get("M") == 0 else "semaine"
                paquete = self._piper(nombre, "CC BY 4.0",
                                      hablantes=hablantes)
                self.assertEqual(
                    [(voz["nombre"], voz["genero"], voz.get("hablante"))
                     for voz in paquete["voces"]], esperado)

    def test_licencias_incluye_el_uso(self):
        paquete = self._piper(
            "mls_10246", "CC BY 4.0",
            entrenamiento="Finetuned from U.S. English Ryan voice (low quality).")
        with tempfile.TemporaryDirectory() as temporal:
            salida = Path(temporal) / "salida"
            armar_catalogo.escribir_catalogo(salida, [{
                "paquete": paquete, "repo": "rhasspy/piper-voices",
                "revision": "rev"}])
            texto = (salida / "LICENCIAS.txt").read_text(encoding="utf-8")
        self.assertIn("Uso: no_comercial", texto)
