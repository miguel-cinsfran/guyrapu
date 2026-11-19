# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Estado de la descarga de caché de vídeo del reproductor."""

import tempfile
import unittest
from pathlib import Path

from guyrapu.player.tarea_cache_video import EstadoCacheVideo, TareaCacheVideo


class TestValoresIniciales(unittest.TestCase):

    def setUp(self):
        self.estado = EstadoCacheVideo()

    def test_tarea_arranca_sin_descarga(self):
        self.assertIsNone(self.estado.tarea)

    def test_local_arranca_apagado(self):
        self.assertFalse(self.estado.local)


class TestTransiciones(unittest.TestCase):

    def setUp(self):
        self.destino = Path(tempfile.gettempdir()) / "VIDEO00001.mp4"
        self.estado = EstadoCacheVideo()
        self.estado.local = True
        self.vigente = self.estado.empezar("VIDEO00001", 3, self.destino)

    def test_empezar_cancela_la_anterior_y_guarda_la_nueva(self):
        nueva = self.estado.empezar("VIDEO00002", 4, self.destino)

        self.assertTrue(self.vigente.cancelacion.is_set())
        self.assertFalse(nueva.cancelacion.is_set())
        self.assertIs(self.estado.tarea, nueva)
        self.assertIs(nueva, self.estado.tarea)

    def test_recibir_con_la_vigente_la_suelta_y_devuelve_true(self):
        self.assertTrue(self.estado.recibir(self.vigente))

        self.assertIsNone(self.estado.tarea)
        self.assertTrue(self.estado.local)

    def test_recibir_con_otra_devuelve_false_y_no_toca_nada(self):
        otra = TareaCacheVideo("VIDEO00002", 4, self.destino)

        self.assertFalse(self.estado.recibir(otra))

        self.assertIs(self.estado.tarea, self.vigente)
        self.assertFalse(self.vigente.cancelacion.is_set())
        self.assertTrue(self.estado.local)

    def test_cancelar_cancela_suelta_y_apaga_local(self):
        self.estado.cancelar()

        self.assertTrue(self.vigente.cancelacion.is_set())
        self.assertIsNone(self.estado.tarea)
        self.assertFalse(self.estado.local)


if __name__ == "__main__":
    unittest.main()
