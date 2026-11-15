# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Valores con los que arranca el estado del relevo del reproductor."""

import unittest

from guyrapu.player.estado_relevo import EstadoRelevo


class TestValoresIniciales(unittest.TestCase):

    def setUp(self):
        self.estado = EstadoRelevo()

    def test_ffmpeg_arranca_sin_relevo(self):
        self.assertIsNone(self.estado.ffmpeg)

    def test_gen_arranca_en_cero(self):
        self.assertEqual(self.estado.gen, 0)

    def test_fuentes_arrancan_vacias(self):
        self.assertIsNone(self.estado.fuentes)

    def test_desfase_arranca_en_cero(self):
        self.assertEqual(self.estado.desfase, 0)

    def test_ventana_arranca_sin_leer(self):
        self.assertIsNone(self.estado.ventana)

    def test_vod_base_ms_arranca_sin_base(self):
        self.assertIsNone(self.estado.vod_base_ms)

    def test_vod_ultima_arranca_sin_lectura(self):
        self.assertIsNone(self.estado.vod_ultima)

    def test_vod_recuperaciones_arranca_en_cero(self):
        self.assertEqual(self.estado.vod_recuperaciones, 0)

    def test_reintentos_arranca_en_cero(self):
        self.assertEqual(self.estado.reintentos, 0)

    def test_vod_reapertura_arranca_sin_agendar(self):
        self.assertIsNone(self.estado.vod_reapertura)

    def test_vod_destino_en_pausa_arranca_sin_salto(self):
        self.assertIsNone(self.estado.vod_destino_en_pausa)

    def test_directo_reapertura_arranca_sin_agendar(self):
        self.assertIsNone(self.estado.directo_reapertura)

    def test_vod_por_relevo_arranca_apagado(self):
        self.assertFalse(self.estado.vod_por_relevo)


if __name__ == "__main__":
    unittest.main()
