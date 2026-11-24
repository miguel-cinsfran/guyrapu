# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas del administrador que apaga y restaura Bloq Mayús en el carril.

Las dos llamadas de Windows se doblan para no tocar el teclado real de quien
usa la máquina.
"""

import unittest

from qa.nvda import teclado_estado


class _TecladoDoble:
    """Guarda el estado que leen y anota cada vez que se lo invierte."""

    def __init__(self, estado_inicial):
        self.estado = estado_inicial
        self.lecturas = 0
        self.cambios = 0

    def leer(self):
        self.lecturas += 1
        return self.estado

    def cambiar(self):
        self.cambios += 1
        self.estado ^= 1


class TestBloqMayus(unittest.TestCase):

    def test_encendido_se_apaga_y_vuelve_a_encender_al_salir(self):
        teclado = _TecladoDoble(1)
        with teclado_estado.con_bloq_mayus_apagado(
                teclado.leer, teclado.cambiar):
            self.assertEqual(teclado.estado, 0)
        self.assertEqual(teclado.estado, 1)
        self.assertEqual(teclado.cambios, 2)
        self.assertEqual(teclado.lecturas, 1)

    def test_encendido_con_excepcion_tambien_vuelve_a_encender(self):
        teclado = _TecladoDoble(1)
        with self.assertRaises(ValueError):
            with teclado_estado.con_bloq_mayus_apagado(
                    teclado.leer, teclado.cambiar):
                raise ValueError("falló una ventana")
        self.assertEqual(teclado.estado, 1)
        self.assertEqual(teclado.cambios, 2)

    def test_apagado_no_toca_la_tecla(self):
        teclado = _TecladoDoble(0)
        with teclado_estado.con_bloq_mayus_apagado(
                teclado.leer, teclado.cambiar):
            self.assertEqual(teclado.estado, 0)
        self.assertEqual(teclado.cambios, 0)
        self.assertEqual(teclado.lecturas, 1)

    def test_el_estado_real_de_windows_es_cero_o_uno(self):
        self.assertIn(teclado_estado.estado(), (0, 1))


if __name__ == "__main__":
    unittest.main()
