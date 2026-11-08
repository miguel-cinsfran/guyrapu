# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de la lectura de codificadores en el registro de OBS."""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from guyrapu.core import paths
from guyrapu.obs.codificadores_obs import (
    codificador_simple,
    codificadores_disponibles,
    leer_codificadores,
)

REGISTRO_DE_LA_OFICINA = """\
10:55:13.695: [obs-websocket] Server started successfully on port 4455.
10:55:13.696: ---------------------------------
10:55:13.696: Available Encoders:
10:55:13.696:   Video Encoders:
10:55:13.696: \t- ffmpeg_svt_av1 (SVT-AV1)
10:55:13.696: \t- ffmpeg_aom_av1 (AOM AV1)
10:55:13.696: \t- obs_qsv11_v2 (QuickSync H.264)
10:55:13.696: \t- obs_qsv11_hevc (QuickSync HEVC)
10:55:13.696: \t- obs_x264 (x264)
10:55:13.696:   Audio Encoders:
10:55:13.696: \t- ffmpeg_aac (FFmpeg AAC)
10:55:13.696: \t- ffmpeg_opus (FFmpeg Opus)
10:55:13.696: ---------------------------------
"""


class TestLeerCodificadores(unittest.TestCase):

    def test_registro_de_la_oficina_solo_deja_h264(self):
        self.assertEqual(leer_codificadores(REGISTRO_DE_LA_OFICINA),
                         ("qsv", "x264"))

    def test_registro_con_todos_los_h264_los_ordena_por_prioridad(self):
        registro = REGISTRO_DE_LA_OFICINA.replace(
            "10:55:13.696:   Audio Encoders:",
            "10:55:13.696: \t- obs_nvenc_h264_tex (NVIDIA NVENC H.264)\n"
            "10:55:13.696: \t- h264_texture_amf (AMD HW H.264)\n"
            "10:55:13.696:   Audio Encoders:")
        self.assertEqual(leer_codificadores(registro),
                         ("nvenc", "qsv", "amd", "x264"))

    def test_registro_sin_bloque_solo_deja_x264(self):
        self.assertEqual(leer_codificadores("OBS arrancó sin más."),
                         ("x264",))
        self.assertEqual(leer_codificadores(""), ("x264",))

    def test_registro_sin_h264_solo_deja_x264(self):
        registro = (
            "Available Encoders:\n"
            "  Video Encoders:\n"
            "\t- obs_qsv11_hevc (QuickSync HEVC)\n"
            "\t- ffmpeg_svt_av1 (SVT-AV1)\n"
            "  Audio Encoders:\n")
        self.assertEqual(leer_codificadores(registro), ("x264",))

    def test_no_confunde_los_audio(self):
        registro = REGISTRO_DE_LA_OFICINA.replace(
            "  Audio Encoders:",
            "  Audio Encoders:\n\t- obs_x264 (no es un codificador de audio)")
        # La línea de audio no se mira: x264 ya venía del bloque de vídeo.
        self.assertEqual(leer_codificadores(registro), ("qsv", "x264"))


class TestCodificadorSimple(unittest.TestCase):

    def test_tabla_de_equivalencias(self):
        casos = {
            "obs_x264": "x264",
            "obs_qsv11_v2": "qsv",
            "obs_qsv11": "qsv",
            "obs_nvenc_h264_tex": "nvenc",
            "jim_nvenc": "nvenc",
            "ffmpeg_nvenc": "nvenc",
            "h264_texture_amf": "amd",
            "amd_amf_h264": "amd",
        }
        for identificador, simple in casos.items():
            with self.subTest(identificador=identificador):
                self.assertEqual(codificador_simple(identificador), simple)

    def test_desconocido_deja_x264(self):
        self.assertEqual(codificador_simple("obs_otro"), "x264")
        self.assertEqual(codificador_simple(None), "x264")
        self.assertEqual(codificador_simple(""), "x264")


class TestUltimoRegistro(unittest.TestCase):

    def test_lee_el_registro_mas_reciente_de_la_carpeta(self):
        with tempfile.TemporaryDirectory() as tmp:
            carpeta = Path(tmp)
            (carpeta / "2026-11-07 10-00-00.txt").write_text(
                "Available Encoders:\n  Video Encoders:\n"
                "\t- obs_qsv11_v2 (QuickSync H.264)\n  Audio Encoders:\n",
                encoding="utf-8")
            (carpeta / "2026-11-08 10-00-00.txt").write_text(
                "Available Encoders:\n  Video Encoders:\n"
                "\t- obs_nvenc_h264_tex (NVIDIA NVENC H.264)\n"
                "  Audio Encoders:\n", encoding="utf-8")
            self.assertEqual(codificadores_disponibles(carpeta), ("nvenc",))

    def test_carpeta_por_defecto_sale_de_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            carpeta = Path(tmp)
            (carpeta / "2026-11-08 10-00-00.txt").write_text(
                REGISTRO_DE_LA_OFICINA, encoding="utf-8")
            with mock.patch.object(paths, "carpeta_obs",
                                   return_value=carpeta):
                self.assertEqual(codificadores_disponibles(),
                                 ("qsv", "x264"))

    def test_sin_registro_legible_solo_deja_x264(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(codificadores_disponibles(Path(tmp) / "no-existe"),
                             ("x264",))
            carpeta = Path(tmp)
            (carpeta / "2026-11-08 10-00-00.txt").write_text(
                "sin bloque de codificadores", encoding="utf-8")
            self.assertEqual(codificadores_disponibles(carpeta), ("x264",))

    def test_un_registro_ilegible_no_rompe(self):
        with tempfile.TemporaryDirectory() as tmp:
            carpeta = Path(tmp)
            (carpeta / "2026-11-08 10-00-00.txt").write_bytes(
                b"\xff\xfe\x00basura")
            self.assertEqual(codificadores_disponibles(carpeta), ("x264",))


if __name__ == "__main__":
    unittest.main()
