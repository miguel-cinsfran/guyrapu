# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas del caché en memoria de direcciones de audio (`cache_enlaces.py`).

Sin red y sin reloj: cada caso pasa el momento y la dirección que vence.
"""

import unittest

from guyrapu.music.cache_enlaces import CacheEnlaces, vencimiento


AHORA = 1000.0
SEIS_HORAS = 6 * 3600
CUATRO_MINUTOS = 4 * 60


def _direccion(segundos):
    """Dirección que vence dentro de `segundos` desde `AHORA`."""
    return (f"https://r1.googlevideo.com/videoplayback"
            f"?expire={int(AHORA + segundos)}&firma=abc")


class TestVencimiento(unittest.TestCase):

    def test_lee_el_expire_de_la_consulta(self):
        self.assertEqual(
            vencimiento("https://x/videoplayback?expire=1800000000&a=1"),
            1800000000)

    def test_sin_expire_da_none(self):
        self.assertIsNone(vencimiento("https://x/videoplayback?a=1"))

    def test_expire_que_no_es_numero_da_none(self):
        self.assertIsNone(vencimiento("https://x/videoplayback?expire=abc"))


class TestCacheEnlaces(unittest.TestCase):

    def test_da_la_direccion_que_todavia_vale(self):
        cache = CacheEnlaces()
        url = _direccion(SEIS_HORAS)
        cache.guardar("uno", url, CUATRO_MINUTOS)
        self.assertEqual(cache.buscar("uno", AHORA), url)

    def test_descarta_la_que_vence_pronto(self):
        cache = CacheEnlaces()
        cache.guardar("uno", _direccion(12 * 60), CUATRO_MINUTOS)
        self.assertIsNone(cache.buscar("uno", AHORA))

    def test_pasar_el_tope_deja_fuera_la_que_se_guardo_primero(self):
        cache = CacheEnlaces(tope=2)
        for video_id in ("uno", "dos", "tres"):
            cache.guardar(video_id, _direccion(SEIS_HORAS), CUATRO_MINUTOS)
        self.assertIsNone(cache.buscar("uno", AHORA))
        self.assertIsNotNone(cache.buscar("dos", AHORA))
        self.assertIsNotNone(cache.buscar("tres", AHORA))


if __name__ == "__main__":
    unittest.main()
