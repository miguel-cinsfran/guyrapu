# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas del proveedor de voz Phonon, con ptts reemplazado por un doble."""

import json
import shutil
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

from guyrapu.core import paths
from guyrapu.voice import motor_local
from guyrapu.voice.proveedores import phonon
from guyrapu.voice.proveedores.base import MotorNoDisponible

_ARCHIVOS_MODELO = ("config.json", "default-voice.safetensors",
                    "model.q8.gguf", "tokenizer.json")


def _ficha(base, identificador, idioma, voces, proveedor="phonon"):
    carpeta = base / identificador
    carpeta.mkdir(parents=True)
    for nombre in _ARCHIVOS_MODELO:
        (carpeta / nombre).write_bytes(b"modelo")
    lista = []
    for nombre in voces:
        archivo = f"{nombre}.safetensors"
        (carpeta / archivo).write_bytes(b"voz")
        lista.append({"nombre": nombre, "idioma": idioma, "genero": None,
                      "archivo": archivo})
    ficha = {
        "id": identificador,
        "tipo": "voz",
        "proveedor": proveedor,
        "idioma": idioma,
        "voces": lista,
        "archivos": [],
    }
    (carpeta / "paquete.json").write_text(
        json.dumps(ficha, ensure_ascii=False), encoding="utf-8")


class _TTSFalso:
    def __init__(self, model, lang, quant):
        self.model = str(model)
        self.lang = lang
        self.quant = quant
        self.sample_rate = 24000
        self.voices = ["default"]
        self.agregadas = []
        self.condiciones = {}
        self.frases = []

    def add_voice(self, nombre, ruta):
        self.agregadas.append((nombre, str(ruta)))
        self.voices.append(nombre)

    def set_conditions(self, condiciones):
        self.condiciones.update(condiciones)

    def stream(self, texto, voice=None):
        self.frases.append((texto, voice))
        return iter(([0.0],))


class _PttsFalso:
    def __init__(self):
        self.creados = []
        self.hilos = []
        self.TTS = self._crear

    def _crear(self, **datos):
        modelo = _TTSFalso(**datos)
        self.creados.append(modelo)
        return modelo

    def set_num_threads(self, numero):
        self.hilos.append(numero)


class _ReproductorFalso:
    def __init__(self):
        self.inicio = None
        self.primer_trozo = None
        self._terminado = threading.Event()
        self._sonando = False

    def empezar(self, tasa):
        self.inicio = time.perf_counter()

    def encolar(self, trozo):
        if self.primer_trozo is None:
            self.primer_trozo = time.perf_counter() - self.inicio
        self._sonando = True

    def terminar(self):
        self._sonando = False
        self._terminado.set()

    def cortar(self):
        self._sonando = False

    def pausar(self):
        return None

    def reanudar(self):
        return None

    def cerrar(self):
        self._sonando = False

    @property
    def sonando(self):
        return self._sonando

    def esperar_fin(self, plazo):
        return self._terminado.wait(plazo)

    def reiniciar(self):
        self.inicio = None
        self.primer_trozo = None
        self._terminado.clear()
        self._sonando = False


