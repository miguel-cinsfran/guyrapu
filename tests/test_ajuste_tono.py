# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas del ajuste del tono de la voz principal desde el teclado."""

import unittest
from types import SimpleNamespace
from unittest import mock

from guyrapu.core import anuncio_ajuste
from guyrapu.ui import ajuste_tono


class WorkerFalso:
    def __init__(self, motor="sapi", tono=50):
        self._motor = motor
        self._tono = tono
        self.cambiado = None

    def motor_activo(self):
        return self._motor

    def get_tono(self):
        return self._tono

    def cambiar_tono(self, valor):
        self.cambiado = valor


class TestAjustarTono(unittest.TestCase):

    def setUp(self):
        parche = mock.patch.object(anuncio_ajuste, "COMPARTIDO",
                                   anuncio_ajuste.AnuncioAjuste())
        parche.start()
        self.addCleanup(parche.stop)

    def _ajustar(self, tono=50, delta=5, motor="sapi"):
        frame = SimpleNamespace(_worker=WorkerFalso(motor, tono))
        with mock.patch.object(ajuste_tono, "guardar_opcion") as guardar, \
                mock.patch.object(ajuste_tono, "anunciar") as anunciar:
            ajuste_tono.ajustar_tono(frame, delta)
        return frame._worker, guardar, anunciar

    def test_sube_cinco_lo_guarda_y_lo_anuncia(self):
        worker, guardar, anunciar = self._ajustar(tono=50, delta=5)
        self.assertEqual(worker.cambiado, 55)
        guardar.assert_called_once_with(
            ajuste_tono.paths.config_ini(), "voz", "tono", "55")
        anunciar.assert_called_once_with("Tono de la voz: 55")

    def test_en_el_maximo_queda_en_cien_y_anuncia_el_limite(self):
        worker, guardar, anunciar = self._ajustar(tono=100, delta=5)
        self.assertEqual(worker.cambiado, 100)
        guardar.assert_called_once_with(
            ajuste_tono.paths.config_ini(), "voz", "tono", "100")
        anunciar.assert_called_once_with("Tono de la voz: 100, máximo")

    def test_en_el_minimo_queda_en_cero_y_anuncia_el_limite(self):
        worker, guardar, anunciar = self._ajustar(tono=0, delta=-5)
        self.assertEqual(worker.cambiado, 0)
        guardar.assert_called_once_with(
            ajuste_tono.paths.config_ini(), "voz", "tono", "0")
        anunciar.assert_called_once_with("Tono de la voz: 0, mínimo")

    def test_elevenlabs_no_cambia_nada_y_avisa(self):
        worker, guardar, anunciar = self._ajustar(motor="elevenlabs")
        self.assertIsNone(worker.cambiado)
        guardar.assert_not_called()
        anunciar.assert_called_once_with(
            "ElevenLabs no permite cambiar el tono.")


if __name__ == "__main__":
    unittest.main()
