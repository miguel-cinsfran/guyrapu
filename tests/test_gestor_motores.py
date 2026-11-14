# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Tests del gestor del motor principal: voces, voz base, cambios y cierre."""

import queue
import unittest

from guyrapu.voice import gestor_motores
from guyrapu.voice import motores
from guyrapu.voice import tts_worker


class Motor:
    """Doble mínimo del envoltorio de Prism para el gestor."""

    def __init__(self, voces=("Voz A", "Voz B"), motor="sapi"):
        self.motor = motor
        self._voces = list(voces)
        self.elegidas = []
        self.velocidad = self.volumen = self.tono = None
        self.paradas = 0
        self.cerrado = False

    def voces(self):
        return list(self._voces)

    def elegir_voz(self, idx):
        self.elegidas.append(idx)
        return True

    def fijar_velocidad(self, pct):
        self.velocidad = pct

    def fijar_volumen(self, pct):
        self.volumen = pct

    def fijar_tono(self, pct):
        self.tono = pct

    def parar(self):
        self.paradas += 1

    def cerrar(self):
        self.cerrado = True


class Fabrica:
    def __init__(self, por_nombre, fallan=()):
        self.por_nombre = por_nombre
        self.fallan = set(fallan)
        self.creados = []

    def __call__(self, nombre):
        self.creados.append(nombre)
        if nombre in self.fallan:
            raise motores.MotorNoDisponible(f"{nombre} no disponible")
        return self.por_nombre[nombre]


def _gestor(motor, **config):
    fabrica = Fabrica({"sapi": motor})
    gestor = gestor_motores.GestorMotores(fabrica)
    gestor.abrir(config.get("motor") or "sapi", config.get("voz"),
                 config.get("velocidad", 50), config.get("volumen", 100),
                 config.get("tono", 50))
    return gestor, fabrica


class TestGestorMotores(unittest.TestCase):
    """El gestor es dueño del motor principal, sus voces y su voz activa."""

    def test_abre_y_expone_motor_voces_y_voz_activa(self):
        motor = Motor()
        gestor, _fabrica = _gestor(motor, voz="Voz B", velocidad=40,
                                   volumen=50, tono=30)
        self.assertIs(gestor.motor, motor)
        self.assertEqual(gestor.voces, ["Voz A", "Voz B"])
        self.assertEqual(gestor.voz_base, 1)
        self.assertEqual(gestor.voz_actual, 1)
        self.assertEqual((motor.velocidad, motor.volumen, motor.tono),
                         (40, 50, 30))

    def test_cambiar_con_motor_sin_voces_conserva_el_viejo(self):
        viejo = Motor()
        nuevo = Motor(voces=())
        fabrica = Fabrica({"sapi": viejo, "onecore": nuevo})
        gestor = gestor_motores.GestorMotores(fabrica)
        gestor.abrir("sapi", None, 50, 100, 50)

        gestor.cambiar("onecore", None, 50, 100, 50)

        self.assertIs(gestor.motor, viejo)
        self.assertFalse(viejo.cerrado)
        self.assertTrue(nuevo.cerrado)

    def test_cambiar_voz_base_y_aplicar_voz(self):
        motor = Motor()
        gestor, _fabrica = _gestor(motor, voz="Voz A")
        motor.elegidas.clear()

        gestor.cambiar_voz_base("Voz B")
        self.assertEqual(gestor.voz_base, 1)
        gestor.aplicar_voz(None)
        self.assertEqual(gestor.voz_actual, 1)
        gestor.aplicar_voz("Inexistente")
        self.assertEqual(motor.elegidas, [1])

    def test_cerrar_cierra_el_motor(self):
        motor = Motor()
        gestor, _fabrica = _gestor(motor)
        gestor.cerrar()
        self.assertTrue(motor.cerrado)


class TestUsoDelWorker(unittest.TestCase):
    """El worker delega en el gestor y no guarda el motor por su cuenta."""

    def test_el_worker_usa_el_gestor_y_no_guarda_sus_datos(self):
        worker = tts_worker.TTSWorker(
            queue.Queue(), {}, fabrica_motor=Fabrica({"sapi": Motor()}))
        self.assertIsInstance(worker._gestor, gestor_motores.GestorMotores)
        for nombre in ("_motor", "_voces", "_voz_base", "_voz_actual"):
            self.assertFalse(hasattr(worker, nombre), nombre)


if __name__ == "__main__":
    unittest.main()