class BasePhonon(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.raiz = Path(self._tmp.name)
        self.base = self.raiz / "voces"
        self.base.mkdir()
        parche_raiz = mock.patch.object(
            paths, "carpeta_instalacion", return_value=self.raiz)
        parche_raiz.start()
        self.addCleanup(parche_raiz.stop)
        parche_voces = mock.patch.object(
            paths, "carpeta_voces", return_value=self.base)
        parche_voces.start()
        self.addCleanup(parche_voces.stop)
        parche_hilos = mock.patch.object(phonon, "_hilos_configurados", False)
        parche_hilos.start()
        self.addCleanup(parche_hilos.stop)


class TestVoces(BasePhonon):

    def test_sin_paquetes_no_hay_voces_y_no_se_puede_crear(self):
        self.assertEqual(phonon.listar_voces(), [])
        with self.assertRaises(MotorNoDisponible) as error:
            phonon.crear()
        self.assertIn("Phonon", str(error.exception))

    def test_lista_las_voces_de_los_dos_paquetes(self):
        _ficha(self.base, "a-es", "es-ES", ["Ana", "Luis"])
        _ficha(self.base, "b-pt", "pt-BR", ["Bia"])
        self.assertEqual(phonon.listar_voces(), ["Ana", "Luis", "Bia"])

    def test_un_nombre_repetido_sale_con_su_idioma(self):
        _ficha(self.base, "a-es", "es-ES", ["Ana"])
        _ficha(self.base, "b-pt", "pt-BR", ["Ana"])
        self.assertEqual(phonon.listar_voces(), ["Ana", "Ana (pt-BR)"])

    def test_un_paquete_de_otro_proveedor_no_aparece(self):
        _ficha(self.base, "a-es", "es-ES", ["Ana"])
        _ficha(self.base, "c-piper", "es-AR", ["Daniela"],
               proveedor="piper")
        self.assertEqual(phonon.listar_voces(), ["Ana"])


class TestSintetizador(BasePhonon):

    def setUp(self):
        super().setUp()
        _ficha(self.base, "a-es", "es-ES", ["Ana", "Luis"])
        _ficha(self.base, "b-pt", "pt-BR", ["Bia"])
        self.falso = _PttsFalso()
        self.sintetizador = phonon.SintetizadorPhonon(self.falso)

    def test_elegir_voz_carga_el_modelo_y_registra_sus_voces(self):
        self.assertTrue(self.sintetizador.elegir_voz(0))
        self.assertEqual(len(self.falso.creados), 1)
        modelo = self.falso.creados[0]
        self.assertEqual(modelo.model, str(self.base / "a-es"))
        self.assertEqual(modelo.lang, "es")
        self.assertEqual(modelo.quant, "q8_0")
        self.assertEqual([nombre for nombre, _ruta in modelo.agregadas],
                         ["Ana", "Luis"])
        self.assertEqual(modelo.agregadas[0][1],
                         str(self.base / "a-es" / "Ana.safetensors"))
        self.assertEqual(self.falso.hilos, [motor_local.HILOS_SINTESIS])
        self.assertEqual(self.sintetizador.tasa, 24000)

    def test_volver_a_un_paquete_no_lo_carga_de_nuevo(self):
        self.assertTrue(self.sintetizador.elegir_voz(0))
        self.assertTrue(self.sintetizador.elegir_voz(2))
        self.assertEqual([modelo.lang for modelo in self.falso.creados],
                         ["es", "pt"])
        self.assertTrue(self.sintetizador.elegir_voz(1))
        self.assertEqual(len(self.falso.creados), 2)

    def test_sintetizar_fija_la_condicion_y_usa_la_voz(self):
        self.assertTrue(self.sintetizador.elegir_voz(0))
        trozos = list(self.sintetizador.sintetizar("Hola", 1.0))
        self.assertEqual(len(trozos), 1)
        modelo = self.falso.creados[0]
        self.assertEqual(modelo.condiciones["duration_delta"],
                         phonon.delta_duracion(1.0))
        self.assertEqual(modelo.frases, [("Hola", "Ana")])

    def test_elegir_fuera_de_rango_no_carga_nada(self):
        self.assertFalse(self.sintetizador.elegir_voz(9))
        self.assertEqual(self.falso.creados, [])

    def test_crear_devuelve_un_motor_local_con_el_sintetizador(self):
        with mock.patch.object(phonon, "_ptts", return_value=self.falso), \
                mock.patch(
                    "guyrapu.voice.reproductor_pcm.ReproductorPCM",
                    _ReproductorFalso):
            motor = phonon.crear()
        try:
            self.assertIsInstance(motor, motor_local.MotorLocal)
            self.assertIsInstance(
                motor._sintetizador, phonon.SintetizadorPhonon)
        finally:
            motor.cerrar()


class TestDuracion(unittest.TestCase):

    def test_los_tres_puntos_medidos(self):
        for factor, esperado in ((0.864, 0.3), (1.0, 0.0), (1.288, -0.45)):
            with self.subTest(factor=factor):
                self.assertAlmostEqual(
                    phonon.delta_duracion(factor), esperado)

    def test_nunca_sube_al_subir_el_factor(self):
        valores = [phonon.delta_duracion(paso / 100)
                   for paso in range(60, 141)]
        for antes, despues in zip(valores, valores[1:]):
            self.assertLessEqual(despues, antes + 1e-12)

    def test_fuera_del_rango_se_acota(self):
        self.assertEqual(phonon.delta_duracion(0.5), 0.3)
        self.assertEqual(phonon.delta_duracion(2.0), -0.45)


class TestModeloReal(BasePhonon):
    """Frontera real con ptts y el modelo de la caché de Hugging Face."""

    CACHE = Path.home() / ".cache" / "huggingface" / "hub"
    MODELO = CACHE / "models--gradium--phonon-40m-es"
    VOCES = CACHE / "models--gradium--phonon-voices"

    def _snapshot(self):
        for carpeta in sorted((self.MODELO / "snapshots").iterdir()):
            if (carpeta / "model.q8.gguf").is_file():
                return carpeta
        return None

    def test_habla_con_el_modelo_instalado(self):
        if not self.MODELO.is_dir():
            self.skipTest("no está la caché de phonon-40m-es")
        try:
            import ptts  # noqa: F401
        except ImportError:
            self.skipTest("ptts no está instalado")
        snapshot = self._snapshot()
        if snapshot is None:
            self.skipTest("la caché de phonon-40m-es no trae el modelo")
        voces = sorted((self.VOCES / "snapshots").glob(
            "*/voices/*.safetensors"))[:2]
        if len(voces) < 2:
            self.skipTest("no están las dos voces de phonon-voices")
        carpeta = self.base / "phonon-40m-es"
        carpeta.mkdir(parents=True)
        for nombre in _ARCHIVOS_MODELO:
            shutil.copy2(snapshot / nombre, carpeta / nombre)
        lista = []
        for indice, origen in enumerate(voces):
            destino = carpeta / f"voz{indice}.safetensors"
            shutil.copy2(origen, destino)
            lista.append({"nombre": f"Voz {indice}", "idioma": "es-ES",
                          "genero": None, "archivo": destino.name})
        ficha = {
            "id": "phonon-40m-es",
            "tipo": "voz",
            "proveedor": "phonon",
            "idioma": "es-ES",
            "voces": lista,
            "archivos": [],
        }
        (carpeta / "paquete.json").write_text(
            json.dumps(ficha, ensure_ascii=False), encoding="utf-8")
        with mock.patch(
                "guyrapu.voice.reproductor_pcm.ReproductorPCM",
                _ReproductorFalso):
            motor = phonon.crear()
        try:
            reproductor = motor._reproductor
            inicio = time.perf_counter()
            self.assertTrue(motor.elegir_voz(0))
            carga = time.perf_counter() - inicio
            self.assertTrue(motor.hablar("Calentamiento."))
            self.assertTrue(reproductor.esperar_fin(20))
            reproductor.reiniciar()
            motor.fijar_volumen(0)
            self.assertTrue(motor.hablar("Hola, esto es una prueba."))
            self.assertTrue(reproductor.esperar_fin(20))
            limite = time.monotonic() + 5
            while motor.hablando() and time.monotonic() < limite:
                time.sleep(0.01)
            self.assertFalse(motor.hablando())
            primero = reproductor.primer_trozo
            print(f"Phonon real: carga {carga * 1000:.0f} ms, "
                  f"primer trozo {primero * 1000:.0f} ms")
            self.assertLess(primero, 0.3)
        finally:
            motor.cerrar()


if __name__ == "__main__":
    unittest.main()
