# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas del perfil de prueba del carril de NVDA, sin tocar NVDA."""

import configparser
import tempfile
import unittest
from pathlib import Path

from qa.nvda import perfil


class TestRutas(unittest.TestCase):

    def test_el_perfil_y_la_copia_viven_bajo_la_carpeta_del_carril(self):
        perfil_armado = perfil.ruta_perfil("C:/Local")
        copia = perfil.ruta_portatil("2026.3.1", "C:/Local")
        self.assertEqual(perfil_armado, Path("C:/Local/guyrapu-qa/perfil-nvda"))
        self.assertEqual(copia, Path("C:/Local/guyrapu-qa/nvda-2026.3.1"))

    def test_el_registro_de_nvda_vive_dentro_del_perfil(self):
        self.assertEqual(
            perfil.ruta_registro("C:/Local"),
            Path("C:/Local/guyrapu-qa/perfil-nvda/nvda.log"))

    def test_la_marca_del_fin_limpio_vive_en_la_carpeta_del_carril(self):
        self.assertEqual(
            perfil.ruta_fin_limpio("C:/Local"),
            Path("C:/Local/guyrapu-qa/fin-limpio.txt"))

    def test_la_version_fijada_es_la_del_archivo(self):
        self.assertEqual(perfil.version_esperada(), "2026.3.1")


class TestPerfilSeguro(unittest.TestCase):

    def test_se_niega_con_la_carpeta_de_configuracion_real(self):
        with tempfile.TemporaryDirectory() as base:
            with self.assertRaises(ValueError):
                perfil.perfil_seguro(Path(base) / "nvda", appdata=base)

    def test_se_niega_dentro_de_la_carpeta_de_configuracion_real(self):
        with tempfile.TemporaryDirectory() as base:
            destino = Path(base) / "nvda" / "perfil-nvda"
            with self.assertRaises(ValueError):
                perfil.perfil_seguro(destino, appdata=base)

    def test_acepta_la_carpeta_del_carril(self):
        with tempfile.TemporaryDirectory() as base:
            destino = Path(base) / "guyrapu-qa" / "perfil-nvda"
            self.assertEqual(perfil.perfil_seguro(destino, appdata=base),
                             destino)


class TestContenidoIni(unittest.TestCase):

    def test_trae_las_claves_que_apagan_lo_que_estorba(self):
        ini = perfil.contenido_ini()
        for linea in (
                "language = es",
                "synth = espia_guyrapu",
                "showWelcomeDialogAtStartup = False",
                "playStartAndExitSounds = False",
                "autoCheck = False",
                "startupNotification = False",
                "askedAllowUsageStats = True",
                "enableMouseTracking = False",
                "progressBarOutputMode = off",
                "unicodeNormalization = DISABLED",
                "enableScratchpadDir = True"):
            self.assertIn(linea, ini)


class TestArmarPerfil(unittest.TestCase):

    def test_copia_la_carpeta_dentro_al_borrador(self):
        with tempfile.TemporaryDirectory() as base:
            origen = Path(base) / "dentro"
            (origen / "globalPlugins").mkdir(parents=True)
            (origen / "synthDrivers").mkdir(parents=True)
            (origen / "globalPlugins" / "pieza.py").write_text(
                "x = 1\n", encoding="utf-8")
            (origen / "synthDrivers" / "espia.py").write_text(
                "x = 2\n", encoding="utf-8")
            destino = Path(base) / "carril" / "perfil-nvda"
            perfil.armar_perfil(destino, origen, appdata=base)
            self.assertTrue(
                (destino / "scratchpad" / "globalPlugins" / "pieza.py")
                .is_file())
            self.assertTrue(
                (destino / "scratchpad" / "synthDrivers" / "espia.py")
                .is_file())
            self.assertIn("enableScratchpadDir = True",
                          (destino / "nvda.ini").read_text(encoding="utf-8"))

    def test_arma_de_cero_y_no_deja_restos_de_la_corrida_anterior(self):
        with tempfile.TemporaryDirectory() as base:
            origen = Path(base) / "dentro"
            origen.mkdir()
            destino = Path(base) / "carril" / "perfil-nvda"
            destino.mkdir(parents=True)
            (destino / "carril.json").write_text("viejo", encoding="utf-8")
            perfil.armar_perfil(destino, origen, appdata=base)
            self.assertFalse((destino / "carril.json").exists())
            self.assertTrue((destino / "nvda.ini").is_file())

    def test_el_ini_generado_apaga_la_lectura_automatica_al_cargar_pagina(self):
        with tempfile.TemporaryDirectory() as base:
            origen = Path(base) / "dentro"
            origen.mkdir()
            destino = Path(base) / "carril" / "perfil-nvda"
            perfil.armar_perfil(destino, origen, appdata=base)
            texto = (destino / "nvda.ini").read_text(encoding="utf-8")
            ini = configparser.ConfigParser(interpolation=None)
            ini.read_string("[nvda]\n" + texto)
            self.assertFalse(ini.getboolean("virtualBuffers",
                                            "autoSayAllOnPageLoad"))

    def test_no_toca_la_configuracion_real_aunque_se_lo_pidan(self):
        with tempfile.TemporaryDirectory() as base:
            origen = Path(base) / "dentro"
            origen.mkdir()
            with self.assertRaises(ValueError):
                perfil.armar_perfil(Path(base) / "nvda", origen,
                                    appdata=base)
            self.assertFalse((Path(base) / "nvda").exists())
