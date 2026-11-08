# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de los ajustes de un perfil de OBS en modo Sencillo."""

import dataclasses
import unittest

from guyrapu.obs.ajustes_perfil import (
    BITRATES_AUDIO,
    CALIDADES_GRABACION,
    CANALES,
    FORMATOS_GRABACION,
    FPS_VALIDOS,
    MUESTREOS,
    PRESETS,
    AjustesPerfil,
    clave_preset,
    mejor_codificador,
    par,
    parametros_obs,
    preset_intermedio,
    validar,
    valores_iniciales,
)


def de_prueba(**cambios):
    return dataclasses.replace(valores_iniciales(False, "x264"), **cambios)


class TestTipo(unittest.TestCase):

    def test_tiene_los_ajustes_del_perfil(self):
        nombres = {campo.name for campo in dataclasses.fields(AjustesPerfil)}
        self.assertEqual(nombres, {
            "ancho_lienzo", "alto_lienzo", "ancho_salida", "alto_salida",
            "fps", "servidor", "clave", "codificador", "bitrate_video",
            "bitrate_audio", "preset", "bitrate_dinamico", "reconectar",
            "espera_reconexion", "reintentos", "carpeta_grabacion",
            "formato_grabacion", "calidad_grabacion", "buffer_clips",
            "segundos_buffer", "muestreo", "canales"})


class TestValoresPermitidos(unittest.TestCase):

    def test_listas(self):
        self.assertEqual(FPS_VALIDOS, (20, 24, 25, 30, 48, 50, 60))
        self.assertEqual(BITRATES_AUDIO,
                         (64, 96, 128, 160, 192, 256, 320))
        self.assertEqual(FORMATOS_GRABACION,
                         ("mkv", "mp4", "hybrid_mp4", "mov", "flv"))
        self.assertEqual(CALIDADES_GRABACION,
                         ("Stream", "Small", "HQ", "Lossless"))
        self.assertEqual(MUESTREOS, (44100, 48000))
        self.assertEqual(CANALES, ("Mono", "Stereo"))

    def test_presets_por_codificador(self):
        self.assertEqual(PRESETS["x264"], (
            "ultrafast", "superfast", "veryfast", "faster", "fast", "medium"))
        self.assertEqual(PRESETS["qsv"], ("speed", "balanced", "quality"))
        self.assertEqual(PRESETS["amd"], ("speed", "balanced", "quality"))
        self.assertEqual(PRESETS["nvenc"],
                         ("p1", "p2", "p3", "p4", "p5", "p6", "p7"))

    def test_clave_de_preset(self):
        self.assertEqual(clave_preset("x264"), "Preset")
        self.assertEqual(clave_preset("qsv"), "QSVPreset")
        self.assertEqual(clave_preset("nvenc"), "NVENCPreset2")
        self.assertEqual(clave_preset("amd"), "AMDPreset")

    def test_preset_intermedio(self):
        self.assertEqual(preset_intermedio("x264"), "veryfast")
        self.assertEqual(preset_intermedio("qsv"), "balanced")
        self.assertEqual(preset_intermedio("nvenc"), "p4")
        self.assertEqual(preset_intermedio("amd"), "balanced")

    def test_mejor_codificador_respeta_la_prioridad(self):
        self.assertEqual(mejor_codificador(("x264", "amd", "qsv")), "qsv")
        self.assertEqual(
            mejor_codificador(("x264", "amd", "qsv", "nvenc")), "nvenc")
        self.assertEqual(mejor_codificador(("x264",)), "x264")
        self.assertEqual(mejor_codificador(()), "x264")


class TestValoresIniciales(unittest.TestCase):

    def test_horizontal(self):
        ajustes = valores_iniciales(False, "qsv")
        self.assertEqual((ajustes.ancho_lienzo, ajustes.alto_lienzo),
                         (1920, 1080))
        self.assertEqual((ajustes.ancho_salida, ajustes.alto_salida),
                         (1280, 720))
        self.assertEqual(ajustes.fps, 30)
        self.assertEqual(ajustes.codificador, "qsv")
        self.assertEqual(ajustes.preset, "balanced")
        self.assertEqual(ajustes.bitrate_video, 2500)
        self.assertEqual(ajustes.bitrate_audio, 160)
        self.assertEqual(ajustes.formato_grabacion, "mkv")
        self.assertEqual(ajustes.calidad_grabacion, "Stream")
        self.assertFalse(ajustes.buffer_clips)
        self.assertEqual(ajustes.segundos_buffer, 30)
        self.assertEqual(ajustes.muestreo, 48000)
        self.assertEqual(ajustes.canales, "Stereo")
        self.assertEqual((ajustes.servidor, ajustes.clave), ("", ""))
        self.assertFalse(ajustes.bitrate_dinamico)
        self.assertTrue(ajustes.reconectar)

    def test_vertical(self):
        ajustes = valores_iniciales(True, "nvenc")
        self.assertEqual((ajustes.ancho_lienzo, ajustes.alto_lienzo),
                         (1080, 1920))
        self.assertEqual((ajustes.ancho_salida, ajustes.alto_salida),
                         (720, 1280))
        self.assertEqual(ajustes.preset, "p4")

    def test_los_iniciales_pasan_la_validacion(self):
        for codificador in ("x264", "qsv", "nvenc", "amd"):
            with self.subTest(codificador=codificador):
                validar(valores_iniciales(False, codificador))


