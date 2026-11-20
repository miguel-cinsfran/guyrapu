# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Cola de frases y audio en memoria de Prism con voces reales, sin red."""

import time
import unittest

from guyrapu.voice.proveedores.base import MotorNoDisponible
from guyrapu.voice.proveedores.prism import MotorPrism

FRASE_UNO = "Primera frase de prueba, uno, dos, tres, cuatro, cinco."
FRASE_DOS = "Segunda frase de prueba, seis, siete, ocho, nueve, diez."
PLAZO_HABLA = 8.0
PLAZO_PARADA = 1.0
MARGEN_COLA = 1.5
UMBRAL_VOZ = 0.5


def _esperar(motor, estado, plazo):
    """Espera a que `hablando()` valga `estado` y dice si lo logró."""
    limite = time.monotonic() + plazo
    while motor.hablando() != estado and time.monotonic() < limite:
        time.sleep(0.01)
    return motor.hablando() == estado


class _VocesReales(unittest.TestCase):

    def _preparar(self, id_motor):
        try:
            motor = MotorPrism(id_motor)
        except MotorNoDisponible as exc:
            self.skipTest(f"El motor {id_motor} no está disponible: {exc}")
        self.addCleanup(motor.cerrar)
        motor.fijar_volumen(0)
        try:
            self._elegir_voz(motor)
        except AssertionError as exc:
            self.skipTest(f"Sin voces {id_motor} con habla sostenida: {exc}")
        return motor

    def _elegir_voz(self, motor):
        # SAPI2SR enciende `speaking` un instante sin producir audio: hace falta
        # una voz que siga hablando para medir la cola y el audio en memoria.
        probadas = []
        for indice, nombre in enumerate(motor.voces() or ["la que trae"]):
            if not motor.elegir_voz(indice):
                continue
            probadas.append(nombre)
            motor.parar()
            if not motor.hablar(FRASE_UNO) or not _esperar(
                    motor, True, PLAZO_HABLA):
                continue
            inicio = time.monotonic()
            while motor.hablando() and time.monotonic() - inicio < UMBRAL_VOZ:
                time.sleep(0.01)
            if motor.hablando():
                motor.parar()
                _esperar(motor, False, PLAZO_PARADA)
                return
            motor.parar()
        raise AssertionError(", ".join(probadas) or "sin voces elegibles")

    def _duracion(self, motor, frase):
        if not motor.hablar(frase) or not _esperar(motor, True, PLAZO_HABLA):
            self.fail(f"El motor {motor.motor} no empezó a hablar")
        inicio = time.monotonic()
        if not _esperar(motor, False, PLAZO_HABLA):
            self.fail(f"El motor {motor.motor} no dejó de hablar")
        return time.monotonic() - inicio

    def _tiempo_dos_frases(self, motor):
        if not motor.hablar(FRASE_UNO) or not _esperar(motor, True, PLAZO_HABLA):
            self.fail(f"El motor {motor.motor} no empezó a hablar")
        inicio = time.monotonic()
        self.assertTrue(motor.hablar(FRASE_DOS))
        self.assertTrue(motor.hablando(), "La segunda frase cortó a la primera")
        if not _esperar(motor, False, PLAZO_HABLA * 2):
            self.fail(f"El motor {motor.motor} no dejó de hablar tras dos frases")
        return time.monotonic() - inicio

    def _parar(self, motor, duracion):
        self.assertTrue(motor.hablar(FRASE_UNO))
        self.assertTrue(_esperar(motor, True, PLAZO_HABLA))
        self.assertTrue(motor.hablar(FRASE_DOS))
        time.sleep(0.2)
        motor.parar()
        self.assertTrue(_esperar(motor, False, PLAZO_PARADA),
                        "parar() no cortó la frase que sonaba")
        time.sleep(duracion + 1.0)
        self.assertFalse(motor.hablando(),
                         "parar() no descartó la frase que esperaba")

    def _en_memoria(self, motor):
        muestras = []

        def capturar(pcm, canales, tasa):
            muestras.extend(pcm)

        motor._backend.speak_to_memory(FRASE_UNO, capturar)
        return muestras


class TestColaPrismReal(_VocesReales):

    def test_onecore_dos_frases_y_parada(self):
        motor = self._preparar("onecore")
        dos = self._tiempo_dos_frases(motor)
        una = self._duracion(motor, FRASE_UNO)
        self.assertGreaterEqual(dos, una * MARGEN_COLA,
                                "No sonaron las dos frases seguidas")
        self._parar(motor, una)

    def test_sapi_dos_frases_y_parada(self):
        motor = self._preparar("sapi")
        dos = self._tiempo_dos_frases(motor)
        una = self._duracion(motor, FRASE_UNO)
        self.assertGreaterEqual(dos, una * MARGEN_COLA,
                                "No sonaron las dos frases seguidas")
        self._parar(motor, una)


class TestPrismMemoriaReal(_VocesReales):

    def test_onecore_speak_to_memory(self):
        motor = self._preparar("onecore")
        self.assertTrue(self._en_memoria(motor),
                        "speak_to_memory no devolvió audio en OneCore")

    def test_sapi_speak_to_memory(self):
        motor = self._preparar("sapi")
        self.assertTrue(self._en_memoria(motor),
                        "speak_to_memory no devolvió audio en SAPI")


if __name__ == "__main__":
    unittest.main()
