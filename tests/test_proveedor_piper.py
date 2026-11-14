# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas del proveedor de voz de Piper con fichas y biblioteca falsas."""

import gc
import json
import os
import shutil
import tempfile
import time
import types
import unittest
import weakref
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import numpy as np

from guyrapu.core import paths
from guyrapu.voice import motor_local
from guyrapu.voice import reproductor_pcm
from guyrapu.voice.proveedores import piper as proveedor_piper
from guyrapu.voice.proveedores.base import MotorNoDisponible


class _ReproductorFalso:
    def empezar(self, tasa):
        pass

    def encolar(self, trozo):
        pass

    def terminar(self):
        pass

    def cortar(self):
        pass

    def pausar(self):
        pass

    def reanudar(self):
        pass

    def cerrar(self):
        pass


def _modulo_piper():
    estado = {"cargadas": [], "voces": []}

    class SynthesisConfig:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class Voz:
        def __init__(self):
            self.config = SimpleNamespace(sample_rate=16000)
            self.configuraciones = []

        def synthesize(self, texto, configuracion):
            self.configuraciones.append(configuracion)
            yield np.array([16384, -16384], dtype=np.int16)

    class PiperVoice:
        @staticmethod
        def load(modelo):
            estado["cargadas"].append(str(modelo))
            voz = Voz()
            estado["voces"].append(voz)
            return voz

    modulo = types.ModuleType("piper")
    modulo.PiperVoice = PiperVoice
    modulo.SynthesisConfig = SynthesisConfig
    return modulo, estado


def _ficha(identificador, nombre, idioma="es-AR", proveedor="piper"):
    return {
        "id": identificador,
        "tipo": "voz",
        "proveedor": proveedor,
        "nombre": f"Piper {nombre}",
        "idioma": idioma,
        "version": 1,
        "guyrapu_minima": "0.0.0",
        "licencia": "CC0",
        "licencia_url": "https://ejemplo.com/licencia",
        "origen": "prueba",
        "voces": [{
            "nombre": nombre,
            "idioma": idioma,
            "genero": None,
            "muestra": None,
            "archivo": f"{identificador}.onnx",
        }],
        "archivos": [
            {"url": "https://ejemplo.com/a", "bytes": 0, "sha256": "0" * 64,
             "ruta": f"{identificador}.onnx"},
            {"url": "https://ejemplo.com/b", "bytes": 0, "sha256": "0" * 64,
             "ruta": f"{identificador}.onnx.json"},
        ],
    }


