# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de scripts/armar_catalogo.py, con respuestas de Hugging Face falsas."""

import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from guyrapu.core import paquetes_catalogo
from guyrapu.core.config import APP_VERSION
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
        self.assertEqual(armar_catalogo._muestras(arbol),
                         {"noa": "audios/voz_noa/support_04.ogg"})

    def test_a_igual_tamano_gana_el_primer_nombre(self):
        arbol = {
            f"audios/voz_noa/{nombre}.ogg": {"size": 100}
            for nombre in ("support_04", "exclamation_02")
        }
        self.assertEqual(armar_catalogo._muestras(arbol),
                         {"noa": "audios/voz_noa/exclamation_02.ogg"})


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


class TestNombrePiper(unittest.TestCase):

    def test_el_nombre_de_jenny_es_el_pedido(self):
        self.assertEqual(armar_catalogo.nombre_piper("jenny_dioco"),
                         "Jenny (Dioco)")
        self.assertEqual(armar_catalogo.nombre_piper("davefx"), "Davefx")


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
            return armar_catalogo._paquete_piper(
                ("es_ES", nombre), entrada,
                {"voz.onnx": {}, "voz.onnx.json": {}},
                "rhasspy/piper-voices", "rev")

    def _phonon(self):
        archivo = {"url": "https://ejemplo.com/phonon.onnx", "bytes": 1,
                   "sha256": "b" * 64, "ruta": "phonon.onnx"}
        metadatos = {ruta: {} for ruta in armar_catalogo.ARCHIVOS_MODELO}
        with mock.patch.object(armar_catalogo, "preparar_archivo",
                               return_value=archivo):
            return armar_catalogo._paquete_phonon(
                "es", armar_catalogo.PHONON["es"], [], metadatos, {}, {})

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

    def test_los_paquetes_de_phonon_conservan_su_enlace(self):
        paquete = self._phonon()
        self.assertEqual(paquete["licencia_url"],
                         "https://huggingface.co/gradium/phonon-40m-es")

    def test_cada_licencia_url_pasa_la_validacion_del_catalogo(self):
        paquetes = (self._piper("daniela", "CC BY 4.0"),
                    self._piper("jenny_dioco", "See URL"),
                    self._phonon())
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
