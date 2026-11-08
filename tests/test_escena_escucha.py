# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas del hilo que devuelve la monitorización al cerrar el panel."""

import unittest
from unittest import mock

from guyrapu.ui import escena_escucha


class _CasillaFalsa:

    def Bind(self, evento, manejador):
        pass


class TestAlCerrar(unittest.TestCase):

    def _control_activo(self):
        control = escena_escucha.ControlEscucha(
            _CasillaFalsa(), None, None, None)
        control.activa = True
        control._fuente = "Mic/Aux"
        control._anterior = "OBS_MONITORING_TYPE_NONE"
        return control

    def test_crea_un_hilo_daemon_que_restaura(self):
        control = self._control_activo()
        restaurar = mock.Mock()
        hilos = []
        original = escena_escucha.diagnostico.crear_hilo

        def registrar(target, nombre, **kw):
            hilo = original(target, nombre, **kw)
            hilos.append(hilo)
            return hilo

        with mock.patch.object(
                escena_escucha.escucha_microfono, "restaurar", restaurar), \
                mock.patch.object(
                    escena_escucha.diagnostico, "crear_hilo",
                    side_effect=registrar):
            control.al_cerrar()

        self.assertEqual(len(hilos), 1)
        hilo = hilos[0]
        hilo.join(2)
        self.assertEqual(hilo.name, "RestaurarEscucha")
        self.assertTrue(hilo.daemon)
        restaurar.assert_called_once_with(
            "Mic/Aux", "OBS_MONITORING_TYPE_NONE")

    def test_sin_escucha_activa_no_crea_hilo(self):
        control = escena_escucha.ControlEscucha(
            _CasillaFalsa(), None, None, None)

        with mock.patch.object(
                escena_escucha.diagnostico, "crear_hilo") as crear:
            control.al_cerrar()

        crear.assert_not_called()
