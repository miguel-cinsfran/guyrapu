# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de la prueba de voz, sin ventanas."""

import threading
import unittest
from unittest import mock

from tests.pseudo_prueba import con_pseudo
from guyrapu.ui import prueba_voz
from guyrapu.voice import escala_voz
from guyrapu.voice import motor_elevenlabs
from guyrapu.voice import motores


class _HiloInmediato:

    def __init__(self, target):
        self._target = target

    def start(self):
        self._target()


class _HiloQuieto:

    def start(self):
        pass


class _HiloLanzado:

    def __init__(self, target, hilos):
        self._target = target
        self._hilos = hilos

    def start(self):
        hilo = threading.Thread(target=self._target, daemon=True)
        self._hilos.append(hilo)
        hilo.start()


class _MotorWindowsFalso:

    def __init__(self, hablando=None):
        self.llamadas = []
        self.dicho = None
        self.cerrado = 0
        self.consultas_hablando = 0
        self._hablando = [True, False] if hablando is None else hablando

    def elegir_voz(self, idx):
        self.llamadas.append("elegir_voz")

    def fijar_velocidad(self, valor):
        self.llamadas.append("fijar_velocidad")

    def fijar_volumen(self, valor):
        self.llamadas.append("fijar_volumen")

    def fijar_tono(self, valor):
        self.llamadas.append("fijar_tono")

    def hablar(self, texto):
        self.llamadas.append("hablar")
        self.dicho = texto

    def hablando(self):
        self.consultas_hablando += 1
        if isinstance(self._hablando, list):
            return self._hablando.pop(0) if self._hablando else False
        return self._hablando

    def cerrar(self):
        self.cerrado += 1


class _MotorElevenFalso:

    def __init__(self, error=None):
        self.error = error
        self.cerrado = 0
        self.dicho = None

    def voces(self):
        return ["Ana"]

    def elegir_voz(self, idx):
        self.voz = idx

    def fijar_velocidad(self, valor):
        self.velocidad = valor

    def fijar_volumen(self, valor):
        self.volumen = valor

    def hablar(self, texto):
        if self.error is not None:
            raise self.error
        self.dicho = texto

    def hablando(self):
        return False

    def cerrar(self):
        self.cerrado += 1


