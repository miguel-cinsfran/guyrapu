# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Migración de los sonidos opcionales a la configuración de cada usuario.

Corre sobre archivos reales en una carpeta temporal: `config.ini` y
`sounds.ini` se leen y se escriben por el mismo cableado que usa la app.
"""

import configparser
import importlib
import tempfile
import unittest
from pathlib import Path

from guyrapu.core import (config, eventos_sonido, motivos_sonido,
                          sonidos_fabrica, sonidos_ini)
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


class TestTextoDeFabrica(unittest.TestCase):
    """El texto de respaldo se arma desde el catálogo, no a mano."""

    def _lineas_de_archivos(self):
        lineas = sonidos_fabrica.TEXTO_FABRICA.splitlines()
        inicio = lineas.index("# Archivos de fábrica:") + 1
        return [linea for linea in lineas[inicio:]
                if linea.startswith("# ") and "vienen callados" not in linea]

    def test_la_lista_sigue_el_orden_del_catalogo(self):
        nombres = [nombre for linea in self._lineas_de_archivos()
                   for nombre in linea[2:].split(", ")]
        propios = [evento for evento in eventos_sonido.EVENTOS
                   if evento not in eventos_sonido.SONIDOS]
        self.assertEqual(nombres, propios)

    def test_ninguna_linea_de_archivos_pasa_de_cien_caracteres(self):
        for linea in self._lineas_de_archivos():
            with self.subTest(linea=linea):
                self.assertLessEqual(len(linea), 100)

    def test_el_texto_sigue_al_catalogo_si_agrega_un_evento(self):
        original = eventos_sonido.EVENTOS
        try:
            eventos_sonido.EVENTOS = original + ["archivo_nuevo"]
            importlib.reload(sonidos_fabrica)
            nombres = [nombre for linea in self._lineas_de_archivos()
                       for nombre in linea[2:].split(", ")]
            self.assertIn("archivo_nuevo", nombres)
        finally:
            eventos_sonido.EVENTOS = original
            importlib.reload(sonidos_fabrica)

    def test_los_callados_salen_de_los_opcionales(self):
        self.assertEqual(
            sonidos_ini.silenciados(sonidos_fabrica.TEXTO_FABRICA),
            set(motivos_sonido.MOTIVOS["opcional"]))
        original = motivos_sonido.MOTIVOS["opcional"]
        try:
            motivos_sonido.MOTIVOS["opcional"] = original + ("opcional_nuevo",)
            importlib.reload(sonidos_fabrica)
            self.assertEqual(
                sonidos_ini.silenciados(sonidos_fabrica.TEXTO_FABRICA),
                set(motivos_sonido.MOTIVOS["opcional"]))
            linea = next(linea for linea in sonidos_fabrica.TEXTO_FABRICA.splitlines()
                         if "vienen callados" in linea)
            self.assertIn("alerta_en_video y opcional_nuevo vienen callados",
                          linea)
        finally:
            motivos_sonido.MOTIVOS["opcional"] = original
            importlib.reload(sonidos_fabrica)

    def test_el_resto_del_texto_no_cambia(self):
        texto = sonidos_fabrica.TEXTO_FABRICA
        self.assertEqual(texto.splitlines()[:6], [
            "[sonidos]",
            "volumen = 0.7",
            "# Tema: carpeta en sounds/themes/ con un WAV por sonido y, si hace falta, uno",
            "# con el nombre de un evento. Copia default a mi_tema y pon: tema = mi_tema",
            "tema = default",
            "# Archivos de fábrica:",
        ])
        self.assertIn("vienen callados: se activan en Preferencias, Sonidos.",
                      texto)
        self.assertTrue(texto.endswith("\n"))


if __name__ == "__main__":
    unittest.main()
