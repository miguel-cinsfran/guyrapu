# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de los ajustes de audio puros (ganancia, limitador, WSOLA y tono)."""

import unittest

import numpy as np

from guyrapu.voice import ajustes_audio

TASA = 16000
TROZO = int(TASA * 0.02)
VENTANA = int(round(TASA * 0.03))


def _tono(frecuencia=440.0, segundos=1.0, amplitud=0.5):
    tiempos = np.arange(int(TASA * segundos)) / TASA
    return (amplitud * np.sin(2 * np.pi * frecuencia * tiempos)).astype(
        np.float32)


def _dominante(senal):
    tamano = 1 << int(np.ceil(np.log2(len(senal))))
    espectro = np.abs(np.fft.rfft(senal * np.hanning(len(senal)), tamano))
    return float(np.fft.rfftfreq(tamano, 1 / TASA)[int(np.argmax(espectro))])


def _en_trozos(procesador, senal):
    partes = []
    for inicio in range(0, len(senal), TROZO):
        salida = procesador.procesar(senal[inicio:inicio + TROZO])
        if len(salida):
            partes.append(salida)
    fin = procesador.vaciar()
    if len(fin):
        partes.append(fin)
    uniones = np.cumsum([len(parte) for parte in partes])[:-1]
    if partes:
        return np.concatenate(partes), uniones
    return np.empty(0, np.float32), uniones


def _de_una_vez(procesador, senal):
    partes = [procesador.procesar(senal), procesador.vaciar()]
    return np.concatenate([parte for parte in partes if len(parte)])


class TestEstirador(unittest.TestCase):

    def test_velocidad_dos_dura_la_mitad_y_mantiene_la_frecuencia(self):
        salida, _uniones = _en_trozos(
            ajustes_audio.Estirador(TASA, 2.0), _tono())
        self.assertLessEqual(abs(len(salida) - len(_tono()) / 2), VENTANA)
        self.assertAlmostEqual(_dominante(salida), 440.0, delta=5.0)

    def test_trozos_o_de_una_vez_dan_la_misma_duracion_y_sin_cortes(self):
        senal = _tono()
        en_trozos, uniones = _en_trozos(
            ajustes_audio.Estirador(TASA, 2.0), senal)
        de_una = _de_una_vez(ajustes_audio.Estirador(TASA, 2.0), senal)
        self.assertLessEqual(abs(len(en_trozos) - len(de_una)), VENTANA)
        self._comprobar_uniones(en_trozos, uniones)

    def test_factor_uno_devuelve_las_mismas_muestras(self):
        senal = _tono()
        procesador = ajustes_audio.Estirador(TASA, 1.0)
        partes = []
        for inicio in range(0, len(senal), TROZO):
            partes.append(procesador.procesar(senal[inicio:inicio + TROZO]))
        self.assertEqual(len(procesador.vaciar()), 0)
        np.testing.assert_array_equal(np.concatenate(partes), senal)

    def _comprobar_uniones(self, salida, uniones):
        self.assertGreater(len(uniones), 0)
        diferencias = np.abs(np.diff(salida))
        dentro = np.delete(diferencias, uniones - 1)
        self.assertGreater(len(dentro), 0)
        mayor = float(np.max(dentro))
        for union in uniones:
            self.assertLessEqual(float(diferencias[union - 1]), mayor + 1e-6)


class TestCambioTono(unittest.TestCase):

    def test_doce_semitonos_conservan_la_duracion_y_suben_la_frecuencia(self):
        senal = _tono()
        salida, _uniones = _en_trozos(
            ajustes_audio.CambioTono(TASA, 12), senal)
        self.assertLessEqual(abs(len(salida) - len(senal)), VENTANA)
        self.assertAlmostEqual(_dominante(salida), 880.0, delta=5.0)

    def test_trozos_o_de_una_vez_dan_la_misma_duracion_y_sin_cortes(self):
        senal = _tono()
        en_trozos, uniones = _en_trozos(
            ajustes_audio.CambioTono(TASA, 12), senal)
        de_una = _de_una_vez(ajustes_audio.CambioTono(TASA, 12), senal)
        self.assertLessEqual(abs(len(en_trozos) - len(de_una)), VENTANA)
        self._comprobar_uniones(en_trozos, uniones)

    def test_cero_semitonos_devuelve_las_mismas_muestras(self):
        senal = _tono()
        procesador = ajustes_audio.CambioTono(TASA, 0)
        partes = []
        for inicio in range(0, len(senal), TROZO):
            partes.append(procesador.procesar(senal[inicio:inicio + TROZO]))
        self.assertEqual(len(procesador.vaciar()), 0)
        np.testing.assert_array_equal(np.concatenate(partes), senal)

    def _comprobar_uniones(self, salida, uniones):
        self.assertGreater(len(uniones), 0)
        diferencias = np.abs(np.diff(salida))
        dentro = np.delete(diferencias, uniones - 1)
        self.assertGreater(len(dentro), 0)
        mayor = float(np.max(dentro))
        for union in uniones:
            self.assertLessEqual(float(diferencias[union - 1]), mayor + 1e-6)


class TestGananciaYLimitador(unittest.TestCase):

    def test_la_ganancia_escala_todo_el_trozo(self):
        trozo = _tono(amplitud=0.2)
        salida = ajustes_audio.aplicar_ganancia(trozo, 0.5)
        np.testing.assert_allclose(salida, trozo * 0.5, rtol=0, atol=1e-7)

    def test_el_limitador_deja_el_pico_en_098_y_conserva_la_forma(self):
        trozo = _tono(amplitud=1.5)
        salida = ajustes_audio.limitar(trozo)
        self.assertAlmostEqual(float(np.max(np.abs(salida))), 0.98, places=5)
        self.assertAlmostEqual(
            float(np.corrcoef(trozo, salida)[0, 1]), 1.0, places=6)


if __name__ == "__main__":
    unittest.main()