class TestProbarPrism(unittest.TestCase):

    def test_no_crea_el_motor_antes_de_que_corra_el_hilo(self):
        with mock.patch.object(motores, "MotorPrism") as crear, \
                mock.patch.object(
                    prueba_voz.diagnostico, "crear_hilo",
                    return_value=_HiloQuieto()) as crear_hilo:
            prueba = prueba_voz.PruebaVoz()
            prueba.probar_prism("sapi", 2, 60, 70, 40)

        crear.assert_not_called()
        self.assertEqual(crear_hilo.call_args[0][1], "ProbarVoz")

    def _prueba_lanzada(self, motor, hilos):
        return mock.patch.object(
            prueba_voz.diagnostico, "crear_hilo",
            side_effect=lambda target, nombre, **kw: _HiloLanzado(target, hilos))

    def test_el_hilo_configura_habla_y_cierra_el_motor(self):
        motor = _MotorWindowsFalso()
        with mock.patch.object(motores, "MotorPrism", return_value=motor), \
                mock.patch.object(
                    prueba_voz.diagnostico, "crear_hilo",
                    side_effect=lambda target, nombre, **kw: _HiloInmediato(target)), \
                mock.patch.object(prueba_voz, "VIDA_PRUEBA_VOZ", 0.01), \
                mock.patch.object(prueba_voz, "anunciar") as anunciar:
            prueba = prueba_voz.PruebaVoz()
            prueba.probar_prism("sapi", 2, 60, 70, 40)

        self.assertEqual(motor.llamadas, [
            "elegir_voz", "fijar_velocidad", "fijar_volumen", "fijar_tono",
            "hablar"])
        self.assertEqual(motor.dicho, "Así suena esta voz.")
        self.assertEqual(motor.cerrado, 1)
        self.assertEqual(motor.consultas_hablando, 0)
        self.assertIsNone(prueba._corte_prism)
        anunciar.assert_not_called()

    def test_no_cierra_el_motor_mientras_no_se_ponga_el_corte(self):
        motor = _MotorWindowsFalso(hablando=False)
        hilos = []
        with mock.patch.object(motores, "MotorPrism", return_value=motor), \
                self._prueba_lanzada(motor, hilos):
            prueba = prueba_voz.PruebaVoz()
            prueba.probar_prism("sapi", 0, 50, 50, 50)
            hilos[0].join(2.5)
            self.assertEqual(motor.cerrado, 0)
            prueba.cerrar()
            hilos[0].join(2)

        self.assertEqual(motor.cerrado, 1)

    def test_una_segunda_prueba_cierra_la_primera(self):
        motor = _MotorWindowsFalso(hablando=False)
        hilos = []
        with mock.patch.object(motores, "MotorPrism", return_value=motor), \
                self._prueba_lanzada(motor, hilos):
            prueba = prueba_voz.PruebaVoz()
            prueba.probar_prism("sapi", 0, 50, 50, 50)
            prueba.probar_prism("sapi", 0, 50, 50, 50)
            hilos[0].join(2)
            self.assertEqual(motor.cerrado, 1)
            prueba.cerrar()
            hilos[1].join(2)

        self.assertEqual(motor.cerrado, 2)

    def test_cerrar_cierra_el_motor(self):
        motor = _MotorWindowsFalso(hablando=False)
        hilos = []
        with mock.patch.object(motores, "MotorPrism", return_value=motor), \
                self._prueba_lanzada(motor, hilos):
            prueba = prueba_voz.PruebaVoz()
            prueba.probar_prism("sapi", 0, 50, 50, 50)
            prueba.cerrar()
            hilos[0].join(2)

        self.assertEqual(motor.cerrado, 1)

    def test_se_cierra_al_vencer_la_vida_de_la_prueba(self):
        motor = _MotorWindowsFalso(hablando=False)
        with mock.patch.object(motores, "MotorPrism", return_value=motor), \
                mock.patch.object(
                    prueba_voz.diagnostico, "crear_hilo",
                    side_effect=lambda target, nombre, **kw: _HiloInmediato(target)), \
                mock.patch.object(prueba_voz, "VIDA_PRUEBA_VOZ", 0.01):
            prueba = prueba_voz.PruebaVoz()
            prueba.probar_prism("sapi", 0, 50, 50, 50)

        self.assertEqual(motor.cerrado, 1)
        self.assertEqual(motor.consultas_hablando, 0)

    def test_motor_no_disponible_anuncia_con_call_after(self):
        with mock.patch.object(
                motores, "MotorPrism",
                side_effect=motores.MotorNoDisponible("no")), \
                mock.patch.object(
                    prueba_voz.diagnostico, "crear_hilo",
                    side_effect=lambda target, nombre, **kw: _HiloInmediato(target)), \
                mock.patch.object(prueba_voz.wx, "CallAfter") as call_after, \
                mock.patch.object(prueba_voz, "anunciar") as anunciar:
            prueba = prueba_voz.PruebaVoz()
            prueba.probar_prism("sapi", 0, 50, 50, 50)

        call_after.assert_called_once_with(
            anunciar, "No se pudo iniciar el motor de voz elegido.")


