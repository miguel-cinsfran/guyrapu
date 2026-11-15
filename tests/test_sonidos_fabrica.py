# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Migración de los sonidos opcionales a la configuración de cada usuario.

Corre sobre archivos reales en una carpeta temporal: `config.ini` y
`sounds.ini` se leen y se escriben por el mismo cableado que usa la app.
"""

import configparser
import tempfile
import unittest
from pathlib import Path

from guyrapu.core import config, sonidos_ini
from tests.rutas_temporales import redirigir_rutas

SONIDOS_BASE = "[sonidos]\nactivar = true\n"


class TestMigracion(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.raiz = Path(self._tmp.name)

    def _cargar(self, config_texto, sounds_texto=None):
        (self.raiz / "config.ini").write_text(config_texto, encoding="utf-8")
        if sounds_texto is not None:
            (self.raiz / "sounds.ini").write_text(sounds_texto, encoding="utf-8")
        with redirigir_rutas(self.raiz):
            config.cargar_configuracion()

    def _sounds(self):
        return self.raiz / "sounds.ini"

    def _callados(self):
        return sonidos_ini.silenciados(
            self._sounds().read_text(encoding="utf-8"))

    def _version(self):
        p = configparser.ConfigParser(interpolation=None)
        p.read(self.raiz / "config.ini", encoding="utf-8")
        return p.getint("sesion", "version_sonidos")

    def test_sonido_tema_falso_calla_musica_tema(self):
        self._cargar("[musica]\nsonido_tema = false\n", SONIDOS_BASE)
        callados = self._callados()
        self.assertIn("musica_tema", callados)
        self.assertNotIn("musica_fin", callados)
        self.assertEqual(self._version(), 1)

    def test_sonido_tema_verdadero_no_toca_sounds_ini(self):
        self._cargar("[musica]\nsonido_tema = true\n", SONIDOS_BASE)
        self.assertEqual(self._sounds().read_text(encoding="utf-8"),
                         SONIDOS_BASE)
        self.assertEqual(self._version(), 1)

    def test_sin_sonido_tema_no_toca_sounds_ini(self):
        self._cargar("[musica]\nvolumen = 80\n", SONIDOS_BASE)
        self.assertEqual(self._sounds().read_text(encoding="utf-8"),
                         SONIDOS_BASE)
        self.assertEqual(self._version(), 1)

    def test_con_la_version_al_dia_no_se_repite(self):
        self._cargar(
            "[sesion]\nversion_sonidos = 1\n"
            "[musica]\nsonido_tema = false\n",
            SONIDOS_BASE)
        self.assertEqual(self._sounds().read_text(encoding="utf-8"),
                         SONIDOS_BASE)
        self.assertEqual(self._version(), 1)

    def test_sin_sounds_ini_no_lo_crea(self):
        self._cargar("[musica]\nsonido_tema = false\n")
        self.assertFalse(self._sounds().exists())
        self.assertEqual(self._version(), 1)

    def test_conserva_lo_ya_callado_y_no_toca_musica_fin(self):
        original = (SONIDOS_BASE + "copiar =\nmusica_fin =\n"
                    "musica_fallo = C:/sonidos/fallo.wav\n")
        self._cargar("[musica]\nsonido_tema = false\n", original)
        callados = self._callados()
        self.assertIn("musica_tema", callados)
        self.assertIn("copiar", callados)
        self.assertIn("musica_fin", callados)
        self.assertNotIn("musica_fallo", callados)
        texto = self._sounds().read_text(encoding="utf-8")
        self.assertEqual(texto.count("musica_fin ="), 1)


if __name__ == "__main__":
    unittest.main()
