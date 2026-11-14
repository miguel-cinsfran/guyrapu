# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas reales del reproductor PCM, saltadas si no hay salida de audio."""

import time
import unittest

import numpy as np

from guyrapu.voice import motor_local
from guyrapu.voice import reproductor_pcm

TASA = 48000
TROZO = int(TASA * 0.02)
HAY_AUDIO = bool(reproductor_pcm.listar_salidas())


def _esperar(condicion, plazo=3.0):
    limite = time.monotonic() + plazo
    while time.monotonic() < limite:
        if condicion():
            return True
        time.sleep(0.005)
    return condicion()


def _esperar_hasta(condicion, plazo):
    """Segundos hasta que la condición se cumple, o None si no llega."""
    inicio = time.perf_counter()
    while time.perf_counter() - inicio < plazo:
        if condicion():
            return time.perf_counter() - inicio
        time.sleep(0.005)
    return None


@unittest.skipUnless(HAY_AUDIO, "sin salida de audio")
class TestReproductorPCM(unittest.TestCase):

    def setUp(self):
        self.reproductor = reproductor_pcm.ReproductorPCM()
        self.reproductor.empezar(TASA)

    def tearDown(self):
        self.reproductor.cerrar()

    def _encolar(self, segundos):
        for _ in range(int(segundos * TASA / TROZO)):
            self.reproductor.encolar(np.zeros(TROZO, np.float32))

    def test_un_segundo_de_silencio_suena_y_el_corte_tarda_menos_de_100_ms(
            self):
        self._encolar(1.0)
        self.assertTrue(self.reproductor.sonando)
        time.sleep(0.05)
        inicio = time.perf_counter()
        self.reproductor.cortar()
        self.assertTrue(self.reproductor._corte_confirmado.wait(0.2))
        medido = time.perf_counter() - inicio
        self.assertFalse(self.reproductor.sonando)
        self.assertLess(medido, 0.1)
        consumidas = self.reproductor._consumidas
        time.sleep(0.05)
        self.assertEqual(self.reproductor._consumidas, consumidas)

    def test_pausar_no_avanza_y_reanudar_termina(self):
        self._encolar(1.0)
        self.reproductor.terminar()
        self.reproductor.pausar()
        self.assertTrue(self.reproductor.sonando)
        time.sleep(0.03)
        pendiente = len(self.reproductor._audio)
        time.sleep(0.1)
        self.assertEqual(len(self.reproductor._audio), pendiente)
        self.reproductor.reanudar()
        self.assertTrue(_esperar(lambda: not self.reproductor.sonando))

    def test_un_nombre_inexistente_cae_en_la_salida_predeterminada(self):
        with self.assertLogs("guyrapu.reproductor_pcm",
                             level="WARNING") as registro:
            reproductor = reproductor_pcm.ReproductorPCM("No existe")
        self.assertEqual(len(registro.records), 1)
        try:
            reproductor.empezar(TASA)
            reproductor.encolar(np.zeros(TROZO, np.float32))
            self.assertTrue(reproductor.sonando)
        finally:
            reproductor.cortar()
            reproductor.cerrar()


@unittest.skipUnless(HAY_AUDIO, "sin salida de audio")
class TestReproductorPCMTasas(unittest.TestCase):

    def _probar_tono(self, tasa):
        reproductor = reproductor_pcm.ReproductorPCM()
        try:
            reproductor.empezar(tasa)
            self.assertFalse(reproductor._mudo)
            tiempos = np.arange(int(tasa * 0.5)) / tasa
            tono = (0.01 * np.sin(2 * np.pi * 440 * tiempos)).astype(
                np.float32)
            trozo = int(tasa * 0.02)
            for inicio in range(0, len(tono), trozo):
                reproductor.encolar(tono[inicio:inicio + trozo])
            self.assertTrue(reproductor.sonando)
            reproductor.terminar()
            transcurrido = _esperar_hasta(
                lambda: not reproductor.sonando, 1.5)
            self.assertIsNotNone(transcurrido)
            self.assertGreaterEqual(transcurrido, 0.4)
            self.assertLessEqual(transcurrido, 1.5)
        finally:
            reproductor.cerrar()

    def test_un_tono_a_22050_suena_y_termina(self):
        self._probar_tono(22050)

    def test_un_tono_a_24000_suena_y_termina(self):
        self._probar_tono(24000)


class SintetizadorSilencio:
    """Sintetizador falso que entrega silencio a la tasa del reproductor."""

    tasa = TASA
    rango_velocidad = (1.0, 1.0)
    ganancia_voz = 1.0

    def voces(self):
        return ["Silencio"]

    def elegir_voz(self, idx):
        return True

    def sintetizar(self, texto, velocidad_propia):
        for _ in range(10):
            yield np.zeros(TROZO, np.float32)

    def cerrar(self):
        return


@unittest.skipUnless(HAY_AUDIO, "sin salida de audio")
class TestMotorLocalReal(unittest.TestCase):

    def test_suena_se_corta_y_se_cierra_sin_errores(self):
        motor = motor_local.MotorLocal(SintetizadorSilencio())
        try:
            self.assertTrue(motor.hablar("silencio"))
            time.sleep(0.05)
            self.assertTrue(motor.hablando())
            motor.parar()
            self.assertFalse(motor.hablando())
        finally:
            motor.cerrar()


if __name__ == "__main__":
    unittest.main()
