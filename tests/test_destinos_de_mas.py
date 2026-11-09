# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de los destinos de Restream que sobran para un directo de TikTok."""

from types import SimpleNamespace
import unittest

from guyrapu.restream import destinos_de_mas


def _canal(plataforma, nombre, activo=True):
    return SimpleNamespace(plataforma=plataforma, nombre=nombre, activo=activo)


class DeMasTest(unittest.TestCase):
    def test_descarta_los_apagados_y_los_de_tiktok_y_conserva_el_orden(self):
        canales = [
            _canal("YouTube", "Canal"),
            _canal("TikTok", "Cuenta"),
            _canal("Twitch", "Canal", activo=False),
            _canal("Facebook", "Página"),
        ]
        self.assertEqual(
            [canal.nombre for canal in destinos_de_mas.de_mas(canales)],
            ["Canal", "Página"])

    def test_sin_canales_devuelve_vacio(self):
        self.assertEqual(destinos_de_mas.de_mas(()), ())
        self.assertEqual(destinos_de_mas.de_mas(None), ())

    def test_el_mensaje_nombra_cada_destino_como_plataforma_y_nombre(self):
        canales = [_canal("YouTube", "Mi canal"),
                   _canal("Facebook", "Mi página")]
        texto = destinos_de_mas.mensaje(canales)
        self.assertIn("YouTube (Mi canal), Facebook (Mi página)", texto)
        self.assertTrue(texto.startswith(
            "Restream también va a transmitir este directo a: "))
        self.assertTrue(texto.endswith("¿Transmitir igual?"))


if __name__ == "__main__":
    unittest.main()
