# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Contrato que cumple cada proveedor de voz registrado.

El registro se recorre entero: sumar un proveedor lo somete a las mismas
reglas sin tocar este archivo. Con el motor real se prueba de verdad, salvo
los de la nube y los que esta máquina no tenga.
"""

import os
import time
import unittest

from guyrapu.voice.proveedores import PROVEEDORES
from guyrapu.voice.proveedores.base import Motor, MotorNoDisponible

CON_RED = os.environ.get("GUYRAPU_PRUEBAS_CON_RED") == "1"


class TestRegistro(unittest.TestCase):

    def test_los_proveedores_van_en_orden(self):
        self.assertEqual([proveedor.id for proveedor in PROVEEDORES],
                         ["sapi", "onecore", "elevenlabs", "phonon",
                          "piper"])


class TestContrato(unittest.TestCase):

    def test_id_unico_y_en_minusculas(self):
        vistos = set()
        for proveedor in PROVEEDORES:
            with self.subTest(proveedor=proveedor.id):
                self.assertEqual(proveedor.id, proveedor.id.lower())
                self.assertNotIn(proveedor.id, vistos)
                vistos.add(proveedor.id)

    def test_nombre_y_licencia_no_vacios(self):
        for proveedor in PROVEEDORES:
            with self.subTest(proveedor=proveedor.id):
                self.assertTrue(proveedor.nombre.strip())
                self.assertTrue(proveedor.licencia.strip())

    def test_listar_voces_devuelve_textos(self):
        for proveedor in PROVEEDORES:
            with self.subTest(proveedor=proveedor.id):
                if proveedor.capacidades.nube and not CON_RED:
                    self.skipTest("la nube se prueba solo con "
                                  "GUYRAPU_PRUEBAS_CON_RED=1")
                voces = proveedor.listar_voces()
                self.assertIsInstance(voces, list)
                for voz in voces:
                    self.assertIsInstance(voz, str)

    def test_crear_devuelve_un_motor_o_lanza_no_disponible(self):
        for proveedor in PROVEEDORES:
            with self.subTest(proveedor=proveedor.id):
                if proveedor.capacidades.nube and not CON_RED:
                    self.skipTest("la nube se prueba solo con "
                                  "GUYRAPU_PRUEBAS_CON_RED=1")
                try:
                    motor = proveedor.crear()
                except MotorNoDisponible:
                    continue
                try:
                    self.assertIsInstance(motor, Motor)
                finally:
                    motor.cerrar()


class TestMotorReal(unittest.TestCase):

    def test_el_motor_real_cumple_el_contrato(self):
        for proveedor in PROVEEDORES:
            with self.subTest(proveedor=proveedor.id):
                if proveedor.capacidades.nube and not CON_RED:
                    self.skipTest("la nube se prueba solo con "
                                  "GUYRAPU_PRUEBAS_CON_RED=1")
                try:
                    motor = proveedor.crear()
                except MotorNoDisponible as exc:
                    self.skipTest(f"{proveedor.id} no está disponible: {exc}")
                try:
                    motor.fijar_volumen(0)
                    motor.elegir_voz(0)
                    self.assertTrue(motor.hablar("prueba"))
                    limite = time.monotonic() + 2.0
                    while not motor.hablando() and time.monotonic() < limite:
                        time.sleep(0.01)
                    self.assertTrue(motor.hablando())
                    motor.parar()
                    limite = time.monotonic() + 1.0
                    while motor.hablando() and time.monotonic() < limite:
                        time.sleep(0.01)
                    self.assertFalse(motor.hablando())
                finally:
                    motor.cerrar()
                self.assertFalse(motor.hablando())


if __name__ == "__main__":
    unittest.main()
