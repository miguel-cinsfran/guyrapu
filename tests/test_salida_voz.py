# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Salida de audio de la voz: motor local, aviso y aplicación en caliente.

Sin ventanas: dobles del reproductor y del worker. La página Voces se prueba
en `test_preferencias_voz`.
"""

import queue
import unittest
from types import SimpleNamespace
from unittest import mock

from guyrapu.ui import gui_aplicar_preferencias
from guyrapu.voice import motor_local
from guyrapu.voice import tts_worker


class SintetizadorFalso:
    tasa = 16000
    rango_velocidad = (1.0, 1.0)
    ganancia_voz = 1.0


class ReproductorFalso:
    def __init__(self, dispositivo=None):
        self.dispositivo = dispositivo


class MotorFalso:
    motor = "phonon"

    def voces(self):
        return ["Voz A"]

    def elegir_voz(self, idx):
        return True

    def fijar_velocidad(self, pct):
        pass

    def fijar_volumen(self, pct):
        pass

    def fijar_tono(self, pct):
        pass

    def parar(self):
        pass

    def cerrar(self):
        pass


class TestMotorLocalConSalida(unittest.TestCase):

    def test_la_salida_llega_al_reproductor(self):
        with mock.patch.object(
                motor_local.reproductor_pcm, "listar_salidas",
                return_value=["Auriculares"]), \
                mock.patch.object(
                    motor_local.reproductor_pcm, "ReproductorPCM",
                    side_effect=ReproductorFalso) as reproductor:
            motor = motor_local.MotorLocal(
                SintetizadorFalso(), salida="Auriculares")
        self.assertEqual(reproductor.call_args.args[0], "Auriculares")
        self.assertEqual(motor._reproductor.dispositivo, "Auriculares")

    def test_la_salida_ausente_avisa_una_vez_y_usa_la_predeterminada(self):
        avisos = []
        with mock.patch.object(
                motor_local.reproductor_pcm, "listar_salidas",
                return_value=["Altavoces"]), \
                mock.patch.object(
                    motor_local.reproductor_pcm, "ReproductorPCM",
                    side_effect=ReproductorFalso) as reproductor:
            motor_local.MotorLocal(
                SintetizadorFalso(), salida="No existe",
                al_avisar=avisos.append)
        self.assertEqual(len(avisos), 1)
        self.assertIn("No existe", avisos[0])
        self.assertIn("No se encontró la salida de audio de la voz", avisos[0])
        self.assertEqual(reproductor.call_args.args, ())


class TestFabricaDelWorker(unittest.TestCase):

    def test_la_fabrica_pasa_la_salida_a_los_motores_locales(self):
        proveedor = SimpleNamespace(id="phonon", crear=mock.Mock())
        with mock.patch("guyrapu.voice.proveedores.obtener",
                        return_value=proveedor):
            worker = tts_worker.TTSWorker(
                queue.Queue(), {"salida_voz": "Auriculares"})
            worker._fabrica_motor("phonon")
        proveedor.crear.assert_called_once()
        argumentos = proveedor.crear.call_args
        self.assertEqual(argumentos.kwargs["salida"], "Auriculares")
        self.assertEqual(argumentos.kwargs["al_avisar"], worker._avisar)

    def test_la_voz_secundaria_tambien_usa_la_salida(self):
        proveedor = SimpleNamespace(
            id="phonon", crear=mock.Mock(return_value=MotorFalso()))
        with mock.patch("guyrapu.voice.proveedores.obtener",
                        return_value=proveedor):
            worker = tts_worker.TTSWorker(queue.Queue(), {
                "motor": "sapi", "motor_secundaria": "phonon",
                "salida_voz": "Auriculares"})
            worker._eleccion.voz_secundaria.preparar(
                "sapi", 50, lambda _texto: None)
        self.assertEqual(proveedor.crear.call_args.kwargs["salida"],
                         "Auriculares")

    def test_el_aviso_pendiente_llega_al_conectar_la_interfaz(self):
        worker = tts_worker.TTSWorker(queue.Queue(), {})
        worker._avisar("No se encontró la salida de audio de la voz")
        avisos = []
        worker.al_avisar = avisos.append
        self.assertEqual(avisos,
                         ["No se encontró la salida de audio de la voz"])


class TestAplicarSalidaEnCaliente(unittest.TestCase):

    def _frame(self, motor, salida, aplicada):
        frame = mock.Mock()
        frame._config = {"motor": motor, "voz": "Voz A",
                         "salida_voz": salida}
        frame._worker.motor_activo.return_value = motor
        frame._worker.salida_voz = aplicada
        frame._voz_idx = 0
        frame._voces_menu = []
        return frame

    def test_cambiar_la_salida_recrea_el_motor_local(self):
        frame = self._frame("phonon", "Auriculares", "Altavoces")
        with mock.patch("guyrapu.ui.gui.anunciar"):
            gui_aplicar_preferencias._aplicar_voz(frame, ["Voz A"])
        frame._worker.cambiar_motor.assert_called_once_with("phonon", "Voz A")

    def test_con_sapi_la_salida_no_recrea_el_motor(self):
        frame = self._frame("sapi", "Auriculares", "")
        with mock.patch("guyrapu.ui.gui.anunciar"):
            gui_aplicar_preferencias._aplicar_voz(frame, ["Voz A"])
        frame._worker.cambiar_motor.assert_not_called()


if __name__ == "__main__":
    unittest.main()
