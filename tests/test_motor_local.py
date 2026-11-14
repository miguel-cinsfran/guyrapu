# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas del motor local con un sintetizador y un reproductor falsos."""

import threading
import time
import unittest

import numpy as np

from guyrapu.voice import escala_voz
from guyrapu.voice import motor_local

TASA = 16000
TROZO = int(TASA * 0.02)


def _esperar(condicion, plazo=3.0):
    limite = time.monotonic() + plazo
    while time.monotonic() < limite:
        if condicion():
            return True
        time.sleep(0.005)
    return condicion()


class SintetizadorFalso:
    """Entrega trozos de silencio y deja ver qué velocidad le pidieron."""

    def __init__(self, trozos=(), rango_velocidad=(1.0, 1.0),
                 por_velocidad=False, espera=None, error_en=None,
                 pausa=0.0, ganancia_voz=1.0):
        self.tasa = TASA
        self.rango_velocidad = rango_velocidad
        self.ganancia_voz = ganancia_voz
        self.velocidades = []
        self.cerrado = False
        self._trozos = list(trozos)
        self._por_velocidad = por_velocidad
        self._espera = espera
        self._error_en = error_en
        self._pausa = pausa

    def voces(self):
        return ["Voz falsa"]

    def elegir_voz(self, idx):
        return True

    def sintetizar(self, texto, velocidad_propia):
        self.velocidades.append(velocidad_propia)
        if self._espera is not None:
            self._espera.wait(2.0)
        if self._por_velocidad:
            yield np.zeros(int(TASA / velocidad_propia), np.float32)
            return
        for indice, trozo in enumerate(self._trozos):
            if self._error_en == indice:
                raise RuntimeError("fallo simulado")
            if self._pausa:
                time.sleep(self._pausa)
            yield trozo

    def cerrar(self):
        self.cerrado = True


class ReproductorFalso:
    """Anota lo que recibe y simula que la frase termina al marcarla."""

    def __init__(self):
        self.tasa = None
        self.trozos = []
        self.encolados = 0
        self.cortes = 0
        self.terminado = False
        self._sonando = False

    @property
    def sonando(self):
        return self._sonando

    def empezar(self, tasa):
        self.tasa = tasa

    def encolar(self, trozo):
        self.encolados += 1
        self.trozos.append(np.asarray(trozo))
        self._sonando = True

    def terminar(self):
        self.terminado = True
        self._sonando = False

    def cortar(self):
        self.cortes += 1
        self.trozos.clear()
        self._sonando = False

    def pausar(self):
        return

    def reanudar(self):
        return

    def cerrar(self):
        self._sonando = False


