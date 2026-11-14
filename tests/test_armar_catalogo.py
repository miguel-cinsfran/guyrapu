# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de scripts/armar_catalogo.py, con respuestas de Hugging Face falsas."""

import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import armar_catalogo

TOKEN = "hf_secreto_que_no_debe_salir"


def _sha256(datos):
    return hashlib.sha256(datos).hexdigest()


def _descargar(datos):
    def falso(url, destino, token=None):
        destino = Path(destino)
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(datos)
    return falso


def _tarjeta(licencia):
    return ("# Model card\n\n## Dataset\n\n"
            f"* URL: https://ejemplo.com/datos\n* License: {licencia}\n")


class TestPrepararArchivo(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.raiz = Path(self._tmp.name)
        self.cache = self.raiz / ".cache-voces"
        self.subir = self.cache / "subir"

    def test_archivo_que_pide_cuenta_va_a_la_release_y_a_subir(self):
        with mock.patch.object(armar_catalogo, "pide_cuenta", return_value=True), \
             mock.patch.object(armar_catalogo, "token_huggingface",
                               return_value=TOKEN), \
             mock.patch.object(armar_catalogo, "descargar", _descargar(b"datos")):
            archivo = armar_catalogo.preparar_archivo(
                "gradium/phonon-40m-es", "rev", "model.q8.gguf",
                {"size": 5, "lfs": {"sha256": _sha256(b"datos")}},
                self.cache, self.subir, nombre="phonon-es-model.q8.gguf")
        self.assertEqual(
            archivo["url"],
            armar_catalogo.URL_SUBIR + "phonon-es-model.q8.gguf")
        self.assertEqual(archivo["sha256"], _sha256(b"datos"))
        self.assertEqual(archivo["bytes"], 5)
        self.assertTrue((self.subir / "phonon-es-model.q8.gguf").is_file())

    def test_archivo_libre_apunta_al_origen(self):
        with mock.patch.object(armar_catalogo, "pide_cuenta", return_value=False):
            archivo = armar_catalogo.preparar_archivo(
                "gradium/phonon-31m-en", "rev", "config.json",
                {"size": 7, "lfs": {"sha256": "b" * 64}},
                self.cache, self.subir)
        self.assertEqual(
            archivo["url"],
            "https://huggingface.co/gradium/phonon-31m-en/resolve/rev/config.json")
        self.assertFalse(self.subir.exists())

    def test_la_huella_lfs_viaja_en_oid(self):
        oid = "c" * 64
        with mock.patch.object(armar_catalogo, "pide_cuenta", return_value=False), \
             mock.patch.object(armar_catalogo, "descargar",
                               side_effect=AssertionError("no debe bajar")):
            archivo = armar_catalogo.preparar_archivo(
                "gradium/phonon-31m-en", "rev", "model.q8.gguf",
                {"size": 123, "lfs": {"oid": oid, "size": 123}},
                self.cache, self.subir)
        self.assertEqual(archivo["sha256"], oid)
        self.assertEqual(archivo["bytes"], 123)

    def test_codifica_las_rutas_con_acentos(self):
        self.assertEqual(
            armar_catalogo.url_origen(
                "rhasspy/piper-voices", "rev",
                "pt/pt_PT/tugão/medium/MODEL_CARD"),
            "https://huggingface.co/rhasspy/piper-voices/resolve/rev/"
            "pt/pt_PT/tug%C3%A3o/medium/MODEL_CARD")

    def test_el_token_no_aparece_en_la_salida(self):
        paquete = {
            "id": "phonon-es",
            "tipo": "voz",
            "proveedor": "phonon",
            "nombre": "Phonon español",
            "idioma": "es-ES",
            "version": 1,
            "guyrapu_minima": "2.5.0",
            "licencia": "CC BY-NC 4.0",
            "licencia_url": "https://huggingface.co/gradium/phonon-40m-es",
            "origen": "Gradium",
            "voces": [],
            "archivos": [],
        }
        salida = self.raiz / "salida"
        armar_catalogo.escribir_catalogo(salida, [{
            "paquete": paquete,
            "repo": "gradium/phonon-40m-es",
            "revision": "rev",
        }])
        for archivo in salida.iterdir():
            self.assertNotIn(TOKEN, archivo.read_text(encoding="utf-8"))
        self.assertIn("phonon-es",
                      (salida / "catalogo.json").read_text(encoding="utf-8"))


class TestAbrir(unittest.TestCase):

    def test_solo_manda_el_token_a_huggingface(self):
        casos = (
            ("https://github.com/miguel-cinsfran/guyrapu-contenido", None),
            ("https://rhasspy.github.io/piper-samples/x.mp3", None),
            ("https://huggingface.co.otro.com/modelo", None),
            ("https://huggingface.co/gradium/modelo", "Bearer " + TOKEN),
        )
        with mock.patch.object(armar_catalogo.urllib.request,
                               "urlopen") as abrir:
            for url, esperado in casos:
                with self.subTest(url=url):
                    abrir.reset_mock()
                    armar_catalogo._abrir(url, token=TOKEN)
                    peticion = abrir.call_args[0][0]
                    self.assertEqual(peticion.get_header("Authorization"),
                                     esperado)


class TestBasePiper(unittest.TestCase):

    def _base(self, cuerpo, aceptadas=()):
        return armar_catalogo.base_piper("## Training\n" + cuerpo + "\n",
                                         aceptadas)

    def test_acepta_las_bases_libres(self):
        for cuerpo in (
                "Trained from scratch on train-clean-360.",
                "Finetuned from the U.S. English hifi_tts_92 base model.",
                "Finetuned from the rdh base model (medium quality).",
                "See: https://brycebeattie.com/files/tts/"):
            with self.subTest(cuerpo=cuerpo):
                self.assertIsNone(self._base(cuerpo))
        self.assertIsNone(self._base(
            "Finetuned from Spanish davefx voice (medium quality).",
            {"davefx"}))
        self.assertEqual(self._base("Finetuned from otra voz voice."),
                         "base desconocida")

    def test_deja_fuera_lessac_y_ryan(self):
        casos = (
            ("Finetuned from U.S. English lessac voice (medium quality).",
             "base no libre: lessac"),
            ("Fine-tuned from English lessac medium on train-clean-360.",
             "base no libre: lessac"),
            ("Finetuned from U.S. English Ryan voice (low quality).",
             "base no libre: ryan"),
        )
        for cuerpo, motivo in casos:
            with self.subTest(cuerpo=cuerpo):
                self.assertEqual(self._base(cuerpo), motivo)

    def test_base_desconocida(self):
        self.assertEqual(self._base("See URL above"), "base desconocida")
        self.assertEqual(armar_catalogo.base_piper("sin seccion"),
                         "base desconocida")
        self.assertEqual(armar_catalogo.base_piper(None), "base desconocida")

    def test_el_nombre_de_jenny_es_el_pedido(self):
        self.assertEqual(armar_catalogo.nombre_piper("jenny_dioco"),
                         "Jenny (Dioco)")
        self.assertEqual(armar_catalogo.nombre_piper("davefx"), "Davefx")


class TestLicenciaPiper(unittest.TestCase):

    def test_acepta_las_que_se_pueden_repartir(self):
        for licencia in ("public domain", "CC0", "CC BY 4.0",
                         "CC-BY-SA 4.0 International",
                         "Attribution-ShareAlike 4.0 International",
                         "https://creativecommons.org/licenses/by/4.0/",
                         "http://creativecommons.org/licenses/by/3.0/",
                         "https://creativecommons.org/publicdomain/zero/1.0/",
                         "Apache 2.0", "Unlicense"):
            with self.subTest(licencia=licencia):
                self.assertIsNotNone(
                    armar_catalogo.licencia_piper("daniela", _tarjeta(licencia)))

    def test_jenny_dioco_entra_aunque_diga_see_url(self):
        self.assertEqual(
            armar_catalogo.licencia_piper("jenny_dioco", _tarjeta("See URL")),
            "See URL")

    def test_deja_fuera_nc_see_url_y_lessac(self):
        for licencia in ("CC BY-NC 4.0", "CC BY-NC-SA 4.0",
                         "https://creativecommons.org/licenses/by-nc/4.0/",
                         "http://creativecommons.org/licenses/by-nc-sa/4.0/",
                         "See URL", "See LICENSE file"):
            with self.subTest(licencia=licencia):
                self.assertIsNone(
                    armar_catalogo.licencia_piper("voz", _tarjeta(licencia)))
        self.assertIsNone(
            armar_catalogo.licencia_piper("lessac", _tarjeta("public domain")))
