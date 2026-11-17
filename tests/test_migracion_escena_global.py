# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Migración que enciende una sola vez los atajos de escena fuera de la app.

Corre la carga entera de `config.ini` en una carpeta temporal: la migración
se prueba por el mismo cableado que usa la aplicación.
"""

import configparser
import tempfile
import unittest
from pathlib import Path

from guyrapu.core import config
from tests.rutas_temporales import redirigir_rutas


class TestMigracionEscenaGlobal(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.raiz = Path(self._tmp.name)

    def _cargar(self, texto):
        (self.raiz / "config.ini").write_text(texto, encoding="utf-8")
        with redirigir_rutas(self.raiz):
            return config.cargar_configuracion()

    def _leer(self):
        parser = configparser.ConfigParser(interpolation=None)
        parser.read(self.raiz / "config.ini", encoding="utf-8")
        return parser

    def test_una_config_vieja_apagada_queda_encendida_y_con_marca(self):
        cfg = self._cargar(
            "[transmision]\nescena_atajos_globales = false\n")
        self.assertTrue(cfg["escena_atajos_globales"])
        parser = self._leer()
        self.assertTrue(
            parser.getboolean("transmision", "escena_atajos_globales"))
        self.assertEqual(parser.getint("sesion", "version_escena_global"), 1)

    def test_una_segunda_migracion_no_toca_lo_que_el_usuario_apago(self):
        self._cargar("[transmision]\nescena_atajos_globales = false\n")
        config.guardar_opcion(self.raiz / "config.ini", "transmision",
                              "escena_atajos_globales", "false")
        with redirigir_rutas(self.raiz):
            cfg = config.cargar_configuracion()
        self.assertFalse(cfg["escena_atajos_globales"])
        self.assertFalse(
            self._leer().getboolean("transmision", "escena_atajos_globales"))


if __name__ == "__main__":
    unittest.main()
