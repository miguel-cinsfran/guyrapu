# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas del fotograma del reproductor como captura para la IA.

Sin ventanas: un doble hace de reproductor de libVLC.
"""

import unittest
from unittest import mock

from guyrapu.obs import obs_captura_ia
from guyrapu.player import fotograma_video
from guyrapu.ui import ia_captura_video as captura_video


def _reproductor(con_video=True):
    reproductor = mock.Mock()
    reproductor.has_vout.return_value = 1 if con_video else 0
    return reproductor


class TestConFotograma(unittest.TestCase):

    def setUp(self):
        self.opciones = (obs_captura_ia.OpcionCaptura(
            "Escena", "Escena actual: Escena", 1280, 720),)

    def test_sin_video_no_agrega_la_opcion(self):
        self.assertEqual(
            captura_video.con_fotograma(self.opciones, _reproductor(False)),
            self.opciones)

    def test_sin_reproductor_no_agrega_la_opcion(self):
        self.assertEqual(
            captura_video.con_fotograma(self.opciones, None), self.opciones)

    def test_con_video_agrega_la_opcion_al_final(self):
        resultado = captura_video.con_fotograma(self.opciones, _reproductor())
        self.assertEqual(len(resultado), 2)
        self.assertIs(resultado[0], self.opciones[0])
        self.assertEqual(resultado[-1].fuente, "Fotograma del vídeo")
        self.assertEqual(resultado[-1].etiqueta, "Fotograma del vídeo")


class TestCapturaDelFotograma(unittest.TestCase):

    def setUp(self):
        self.cliente = mock.Mock()
        self.reproductor = _reproductor()
        self.opcion = captura_video.con_fotograma((), self.reproductor)[0]

    def test_la_opcion_del_fotograma_se_reconoce(self):
        self.assertTrue(captura_video.es_fotograma(self.opcion))
        self.assertFalse(captura_video.es_fotograma(
            obs_captura_ia.OpcionCaptura("Cámara", "Cámara", 640, 360)))

    def test_capturar_usa_el_reproductor_y_no_el_cliente(self):
        with mock.patch.object(captura_video.fotograma_video, "capturar",
                               return_value=(b"jpg", 640, 360)) as capturar, \
                mock.patch.object(captura_video.obs_captura_ia,
                                  "capturar") as capturar_obs:
            resultado = captura_video.capturar(
                self.cliente, self.opcion, self.reproductor)
        capturar.assert_called_once_with(self.reproductor)
        capturar_obs.assert_not_called()
        self.assertEqual(resultado, obs_captura_ia.Captura(
            b"jpg", 640, 360, None))

    def test_vista_previa_usa_el_reproductor_y_no_el_cliente(self):
        with mock.patch.object(captura_video.fotograma_video, "capturar",
                               return_value=(b"jpg", 640, 360)) as capturar, \
                mock.patch.object(captura_video.obs_captura_ia,
                                  "vista_previa") as vista_obs:
            jpeg = captura_video.vista_previa(
                self.cliente, self.opcion, self.reproductor)
        capturar.assert_called_once_with(self.reproductor)
        vista_obs.assert_not_called()
        self.assertEqual(jpeg, b"jpg")

    def test_otra_opcion_captura_con_obs(self):
        otra = obs_captura_ia.OpcionCaptura("Cámara", "Cámara", 640, 360)
        captura = obs_captura_ia.Captura(b"x", 640, 360, False)
        with mock.patch.object(captura_video.obs_captura_ia, "capturar",
                               return_value=captura) as capturar_obs, \
                mock.patch.object(captura_video.fotograma_video,
                                  "capturar") as capturar_video:
            resultado = captura_video.capturar(
                self.cliente, otra, self.reproductor)
        capturar_obs.assert_called_once_with(self.cliente, otra)
        capturar_video.assert_not_called()
        self.assertIs(resultado, captura)

    def test_otra_opcion_ve_la_previa_con_obs(self):
        otra = obs_captura_ia.OpcionCaptura("Cámara", "Cámara", 640, 360)
        with mock.patch.object(captura_video.obs_captura_ia, "vista_previa",
                               return_value=b"jpg") as vista_obs, \
                mock.patch.object(captura_video.fotograma_video,
                                  "capturar") as capturar_video:
            jpeg = captura_video.vista_previa(
                self.cliente, otra, self.reproductor)
        vista_obs.assert_called_once_with(self.cliente, otra)
        capturar_video.assert_not_called()
        self.assertEqual(jpeg, b"jpg")

    def test_fallo_del_fotograma_sale_como_captura_fallida(self):
        with mock.patch.object(captura_video.fotograma_video, "capturar",
                               side_effect=fotograma_video.FotogramaFallido(
                                   "sin fotograma")):
            with self.assertRaises(obs_captura_ia.CapturaFallida) as fallo:
                captura_video.capturar(
                    self.cliente, self.opcion, self.reproductor)
        self.assertEqual(str(fallo.exception),
                         "No se pudo capturar el fotograma del vídeo.")


if __name__ == "__main__":
    unittest.main()