class TestProveedorPiper(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.raiz = Path(self._tmp.name)
        parche = mock.patch.object(
            paths, "carpeta_instalacion", return_value=self.raiz)
        parche.start()
        self.addCleanup(parche.stop)

    def _instalar(self, *fichas):
        base = self.raiz / "voces"
        for ficha in fichas:
            carpeta = base / ficha["id"]
            carpeta.mkdir(parents=True)
            (carpeta / "paquete.json").write_text(
                json.dumps(ficha), encoding="utf-8")
            for archivo in ficha["archivos"]:
                (carpeta / archivo["ruta"]).write_bytes(b"")

    def _crear(self, modulo):
        with mock.patch.dict("sys.modules", {"piper": modulo}), \
             mock.patch.object(reproductor_pcm, "ReproductorPCM",
                               _ReproductorFalso):
            return proveedor_piper.crear()

    def test_sin_paquetes_lista_vacia_y_crear_no_esta_disponible(self):
        self._instalar()
        self.assertEqual(proveedor_piper.listar_voces(), [])
        with self.assertRaises(MotorNoDisponible) as error:
            proveedor_piper.crear()
        self.assertIn("Piper", str(error.exception))

    def test_lista_las_voces_de_los_paquetes_instalados(self):
        self._instalar(_ficha("a-daniela", "Daniela"),
                       _ficha("b-jorge", "Jorge"))
        self.assertEqual(proveedor_piper.listar_voces(),
                         ["Daniela, español (Argentina)",
                          "Jorge, español (Argentina)"])

    def test_un_nombre_repetido_sale_con_su_idioma(self):
        self._instalar(_ficha("a-daniela", "Daniela", "es-AR"),
                       _ficha("b-daniela", "Daniela", "es-ES"))
        self.assertEqual(proveedor_piper.listar_voces(),
                         ["Daniela, español (Argentina)",
                          "Daniela, español (España)"])

    def test_dos_voces_con_el_mismo_texto_llevan_numero(self):
        self._instalar(_ficha("a-daniela", "Daniela", "es-AR"),
                       _ficha("b-daniela", "Daniela", "es-AR"))
        self.assertEqual(proveedor_piper.listar_voces(),
                         ["Daniela, español (Argentina)",
                          "Daniela, español (Argentina), 2"])

    def test_la_voz_usa_su_propio_idioma(self):
        ficha = _ficha("a-daniela", "Daniela", "es-AR")
        ficha["voces"][0]["idioma"] = "es-ES"
        self._instalar(ficha)
        self.assertEqual(proveedor_piper.listar_voces(),
                         ["Daniela, español (España)"])

    def test_la_voz_sin_idioma_usa_el_del_paquete(self):
        ficha = _ficha("a-daniela", "Daniela", "es-AR")
        del ficha["voces"][0]["idioma"]
        self._instalar(ficha)
        self.assertEqual(proveedor_piper.listar_voces(),
                         ["Daniela, español (Argentina)"])

    def test_un_paquete_de_otro_proveedor_no_aparece(self):
        self._instalar(_ficha("a-daniela", "Daniela"),
                       _ficha("b-otra", "Otra", proveedor="phonon"))
        self.assertEqual(proveedor_piper.listar_voces(),
                         ["Daniela, español (Argentina)"])

    def test_crear_devuelve_un_motor_local_con_el_sintetizador(self):
        self._instalar(_ficha("a-daniela", "Daniela"))
        modulo, _estado = _modulo_piper()
        motor = self._crear(modulo)
        try:
            self.assertIsInstance(motor, motor_local.MotorLocal)
            self.assertIsInstance(motor._sintetizador,
                                  proveedor_piper.SintetizadorPiper)
        finally:
            motor.cerrar()

    def test_elegir_la_segunda_carga_su_onnx_y_suelta_la_primera(self):
        self._instalar(_ficha("a-daniela", "Daniela"),
                       _ficha("b-jorge", "Jorge"))
        modulo, estado = _modulo_piper()
        motor = self._crear(modulo)
        try:
            sintetizador = motor._sintetizador
            self.assertTrue(sintetizador.elegir_voz(0))
            primera = estado["voces"][0]
            referencia = weakref.ref(primera)
            self.assertTrue(sintetizador.elegir_voz(1))
            self.assertEqual(
                [Path(cargada) for cargada in estado["cargadas"]],
                [self.raiz / "voces" / "a-daniela" / "a-daniela.onnx",
                 self.raiz / "voces" / "b-jorge" / "b-jorge.onnx"])
            estado["voces"].clear()
            del primera
            gc.collect()
            self.assertIsNone(referencia())
        finally:
            motor.cerrar()

    def test_sintetizar_pasa_la_velocidad_y_entrega_float32(self):
        self._instalar(_ficha("a-daniela", "Daniela"))
        modulo, estado = _modulo_piper()
        motor = self._crear(modulo)
        try:
            sintetizador = motor._sintetizador
            self.assertTrue(sintetizador.elegir_voz(0))
            voz = estado["voces"][0]
            self.assertEqual(sintetizador.rango_velocidad, (0.5, 2.0))

            trozos = list(sintetizador.sintetizar("hola", 2.0))
            self.assertEqual(voz.configuraciones[-1].kwargs,
                             {"length_scale": 0.5})
            self.assertTrue(all(trozo.dtype == np.float32
                                for trozo in trozos))

            list(sintetizador.sintetizar("hola", 0.5))
            self.assertEqual(voz.configuraciones[-1].kwargs,
                             {"length_scale": 2.0})
        finally:
            motor.cerrar()

    def test_cerrar_suelta_la_voz(self):
        self._instalar(_ficha("a-daniela", "Daniela"))
        modulo, estado = _modulo_piper()
        sintetizador = proveedor_piper.SintetizadorPiper(
            proveedor_piper._entradas(), (modulo.PiperVoice,
                                          modulo.SynthesisConfig))
        self.assertTrue(sintetizador.elegir_voz(0))
        referencia = weakref.ref(estado["voces"][0])
        estado["voces"].clear()
        sintetizador.cerrar()
        gc.collect()
        self.assertIsNone(referencia())


_RUTA_MODELO = (Path(os.environ.get("LOCALAPPDATA", "")) / "hermes" / "models"
                / "piper" / "es_AR-daniela-high.onnx")
_HAY_MODELO = (_RUTA_MODELO.is_file()
               and Path(f"{_RUTA_MODELO}.json").is_file())


def _armar_paquete_real(raiz):
    carpeta = raiz / "voces" / "piper-es-ar-daniela-high"
    carpeta.mkdir(parents=True)
    modelo = carpeta / _RUTA_MODELO.name
    configuracion = carpeta / f"{_RUTA_MODELO.name}.json"
    for origen, destino in ((_RUTA_MODELO, modelo),
                            (Path(f"{_RUTA_MODELO}.json"), configuracion)):
        try:
            os.link(origen, destino)
        except OSError:
            shutil.copy2(origen, destino)
    ficha = _ficha("piper-es-ar-daniela-high", "Daniela", "es-AR")
    ficha["archivos"] = [
        {"url": "https://ejemplo.com/a", "bytes": 0, "sha256": "0" * 64,
         "ruta": modelo.name},
        {"url": "https://ejemplo.com/b", "bytes": 0, "sha256": "0" * 64,
         "ruta": configuracion.name},
    ]
    (carpeta / "paquete.json").write_text(
        json.dumps(ficha), encoding="utf-8")


@unittest.skipUnless(_HAY_MODELO, "no hay un modelo de Piper local")
class TestPiperReal(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.raiz = Path(self._tmp.name)
        parche = mock.patch.object(
            paths, "carpeta_instalacion", return_value=self.raiz)
        parche.start()
        self.addCleanup(parche.stop)
        self._armar_paquete()

    def _armar_paquete(self):
        _armar_paquete_real(self.raiz)

    def test_habla_una_voz_real_sin_red(self):
        motor = proveedor_piper.crear()
        try:
            inicio_carga = time.monotonic()
            self.assertTrue(motor.elegir_voz(0))
            carga = time.monotonic() - inicio_carga
            motor.fijar_volumen(0)

            original = motor._reproductor.encolar
            instante = {}

            def encolar(trozo):
                instante.setdefault("primero", time.monotonic())
                original(trozo)

            motor._reproductor.encolar = encolar
            texto = ("Esta es una prueba de voz local de Piper que se lee "
                     "sin red y con volumen cero para medir cuánto tarda "
                     "en llegar el primer trozo al reproductor de audio.")[:150]
            inicio = time.monotonic()
            self.assertTrue(motor.hablar(texto))
            self.assertTrue(motor.hablando())
            limite = time.monotonic() + 20.0
            while motor.hablando() and time.monotonic() < limite:
                time.sleep(0.02)
            self.assertFalse(motor.hablando())
            primero = instante.get("primero")
            self.assertIsNotNone(primero)
            print(f"\nPiper real: carga {carga:.3f} s, primer trozo "
                  f"{primero - inicio:.3f} s")
        finally:
            motor.cerrar()


if __name__ == "__main__":
    unittest.main()