class TestPar(unittest.TestCase):

    def test_redondea_hacia_abajo_al_par(self):
        self.assertEqual(par(854), 852)
        self.assertEqual(par(721), 720)
        self.assertEqual(par(1920), 1920)
        self.assertEqual(par(1080), 1080)


class TestParametrosObs(unittest.TestCase):

    def parametros(self, ajustes):
        return {(categoria, nombre): valor
                for categoria, nombre, valor in parametros_obs(ajustes)}

    def test_correspondencia_con_las_claves_de_obs(self):
        ajustes = de_prueba(
            codificador="nvenc", preset="p4", bitrate_video=4500,
            bitrate_audio=192, bitrate_dinamico=True, reconectar=False,
            espera_reconexion=10, reintentos=20, formato_grabacion="mp4",
            calidad_grabacion="HQ", buffer_clips=True, segundos_buffer=60,
            muestreo=44100, canales="Mono")
        parametros = self.parametros(ajustes)
        self.assertEqual(parametros[("SimpleOutput", "StreamEncoder")], "nvenc")
        self.assertEqual(parametros[("SimpleOutput", "VBitrate")], "4500")
        self.assertEqual(parametros[("SimpleOutput", "ABitrate")], "192")
        self.assertEqual(parametros[("SimpleOutput", "NVENCPreset2")], "p4")
        self.assertEqual(parametros[("SimpleOutput", "DynamicBitrate")],
                         "true")
        self.assertEqual(parametros[("Output", "Reconnect")], "false")
        self.assertEqual(parametros[("Output", "RetryDelay")], "10")
        self.assertEqual(parametros[("Output", "MaxRetries")], "20")
        self.assertEqual(parametros[("SimpleOutput", "RecFormat2")], "mp4")
        self.assertEqual(parametros[("SimpleOutput", "RecQuality")], "HQ")
        self.assertEqual(parametros[("SimpleOutput", "RecRB")], "true")
        self.assertEqual(parametros[("SimpleOutput", "RecRBTime")], "60")
        self.assertEqual(parametros[("Audio", "SampleRate")], "44100")
        self.assertEqual(parametros[("Audio", "ChannelSetup")], "Mono")

    def test_usa_la_clave_de_preset_del_codificador(self):
        for codificador in ("x264", "qsv", "nvenc", "amd"):
            with self.subTest(codificador=codificador):
                ajustes = valores_iniciales(False, codificador)
                parametros = self.parametros(ajustes)
                self.assertEqual(
                    parametros[("SimpleOutput", clave_preset(codificador))],
                    ajustes.preset)
                if codificador != "qsv":
                    self.assertNotIn(("SimpleOutput", "QSVPreset"),
                                     parametros)


class TestValidar(unittest.TestCase):

    def test_acepta_los_valores_iniciales(self):
        validar(valores_iniciales(False, "x264"))

    def test_rechaza_valores_fuera_de_lista(self):
        casos = {
            "fps": {"fps": 29},
            "bitrate_audio": {"bitrate_audio": 100},
            "formato_grabacion": {"formato_grabacion": "avi"},
            "calidad_grabacion": {"calidad_grabacion": "Alta"},
            "muestreo": {"muestreo": 22050},
            "canales": {"canales": "Cinco"},
            "codificador": {"codificador": "vaapi"},
            "preset": {"preset": "p9", "codificador": "nvenc"},
            "lienzo_impar": {"ancho_lienzo": 1919},
            "salida_impar": {"alto_salida": 721},
        }
        for nombre, cambios in casos.items():
            with self.subTest(caso=nombre), self.assertRaises(ValueError):
                validar(de_prueba(**cambios))


if __name__ == "__main__":
    unittest.main()
