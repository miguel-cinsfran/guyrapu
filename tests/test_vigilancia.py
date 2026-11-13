# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas del estado de un enlace en vivo y del filtro de avisos."""

import unittest

from guyrapu.core import vigilancia
from guyrapu.core.tiempo import TiempoDoble


CAIDA = vigilancia.Aviso("se cayó", "error")
VUELTA = vigilancia.Aviso("volvió", "conectado")
RENDICION = vigilancia.Aviso("me rindo", "error")


class TestVigilancia(unittest.TestCase):

    def _crear(self, tiempo, **extra):
        avisos = []
        vigia = vigilancia.Vigilancia(
            lambda frase, sonido: avisos.append((frase, sonido)),
            caida=CAIDA, vuelta=VUELTA, rendicion=RENDICION,
            tiempo=tiempo, **extra)
        return vigia, avisos

    def test_una_caida_y_una_vuelta(self):
        tiempo = TiempoDoble()
        vigia, avisos = self._crear(tiempo)
        vigia.leida(True)
        vigia.leida(False)
        vigia.leida(False)
        self.assertTrue(vigia.caido)
        self.assertEqual(vigia.desde, 0.0)
        vigia.leida(True)
        self.assertFalse(vigia.caido)
        self.assertIsNone(vigia.desde)
        self.assertEqual(avisos, [("se cayó", "error"),
                                  ("volvió", "conectado")])

    def test_varias_lecturas_malas_seguidas_son_una_sola_caida(self):
        tiempo = TiempoDoble()
        vigia, avisos = self._crear(tiempo, max_caidas=3,
                                    duracion_estable=60.0)
        vigia.leida(True)
        for _ in range(5):
            tiempo.avanzar(1.0)
            vigia.leida(False)
        self.assertFalse(vigia.rendido)
        self.assertEqual(avisos.count(("se cayó", "error")), 1)

    def test_tres_caidas_separadas_por_vueltas_rinden_una_sola_vez(self):
        tiempo = TiempoDoble()
        vigia, avisos = self._crear(tiempo, max_caidas=3,
                                    duracion_estable=60.0)
        for _ in range(3):
            vigia.leida(True)
            tiempo.avanzar(1.0)
            vigia.leida(False)
            tiempo.avanzar(1.0)
        self.assertTrue(vigia.rendido)
        self.assertEqual(avisos.count(("me rindo", "error")), 1)
        tiempo.avanzar(1.0)
        vigia.leida(False)
        self.assertEqual(avisos.count(("me rindo", "error")), 1)

    def test_una_conexion_larga_reinicia_la_cuenta(self):
        tiempo = TiempoDoble()
        vigia, avisos = self._crear(tiempo, max_caidas=3,
                                    duracion_estable=60.0)
        vigia.leida(False)
        vigia.leida(True)
        tiempo.avanzar(1.0)
        vigia.leida(False)
        vigia.leida(True)
        tiempo.avanzar(60.0)
        vigia.leida(False)
        self.assertFalse(vigia.rendido)
        self.assertEqual(avisos.count(("me rindo", "error")), 0)

    def test_la_gracia_calla_la_caida_y_la_anuncia_al_vencer(self):
        tiempo = TiempoDoble()
        vigia, avisos = self._crear(tiempo, gracia=60.0)
        vigia.leida(False)
        tiempo.avanzar(59.0)
        vigia.leida(False)
        self.assertEqual(avisos, [])
        tiempo.avanzar(1.0)
        vigia.leida(False)
        self.assertTrue(vigia.caido)
        self.assertEqual(avisos, [("se cayó", "error")])

    def test_una_lectura_buena_dentro_de_la_gracia_no_anuncia_nada(self):
        tiempo = TiempoDoble()
        vigia, avisos = self._crear(tiempo, gracia=60.0)
        vigia.leida(False)
        vigia.leida(True)
        self.assertFalse(vigia.caido)
        self.assertEqual(avisos, [])

    def test_con_gracia_y_ya_respondido_el_fallo_se_anuncia_enseguida(self):
        tiempo = TiempoDoble()
        vigia, avisos = self._crear(tiempo, gracia=60.0)
        vigia.leida(True)
        vigia.leida(False)
        self.assertEqual(avisos, [("se cayó", "error")])

    def test_reiniciar_gracia_devuelve_la_gracia_sin_borrar_la_caida(self):
        tiempo = TiempoDoble()
        vigia, avisos = self._crear(tiempo, gracia=60.0)
        vigia.leida(False)
        tiempo.avanzar(60.0)
        vigia.leida(False)
        desde = vigia.desde
        vigia.reiniciar_gracia()
        self.assertTrue(vigia.caido)
        self.assertEqual(vigia.desde, desde)
        vigia.leida(True)
        avisos_antes = list(avisos)
        tiempo.avanzar(1.0)
        vigia.reiniciar_gracia()
        vigia.leida(False)
        self.assertEqual(avisos, avisos_antes)
        tiempo.avanzar(60.0)
        vigia.leida(False)
        self.assertEqual(avisos, avisos_antes + [("se cayó", "error")])


class TestAvisosRepetidos(unittest.TestCase):

    def test_cada_tipo_tiene_su_plazo(self):
        tiempo = TiempoDoble()
        avisos = vigilancia.AvisosRepetidos(tiempo.ahora, plazo=10.0,
                                            plazos={"sobrecarga": 2.0})
        self.assertTrue(avisos.toca("red"))
        tiempo.avanzar(5.0)
        self.assertFalse(avisos.toca("red"))
        self.assertTrue(avisos.toca("sobrecarga"))
        tiempo.avanzar(2.0)
        self.assertTrue(avisos.toca("sobrecarga"))
        self.assertFalse(avisos.toca("red"))
        tiempo.avanzar(3.0)
        self.assertTrue(avisos.toca("red"))

    def test_los_plazos_por_defecto_y_la_vuelta_siempre_toca(self):
        tiempo = TiempoDoble()
        avisos = vigilancia.AvisosRepetidos(tiempo.ahora)
        self.assertTrue(avisos.toca("red"))
        self.assertFalse(avisos.toca("red"))
        tiempo.avanzar(59.0)
        self.assertFalse(avisos.toca("red"))
        tiempo.avanzar(1.0)
        self.assertTrue(avisos.toca("red"))
        self.assertTrue(avisos.toca("vuelta"))
        self.assertTrue(avisos.toca("vuelta"))

    def test_la_sobrecarga_espera_su_plazo_mas_largo(self):
        tiempo = TiempoDoble()
        avisos = vigilancia.AvisosRepetidos(tiempo.ahora)
        self.assertTrue(avisos.toca("sobrecarga"))
        tiempo.avanzar(299.0)
        self.assertFalse(avisos.toca("sobrecarga"))
        tiempo.avanzar(1.0)
        self.assertTrue(avisos.toca("sobrecarga"))


if __name__ == "__main__":
    unittest.main()
