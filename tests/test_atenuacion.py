# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas del atenuador de la música, con el reloj en manos de la prueba."""

import unittest

from guyrapu.music import atenuacion


class RelojFalso:
    def __init__(self, ahora=0.0):
        self.ahora = ahora

    def __call__(self):
        return self.ahora

    def avanzar(self, segundos):
        self.ahora += segundos


class TestAtenuador(unittest.TestCase):

    def _crear(self, reloj=None, activas=("voz", "medio"), porcentaje=30):
        reloj = reloj if reloj is not None else RelojFalso()
        atenuador = atenuacion.Atenuador(reloj=reloj)
        atenuador.configurar(activas, porcentaje)
        return atenuador, reloj

    def test_sin_pedidos_el_factor_es_uno(self):
        atenuador, reloj = self._crear()
        reloj.avanzar(10)
        self.assertEqual(1.0, atenuador.factor(reloj()))

    def test_la_bajada_llega_al_porcentaje_en_tres_decimos(self):
        atenuador, reloj = self._crear()
        atenuador.pedir("voz", 5)
        reloj.avanzar(0.15)
        self.assertTrue(0.3 < atenuador.factor(reloj()) < 1.0)
        reloj.avanzar(0.15)
        self.assertAlmostEqual(0.3, atenuador.factor(reloj()))

    def test_la_subida_espera_ocho_decimos_y_dura_uno_cinco(self):
        atenuador, reloj = self._crear()
        atenuador.pedir("voz", 5)
        reloj.avanzar(0.3)
        atenuador.soltar("voz")
        reloj.avanzar(0.8)
        self.assertAlmostEqual(0.3, atenuador.factor(reloj()))
        reloj.avanzar(0.75)
        self.assertAlmostEqual(0.65, atenuador.factor(reloj()))
        reloj.avanzar(0.75)
        self.assertAlmostEqual(1.0, atenuador.factor(reloj()))

    def test_un_pedido_vencido_sube_sin_que_nadie_suelte(self):
        atenuador, reloj = self._crear()
        atenuador.pedir("voz", 1)
        reloj.avanzar(1)
        atenuador.factor(reloj())
        reloj.avanzar(0.8)
        self.assertAlmostEqual(0.3, atenuador.factor(reloj()))
        reloj.avanzar(1.5)
        self.assertAlmostEqual(1.0, atenuador.factor(reloj()))

    def test_un_pedido_se_renueva_al_volver_a_pedirlo(self):
        atenuador, reloj = self._crear()
        atenuador.pedir("voz", 0.5)
        reloj.avanzar(0.4)
        atenuador.pedir("voz", 0.5)
        reloj.avanzar(0.2)
        self.assertAlmostEqual(0.3, atenuador.factor(reloj()))

    def test_dos_fuentes_y_una_suelta_siguen_bajo(self):
        atenuador, reloj = self._crear()
        atenuador.pedir("voz", 5)
        atenuador.pedir("medio", 5)
        reloj.avanzar(0.3)
        atenuador.soltar("voz")
        reloj.avanzar(2)
        self.assertAlmostEqual(0.3, atenuador.factor(reloj()))
        atenuador.soltar("medio")
        reloj.avanzar(0.8 + 1.5)
        self.assertAlmostEqual(1.0, atenuador.factor(reloj()))

    def test_una_fuente_apagada_no_baja(self):
        atenuador, reloj = self._crear(activas=("medio",))
        atenuador.pedir("voz", 5)
        reloj.avanzar(1)
        self.assertEqual(1.0, atenuador.factor(reloj()))

    def test_un_nuevo_pedido_durante_la_subida_no_salta(self):
        atenuador, reloj = self._crear()
        atenuador.pedir("voz", 1)
        reloj.avanzar(0.3)
        atenuador.soltar("voz")
        reloj.avanzar(0.8 + 0.75)
        antes = atenuador.factor(reloj())
        atenuador.pedir("medio", 1)
        self.assertAlmostEqual(antes, atenuador.factor(reloj()))
        reloj.avanzar(0.3)
        self.assertAlmostEqual(0.3, atenuador.factor(reloj()))

    def test_el_factor_nunca_sale_del_rango(self):
        atenuador, reloj = self._crear(porcentaje=40)
        for paso in range(120):
            if paso % 7 == 0:
                atenuador.pedir("voz", 2)
            if paso % 11 == 0:
                atenuador.soltar("voz")
                atenuador.pedir("medio", 1)
            reloj.avanzar(0.1)
            valor = atenuador.factor(reloj())
            self.assertGreaterEqual(valor, 0.4)
            self.assertLessEqual(valor, 1.0)


if __name__ == "__main__":
    unittest.main()
