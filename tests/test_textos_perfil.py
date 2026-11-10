# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de cómo se dice cada valor de un perfil de OBS."""

import unittest

from guyrapu.obs import textos_perfil


class TestCodificadores(unittest.TestCase):

    def test_las_cuatro_formas_de_decirlo(self):
        self.assertEqual(textos_perfil.opciones_codificador(), (
            ("nvenc", "Gráfica NVIDIA (NVENC)"),
            ("qsv", "Gráfica Intel (QuickSync)"),
            ("amd", "Gráfica AMD"),
            ("x264", "Procesador (x264)"),
        ))

    def test_ofrece_solo_los_disponibles(self):
        self.assertEqual(
            [valor for valor, _etiqueta
             in textos_perfil.opciones_codificador(("x264", "qsv"))],
            ["qsv", "x264"])

    def test_dice_el_codificador_y_no_inventa(self):
        self.assertEqual(textos_perfil.decir_codificador("nvenc"),
                         "Gráfica NVIDIA (NVENC)")
        self.assertEqual(textos_perfil.decir_codificador("vaapi"), "vaapi")


class TestPresets(unittest.TestCase):

    def test_el_x264_tiene_sus_seis_presets(self):
        opciones = textos_perfil.opciones_preset("x264")
        self.assertEqual([valor for valor, _etiqueta in opciones], [
            "ultrafast", "superfast", "veryfast", "faster", "fast", "medium"])
        self.assertEqual(opciones[2], ("veryfast", "Muy rápido"))

    def test_el_nvenc_tiene_siete_y_el_qsv_tres(self):
        self.assertEqual(len(textos_perfil.opciones_preset("nvenc")), 7)
        self.assertEqual(len(textos_perfil.opciones_preset("qsv")), 3)

    def test_el_preset_cambia_de_lista_con_el_codificador(self):
        self.assertNotEqual(textos_perfil.opciones_preset("x264"),
                            textos_perfil.opciones_preset("nvenc"))

    def test_dice_el_preset_y_no_inventa(self):
        self.assertEqual(textos_perfil.decir_preset("nvenc", "p4"),
                         "Equilibrado")
        self.assertEqual(textos_perfil.decir_preset("x264", "raro"), "raro")


class TestCalidadDeGrabacion(unittest.TestCase):

    def test_los_textos_de_obs_en_espanol(self):
        self.assertEqual(textos_perfil.opciones_calidad(), (
            ("Stream", "Igual que la transmisión"),
            ("Small", "Alta calidad, archivo mediano"),
            ("HQ", "Calidad indistinguible, archivo grande"),
            ("Lossless", "Sin pérdida, archivo muy grande"),
        ))

    def test_dice_la_calidad(self):
        self.assertEqual(textos_perfil.decir_calidad("HQ"),
                         "Calidad indistinguible, archivo grande")


class TestFormatoMuestreoYCanales(unittest.TestCase):

    def test_los_formatos(self):
        self.assertEqual(textos_perfil.opciones_formato(), (
            ("mkv", "MKV"), ("mp4", "MP4"),
            ("hybrid_mp4", "Híbrido MP4"), ("mov", "MOV"), ("flv", "FLV")))
        self.assertEqual(textos_perfil.decir_formato("hybrid_mp4"),
                         "Híbrido MP4")

    def test_el_muestreo(self):
        self.assertEqual(textos_perfil.opciones_muestreo(), (
            (44100, "44,1 kHz"), (48000, "48 kHz")))
        self.assertEqual(textos_perfil.decir_muestreo(48000), "48 kHz")

    def test_los_canales(self):
        self.assertEqual(textos_perfil.opciones_canales(), (
            ("Mono", "Mono"), ("Stereo", "Estéreo")))
        self.assertEqual(textos_perfil.decir_canales("Stereo"), "Estéreo")


class TestResoluciones(unittest.TestCase):

    def test_las_horizontales_ofrecidas(self):
        self.assertEqual(
            textos_perfil.opciones_resolucion(False),
            ((1920, 1080), (1600, 900), (1280, 720)))

    def test_las_verticales_ofrecidas(self):
        self.assertEqual(
            textos_perfil.opciones_resolucion(True),
            ((1080, 1920), (900, 1600), (720, 1280)))

    def test_agrega_la_que_el_perfil_ya_tiene(self):
        self.assertIn((1366, 768),
                      textos_perfil.opciones_resolucion(False, (1366, 768)))

    def test_la_salida_no_pasa_del_lienzo(self):
        opciones = textos_perfil.opciones_salida(False, (1280, 720))
        self.assertEqual(opciones, ((1280, 720),))
        self.assertNotIn((1920, 1080), opciones)

    def test_la_equivalente_cambia_de_orientacion(self):
        self.assertEqual(
            textos_perfil.equivalente((1920, 1080), True), (1080, 1920))
        self.assertEqual(
            textos_perfil.equivalente((1080, 1920), False), (1920, 1080))
        self.assertEqual(
            textos_perfil.equivalente((1600, 900), True), (900, 1600))


class TestListasSimples(unittest.TestCase):

    def test_los_fotogramas_por_segundo(self):
        opciones = textos_perfil.opciones_fps()
        self.assertEqual([valor for valor, _etiqueta in opciones],
                         [20, 24, 25, 30, 48, 50, 60])
        self.assertEqual(opciones[3], (30, "30"))

    def test_los_bitrates_de_audio(self):
        opciones = textos_perfil.opciones_bitrate_audio()
        self.assertEqual([valor for valor, _etiqueta in opciones],
                         [64, 96, 128, 160, 192, 256, 320])


if __name__ == "__main__":
    unittest.main()
