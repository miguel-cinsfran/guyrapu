# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Valores con los que arranca el estado del relevo del reproductor."""

import unittest
from unittest import mock

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


class TestTransiciones(unittest.TestCase):
    """Cada transición deja todos los campos como el tramo del panel que
    reemplaza. El estado arranca con valores distintos de los de fábrica
    para que también se note lo que no debe tocar."""

    def setUp(self):
        self.relevo = mock.Mock()
        self.reapertura_vod = mock.Mock()
        self.reapertura_directa = mock.Mock()
        self.estado = EstadoRelevo()
        self.estado.ffmpeg = self.relevo
        self.estado.gen = 7
        self.estado.fuentes = ("vídeo", "audio")
        self.estado.desfase = 3
        self.estado.ventana = (5.0, 720)
        self.estado.vod_base_ms = 1000
        self.estado.vod_ultima = 2000
        self.estado.vod_recuperaciones = 2
        self.estado.reintentos = 4
        self.estado.vod_reapertura = self.reapertura_vod
        self.estado.vod_destino_en_pausa = 5000
        self.estado.directo_reapertura = self.reapertura_directa
        self.estado.vod_por_relevo = True

    def _campos(self):
        return (
            self.estado.ffmpeg,
            self.estado.gen,
            self.estado.fuentes,
            self.estado.desfase,
            self.estado.ventana,
            self.estado.vod_base_ms,
            self.estado.vod_ultima,
            self.estado.vod_recuperaciones,
            self.estado.reintentos,
            self.estado.vod_reapertura,
            self.estado.vod_destino_en_pausa,
            self.estado.directo_reapertura,
            self.estado.vod_por_relevo,
        )

    def test_soltar_detiene_reaperturas_y_relevo_y_limpia_sus_campos(self):
        self.estado.soltar()

        self.assertEqual(self._campos(), (
            None, 7, ("vídeo", "audio"), 3, (5.0, 720), None, 2000, 2, 4,
            None, None, None, True))
        self.reapertura_vod.Stop.assert_called_once_with()
        self.reapertura_directa.Stop.assert_called_once_with()
        self.relevo.detener.assert_called_once_with()

    def test_detener_reapertura_vod_solo_la_detiene(self):
        self.estado.detener_reapertura_vod()

        self.assertEqual(self._campos(), (
            self.relevo, 7, ("vídeo", "audio"), 3, (5.0, 720), 1000, 2000,
            2, 4, self.reapertura_vod, 5000, self.reapertura_directa, True))
        self.reapertura_vod.Stop.assert_called_once_with()
        self.reapertura_directa.Stop.assert_not_called()
        self.relevo.detener.assert_not_called()

    def test_olvidar_vod_limpia_solo_lo_del_vod(self):
        self.estado.olvidar_vod()

        self.assertEqual(self._campos(), (
            self.relevo, 7, ("vídeo", "audio"), 3, (5.0, 720), 1000, None,
            0, 4, self.reapertura_vod, None, self.reapertura_directa, False))

    def test_al_detener_limpia_lo_que_queda_tras_soltar(self):
        # El panel llama a _detener_relevo_ffmpeg y después a al_detener.
        self.estado.soltar()
        self.estado.al_detener()

        self.assertEqual(self._campos(), (
            None, 7, None, 0, None, None, None, 0, 4, None, None, None,
            False))

    def test_nueva_generacion_sube_el_contador_y_lo_devuelve(self):
        self.assertEqual(self.estado.nueva_generacion(), 8)

        self.assertEqual(self._campos(), (
            self.relevo, 8, ("vídeo", "audio"), 3, (5.0, 720), 1000, 2000,
            2, 4, self.reapertura_vod, 5000, self.reapertura_directa, True))

    def test_adoptar_en_grabado_pone_base_y_ultima(self):
        nuevo = mock.Mock()
        self.estado.adoptar(nuevo, ("nuevo-vídeo", "nuevo-audio"),
                            inicio_ms=12345)

        self.assertEqual(self._campos(), (
            nuevo, 7, ("nuevo-vídeo", "nuevo-audio"), 0, (5.0, 720), 12345,
            12345, 2, 0, self.reapertura_vod, 5000,
            self.reapertura_directa, True))

    def test_adoptar_en_directo_aplica_desfase_y_deja_la_base_vacia(self):
        nuevo = mock.Mock()
        self.estado.adoptar(nuevo, ("nuevo-vídeo", "nuevo-audio"), desfase=2)

        self.assertEqual(self._campos(), (
            nuevo, 7, ("nuevo-vídeo", "nuevo-audio"), 2, (5.0, 720), None,
            2000, 2, 0, self.reapertura_vod, 5000,
            self.reapertura_directa, True))

    def test_fallo_al_arrancar_en_grabado_apaga_el_modo_vod(self):
        self.estado.fallo_al_arrancar(True)

        self.assertEqual(self._campos(), (
            None, 7, None, 0, (5.0, 720), None, 2000, 2, 4,
            self.reapertura_vod, 5000, self.reapertura_directa, False))

    def test_fallo_al_arrancar_en_directo_conserva_lo_del_vod(self):
        self.estado.fallo_al_arrancar(False)

        self.assertEqual(self._campos(), (
            None, 7, None, 0, (5.0, 720), 1000, 2000, 2, 4,
            self.reapertura_vod, 5000, self.reapertura_directa, True))


if __name__ == "__main__":
    unittest.main()