class TestProbarElevenLabs(unittest.TestCase):

    def test_cierra_el_motor_y_libera_la_marca(self):
        motor = _MotorElevenFalso()
        anunciar = mock.Mock()
        with mock.patch.object(
                prueba_voz.wx, "CallAfter",
                side_effect=lambda funcion, *args: funcion(*args)), \
                mock.patch.object(
                    prueba_voz.diagnostico, "crear_hilo",
                    side_effect=lambda target, nombre, **kw: _HiloInmediato(target)), \
                mock.patch.object(
                    motor_elevenlabs, "MotorElevenLabs", return_value=motor), \
                mock.patch.object(escala_voz, "resolver_voz", return_value=0), \
                mock.patch.object(prueba_voz, "anunciar", anunciar):
            prueba = prueba_voz.PruebaVoz()
            prueba.probar_elevenlabs("clave", "Ana", 60, 70)

        self.assertEqual(motor.dicho, "Así suena esta voz.")
        self.assertEqual(motor.cerrado, 1)
        self.assertFalse(prueba._probando_eleven)
        anunciar.assert_not_called()

    def test_no_arranca_una_segunda_mientras_sigue_la_primera(self):
        prueba = prueba_voz.PruebaVoz()
        with mock.patch.object(
                prueba_voz.diagnostico, "crear_hilo",
                return_value=_HiloQuieto()) as crear:
            prueba.probar_elevenlabs("clave", "Ana", 60, 70)
            prueba.probar_elevenlabs("clave", "Ana", 60, 70)

        self.assertEqual(crear.call_count, 1)
        self.assertTrue(prueba._probando_eleven)

    def test_un_error_se_anuncia_con_su_texto(self):
        motor = _MotorElevenFalso(error=RuntimeError("falla de prueba"))
        anunciar = mock.Mock()
        with mock.patch.object(
                prueba_voz.wx, "CallAfter",
                side_effect=lambda funcion, *args: funcion(*args)), \
                mock.patch.object(
                    prueba_voz.diagnostico, "crear_hilo",
                    side_effect=lambda target, nombre, **kw: _HiloInmediato(target)), \
                mock.patch.object(
                    motor_elevenlabs, "MotorElevenLabs", return_value=motor), \
                mock.patch.object(escala_voz, "resolver_voz", return_value=0), \
                mock.patch.object(prueba_voz, "anunciar", anunciar):
            prueba = prueba_voz.PruebaVoz()
            prueba.probar_elevenlabs("clave", "Ana", 60, 70)

        anunciar.assert_called_once_with("falla de prueba")
        self.assertEqual(motor.cerrado, 1)
        self.assertFalse(prueba._probando_eleven)


class TestPseudoTextos(unittest.TestCase):
    """Bajo pseudotraducción, cada frase al usuario sale marcada."""

    def test_prism_habla_y_anuncia_marcado(self):
        motor = _MotorWindowsFalso()
        with con_pseudo():
            with mock.patch.object(motores, "MotorPrism", return_value=motor), \
                    mock.patch.object(
                        prueba_voz.diagnostico, "crear_hilo",
                        side_effect=lambda target, nombre, **kw: _HiloInmediato(target)), \
                    mock.patch.object(prueba_voz, "VIDA_PRUEBA_VOZ", 0.01):
                prueba = prueba_voz.PruebaVoz()
                prueba.probar_prism("sapi", 2, 60, 70, 40)
        self.assertTrue(motor.dicho.startswith("[¡"), motor.dicho)

    def test_prism_sin_motor_anuncia_marcado(self):
        with con_pseudo():
            with mock.patch.object(
                    motores, "MotorPrism",
                    side_effect=motores.MotorNoDisponible("no")), \
                    mock.patch.object(
                        prueba_voz.diagnostico, "crear_hilo",
                        side_effect=lambda target, nombre, **kw: _HiloInmediato(target)), \
                    mock.patch.object(
                        prueba_voz.wx, "CallAfter",
                        side_effect=lambda funcion, *args: funcion(*args)), \
                    mock.patch.object(prueba_voz, "anunciar") as anunciar:
                prueba = prueba_voz.PruebaVoz()
                prueba.probar_prism("sapi", 0, 50, 50, 50)
        anunciar.assert_called_once()
        self.assertTrue(anunciar.call_args.args[0].startswith("[¡"),
                        anunciar.call_args.args[0])


class TestCerrar(unittest.TestCase):

    def test_sin_prueba_en_curso_no_hace_nada(self):
        prueba = prueba_voz.PruebaVoz()
        prueba.cerrar()
        self.assertIsNone(prueba._corte_prism)

    def test_con_prueba_en_curso_la_corta(self):
        with mock.patch.object(
                prueba_voz.diagnostico, "crear_hilo",
                return_value=_HiloQuieto()):
            prueba = prueba_voz.PruebaVoz()
            prueba.probar_prism("sapi", 0, 50, 50, 50)
            corte = prueba._corte_prism
            prueba.cerrar()

        self.assertTrue(corte.is_set())
