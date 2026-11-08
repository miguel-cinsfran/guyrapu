# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de `guyrapu/obs/perfil_por_uso.py`, sin OBS ni config.ini real."""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from guyrapu.core import plataformas
from guyrapu.obs import perfil_por_uso


class TestPerfilPorUso(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.ruta = Path(self.tmp.name) / "config.ini"

    def _escribir(self, horizontal, vertical):
        self.ruta.write_text(
            "[transmision]\n"
            f"perfil_horizontal = {horizontal}\n"
            f"perfil_vertical = {vertical}\n",
            encoding="utf-8")

    def test_cada_orientacion_lee_su_perfil(self):
        self._escribir("Mi horizontal", "Mi vertical")
        self.assertEqual(
            perfil_por_uso.perfil_elegido("YouTube", self.ruta),
            "Mi horizontal")
        self.assertEqual(
            perfil_por_uso.perfil_elegido("TikTok", self.ruta),
            "Mi vertical")

    def test_sin_archivo_usa_los_de_fabrica(self):
        ruta = Path(self.tmp.name) / "no-existe.ini"
        self.assertEqual(
            perfil_por_uso.perfil_elegido("YouTube", ruta), "YouTube")
        self.assertEqual(
            perfil_por_uso.perfil_elegido("TikTok", ruta), "TikTok")

    def test_vacio_significa_no_cambiar_de_perfil(self):
        self._escribir("", "")
        self.assertEqual(
            perfil_por_uso.perfil_elegido("YouTube", self.ruta), "")
        self.assertEqual(
            perfil_por_uso.perfil_elegido("TikTok", self.ruta), "")

    def test_plataforma_desconocida_no_tiene_perfil(self):
        self._escribir("Mi horizontal", "Mi vertical")
        self.assertIsNone(
            perfil_por_uso.perfil_elegido("Restream", self.ruta))
        self.assertIsNone(perfil_por_uso.perfil_elegido("", self.ruta))

    def test_la_orientacion_sale_del_registro_no_del_nombre(self):
        self._escribir("Mi horizontal", "Mi vertical")
        nueva = plataformas.Plataforma(
            "twitch", "Twitch", "mensaje_nuevo", False, "vertical")
        with mock.patch.dict(plataformas.PLATAFORMAS, {"twitch": nueva}):
            self.assertEqual(
                perfil_por_uso.perfil_elegido("Twitch", self.ruta),
                "Mi vertical")


if __name__ == "__main__":
    unittest.main()