class TestMotorLocal(unittest.TestCase):

    def test_hablar_deja_hablando_en_true_antes_de_volver(self):
        listo = threading.Event()
        sintetizador = SintetizadorFalso(
            trozos=[np.zeros(TROZO, np.float32)], espera=listo)
        motor = motor_local.MotorLocal(sintetizador, ReproductorFalso())
        try:
            self.assertTrue(motor.hablar("hola"))
            self.assertTrue(motor.hablando())
            listo.set()
            self.assertTrue(_esperar(lambda: not motor.hablando()))
        finally:
            motor.cerrar()

    def test_parar_en_mitad_de_una_frase_larga_la_abandona(self):
        sintetizador = SintetizadorFalso(
            trozos=[np.zeros(TROZO, np.float32)] * 100, pausa=0.005)
        reproductor = ReproductorFalso()
        motor = motor_local.MotorLocal(sintetizador, reproductor)
        try:
            self.assertTrue(motor.hablar("una frase larga"))
            self.assertTrue(_esperar(lambda: reproductor.encolados > 0))
            motor.parar()
            self.assertFalse(motor.hablando())
            cantidad = reproductor.encolados
            time.sleep(0.08)
            self.assertLessEqual(reproductor.encolados, cantidad + 1)
            self.assertLess(cantidad, 100)
        finally:
            motor.cerrar()

    def test_un_error_del_sintetizador_no_sale_y_deja_de_hablar(self):
        sintetizador = SintetizadorFalso(
            trozos=[np.zeros(TROZO, np.float32)] * 2, error_en=1)
        reproductor = ReproductorFalso()
        motor = motor_local.MotorLocal(sintetizador, reproductor)
        errores = []
        anterior = threading.excepthook
        threading.excepthook = lambda datos: errores.append(datos.exc_value)
        try:
            self.assertTrue(motor.hablar("hola"))
            self.assertTrue(_esperar(lambda: not motor.hablando()))
            self.assertTrue(reproductor.terminado)
            self.assertEqual(errores, [])
        finally:
            threading.excepthook = anterior
            motor.cerrar()

    def test_velocidad_100_pide_el_maximo_y_estira_el_resto(self):
        sintetizador = SintetizadorFalso(
            rango_velocidad=(1.0, 2.0), por_velocidad=True)
        reproductor = ReproductorFalso()
        motor = motor_local.MotorLocal(sintetizador, reproductor)
        try:
            motor.fijar_velocidad(100)
            self.assertTrue(motor.hablar("hola"))
            self.assertTrue(_esperar(lambda: not motor.hablando()))
            self.assertEqual(sintetizador.velocidades, [2.0])
            total = sum(len(trozo) for trozo in reproductor.trozos)
            self.assertLessEqual(abs(total - TASA / 3.0), int(TASA * 0.03))
        finally:
            motor.cerrar()

    def test_la_ganancia_del_sintetizador_y_el_volumen_escalan_la_salida(
            self):
        entrada = (0.2 * np.sin(
            2 * np.pi * 440 * np.arange(TROZO) / TASA)).astype(np.float32)
        for volumen, factor in ((100, 0.5), (50, 0.25)):
            with self.subTest(volumen=volumen):
                sintetizador = SintetizadorFalso(
                    trozos=[entrada], ganancia_voz=0.5)
                reproductor = ReproductorFalso()
                motor = motor_local.MotorLocal(sintetizador, reproductor)
                try:
                    motor.fijar_velocidad(50)
                    motor.fijar_volumen(volumen)
                    motor.fijar_tono(50)
                    self.assertTrue(motor.hablar("hola"))
                    self.assertTrue(_esperar(lambda: not motor.hablando()))
                    salida = (np.concatenate(reproductor.trozos)
                              if reproductor.trozos
                              else np.empty(0, np.float32))
                    np.testing.assert_allclose(
                        salida, entrada * factor, rtol=0, atol=1e-6)
                finally:
                    motor.cerrar()

    def test_el_tono_y_la_velocidad_conservan_la_duracion_esperada(self):
        entrada = (0.01 * np.sin(
            2 * np.pi * 440 * np.arange(int(TASA * 0.5)) / TASA)).astype(
                np.float32)
        casos = (
            (70, 50, len(entrada)),
            (50, 70, len(entrada) / escala_voz.factor_velocidad_local(70)),
        )
        for tono, velocidad, esperado in casos:
            with self.subTest(tono=tono, velocidad=velocidad):
                sintetizador = SintetizadorFalso(trozos=[entrada])
                reproductor = ReproductorFalso()
                motor = motor_local.MotorLocal(sintetizador, reproductor)
                try:
                    motor.fijar_tono(tono)
                    motor.fijar_velocidad(velocidad)
                    self.assertTrue(motor.hablar("hola"))
                    self.assertTrue(_esperar(lambda: not motor.hablando()))
                    total = sum(len(trozo) for trozo in reproductor.trozos)
                    self.assertLessEqual(
                        abs(total - esperado), TROZO,
                        f"tono {tono}, velocidad {velocidad}: {total} "
                        f"muestras, se esperaban {esperado}")
                finally:
                    motor.cerrar()

    def test_hablar_vacio_o_cerrado_devuelve_false(self):
        motor = motor_local.MotorLocal(
            SintetizadorFalso(), ReproductorFalso())
        self.assertFalse(motor.hablar(""))
        self.assertFalse(motor.hablar(None))
        motor.cerrar()
        self.assertFalse(motor.hablar("hola"))


if __name__ == "__main__":
    unittest.main()
