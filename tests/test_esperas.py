# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de las cadencias y de la espera con motivo."""

import threading
import unittest

from guyrapu.core import esperas
from guyrapu.core.tiempo import TiempoDoble


class TestCadencias(unittest.TestCase):

    def test_fija(self):
        cadencia = esperas.Fija(2.0)
        self.assertEqual([cadencia.espera(n, 100.0) for n in range(4)],
                         [2.0, 2.0, 2.0, 2.0])

    def test_rapida_y_lenta_cambia_con_el_tiempo_transcurrido(self):
        cadencia = esperas.RapidaYLenta(5.0, 120.0, 30.0)
        self.assertEqual(cadencia.espera(0, 0.0), 5.0)
        self.assertEqual(cadencia.espera(20, 119.0), 5.0)
        self.assertEqual(cadencia.espera(30, 120.0), 30.0)
        self.assertEqual(cadencia.espera(40, 500.0), 30.0)

    def test_creciente_duplica_hasta_el_techo(self):
        cadencia = esperas.Creciente(2.0, 30.0)
        self.assertEqual([cadencia.espera(n, 0.0) for n in range(6)],
                         [2.0, 4.0, 8.0, 16.0, 30.0, 30.0])


class TestEsperar(unittest.TestCase):

    def test_se_detiene_cuando_el_resultado_esta_listo(self):
        tiempo = TiempoDoble()
        consultas = []

        def consultar():
            consultas.append(tiempo.ahora())
            return len(consultas)

        resultado = esperas.esperar(consultar, lambda valor: valor >= 3,
                                    cadencia=esperas.Fija(2.0), plazo=100.0,
                                    tiempo=tiempo)
        self.assertEqual(resultado, esperas.Resultado(3, "listo"))
        self.assertEqual(consultas, [0.0, 2.0, 4.0])

    def test_el_plazo_devuelve_el_ultimo_valor(self):
        tiempo = TiempoDoble()

        def consultar():
            return "sin directo"

        resultado = esperas.esperar(consultar, lambda valor: False,
                                    cadencia=esperas.Fija(4.0), plazo=10.0,
                                    tiempo=tiempo)
        self.assertEqual(resultado, esperas.Resultado("sin directo", "plazo"))
        self.assertEqual(tiempo.dormidas, [4.0, 4.0, 2.0])

    def test_el_tope_de_intentos_devuelve_el_ultimo_valor(self):
        tiempo = TiempoDoble()
        consultas = []

        def consultar():
            consultas.append(tiempo.ahora())
            return False

        resultado = esperas.esperar(consultar, bool,
                                    cadencia=esperas.Fija(1.0), intentos=3,
                                    tiempo=tiempo)
        self.assertEqual(resultado, esperas.Resultado(False, "intentos"))
        self.assertEqual(len(consultas), 3)

    def test_la_parada_corta_antes_de_otra_consulta(self):
        tiempo = TiempoDoble()
        parada = threading.Event()
        consultas = []

        def consultar():
            consultas.append(tiempo.ahora())
            parada.set()
            return "a medias"

        resultado = esperas.esperar(consultar, lambda valor: False,
                                    cadencia=esperas.Fija(5.0), parada=parada,
                                    tiempo=tiempo)
        self.assertEqual(resultado, esperas.Resultado("a medias", "parada"))
        self.assertEqual(consultas, [0.0])

    def test_la_parada_corta_el_sueno(self):
        tiempo = TiempoDoble()
        parada = threading.Event()
        tiempo.programar_parada(3.0, parada)
        consultas = []

        def consultar():
            consultas.append(tiempo.ahora())
            return False

        resultado = esperas.esperar(consultar, bool,
                                    cadencia=esperas.Fija(5.0), parada=parada,
                                    tiempo=tiempo)
        self.assertEqual(resultado, esperas.Resultado(False, "parada"))
        self.assertEqual(consultas, [0.0])

    def test_ninguna_cadencia_suma_mas_que_el_plazo(self):
        cadencias = (esperas.Fija(7.0),
                     esperas.RapidaYLenta(2.0, 12.0, 9.0),
                     esperas.Creciente(2.0, 30.0))
        for cadencia in cadencias:
            with self.subTest(cadencia=cadencia):
                tiempo = TiempoDoble()
                resultado = esperas.esperar(lambda: None, lambda valor: False,
                                            cadencia=cadencia, plazo=25.0,
                                            tiempo=tiempo)
                self.assertEqual(resultado.motivo, "plazo")
                self.assertLessEqual(sum(tiempo.dormidas), 25.0)
                self.assertAlmostEqual(sum(tiempo.dormidas), 25.0)


class TestTolerancia(unittest.TestCase):

    def test_un_error_tolerado_cuenta_como_no_listo(self):
        tiempo = TiempoDoble()
        intentos = []

        def consultar():
            intentos.append(tiempo.ahora())
            if len(intentos) < 3:
                raise ValueError("todavía no")
            return "listo"

        resultado = esperas.esperar(consultar,
                                    lambda valor: valor == "listo",
                                    cadencia=esperas.Fija(1.0),
                                    tolerar=(ValueError,), tiempo=tiempo)
        self.assertEqual(resultado, esperas.Resultado("listo", "listo"))
        self.assertEqual(len(intentos), 3)

    def test_sin_la_tupla_el_error_sale(self):
        def consultar():
            raise ValueError("no tolerado")

        with self.assertRaises(ValueError):
            esperas.esperar(consultar, bool, cadencia=esperas.Fija(1.0),
                            tiempo=TiempoDoble())


if __name__ == "__main__":
    unittest.main()
