# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas del fotograma que muestra el reproductor.

Los dobles cubren el acceso al reproductor y el fallo del snapshot. Las dos
pruebas con vídeo real generan un archivo con ffmpeg y lo reproduce libVLC en
un marco wx oculto y abren ventanas.
"""

import subprocess
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import wx

from guyrapu.downloads import ffmpeg_bin
from guyrapu.player import fotograma_video as fotograma
from guyrapu.player import motor_vlc
from tests.ventanas_prueba import app_de_prueba, destruir


_PNG_MINIMO = (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
               b"\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
               b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01"
               b"\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82")


class _ImagenFalsa:
    def __init__(self, ruta, tipo):
        self.ruta = str(ruta)
        self.tipo = tipo
        self.ok = True

    def IsOk(self):
        return self.ok

    def GetWidth(self):
        return 640

    def GetHeight(self):
        return 360

    def SaveFile(self, salida, tipo):
        salida.write(b"jpg-falso")


class TestAccesoAlReproductor(unittest.TestCase):

    def test_sin_panel_no_hay_reproductor(self):
        self.assertIsNone(fotograma.reproductor_de(SimpleNamespace()))

    def test_sin_reproductor_no_hay_reproductor(self):
        marco = SimpleNamespace(_rep_panel=SimpleNamespace())
        self.assertIsNone(fotograma.reproductor_de(marco))

    def test_devuelve_el_reproductor_del_panel(self):
        reproductor = object()
        marco = SimpleNamespace(_rep_panel=SimpleNamespace(
            _player=reproductor))
        self.assertIs(fotograma.reproductor_de(marco), reproductor)


class TestMuestraVideo(unittest.TestCase):

    def test_sin_reproductor_no_muestra_video(self):
        self.assertFalse(fotograma.muestra_video(None))

    def test_sin_salida_de_video_no_muestra_video(self):
        reproductor = mock.Mock()
        reproductor.has_vout.return_value = 0
        self.assertFalse(fotograma.muestra_video(reproductor))

    def test_con_salida_de_video_muestra_video(self):
        reproductor = mock.Mock()
        reproductor.has_vout.return_value = 1
        self.assertTrue(fotograma.muestra_video(reproductor))

    def test_si_falla_la_consulta_no_muestra_video(self):
        reproductor = mock.Mock()
        reproductor.has_vout.side_effect = RuntimeError("sin vídeo")
        self.assertFalse(fotograma.muestra_video(reproductor))


class TestCapturar(unittest.TestCase):

    def setUp(self):
        self.reproductor = mock.Mock()
        self.reproductor.video_get_size.return_value = (640, 360)
        parche = mock.patch.object(fotograma.wx, "Image", _ImagenFalsa)
        parche.start()
        self.addCleanup(parche.stop)

    def test_snapshot_fallido_lanza(self):
        self.reproductor.video_take_snapshot.return_value = -1
        with self.assertRaises(fotograma.FotogramaFallido):
            fotograma.capturar(self.reproductor)

    def test_sin_archivo_lanza(self):
        self.reproductor.video_take_snapshot.return_value = 0
        with self.assertRaises(fotograma.FotogramaFallido):
            fotograma.capturar(self.reproductor)

    def test_imagen_ilegible_lanza(self):
        self.reproductor.video_take_snapshot.side_effect = (
            lambda num, ruta, ancho, alto: Path(ruta).write_bytes(
                _PNG_MINIMO) and 0)

        def imagen_rota(ruta, tipo):
            imagen = _ImagenFalsa(ruta, tipo)
            imagen.ok = False
            return imagen

        with mock.patch.object(fotograma.wx, "Image", imagen_rota), \
                self.assertRaises(fotograma.FotogramaFallido):
            fotograma.capturar(self.reproductor)

    def test_no_agranda_un_video_angosto(self):
        self.reproductor.video_take_snapshot.side_effect = (
            lambda num, ruta, ancho, alto: Path(ruta).write_bytes(
                _PNG_MINIMO) and 0)
        resultado = fotograma.capturar(self.reproductor)
        self.assertEqual(resultado, (b"jpg-falso", 640, 360))
        self.reproductor.video_take_snapshot.assert_called_once()
        self.assertEqual(
            self.reproductor.video_take_snapshot.call_args.args[2], 640)
        self.assertEqual(
            self.reproductor.video_take_snapshot.call_args.args[3], 0)

    def test_video_ancho_queda_en_el_lado_pedido(self):
        self.reproductor.video_get_size.return_value = (1920, 1080)
        self.reproductor.video_take_snapshot.side_effect = (
            lambda num, ruta, ancho, alto: Path(ruta).write_bytes(
                _PNG_MINIMO) and 0)
        fotograma.capturar(self.reproductor)
        self.assertEqual(
            self.reproductor.video_take_snapshot.call_args.args[2], 1280)


@unittest.skipUnless(motor_vlc.disponible(), "libVLC no está disponible")
class TestCapturaReal(unittest.TestCase):

    def _generar_video(self, ffmpeg, ruta):
        proc = subprocess.run(
            [ffmpeg, "-y", "-f", "lavfi",
             "-i", "testsrc=size=640x360:rate=10", "-t", "5",
             "-pix_fmt", "yuv420p", str(ruta)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return proc.returncode == 0 and ruta.is_file()

    def _reproductor(self, marco, ruta, sin_imagen=False):
        instancia = motor_vlc.instancia()
        if instancia is None:
            self.skipTest("no se pudo crear la instancia de libVLC")
        reproductor = instancia.media_player_new()
        medio = instancia.media_new_path(str(ruta))
        if sin_imagen:
            medio.add_option(":no-video")
        reproductor.set_hwnd(marco.GetHandle())
        reproductor.set_media(medio)

        def terminar():
            for accion in (reproductor.stop, reproductor.release):
                try:
                    accion()
                except Exception:
                    pass

        self.addCleanup(terminar)
        reproductor.play()
        return reproductor

    def test_captura_un_jpeg_del_video_que_se_ve(self):
        ffmpeg = ffmpeg_bin.ruta_ffmpeg()
        if not ffmpeg:
            self.skipTest("sin ffmpeg")
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = Path(carpeta) / "video.mp4"
            if not self._generar_video(ffmpeg, ruta):
                self.skipTest("ffmpeg no pudo generar el video")
            app_de_prueba()
            marco = wx.Frame(None)
            self.addCleanup(destruir, marco)
            reproductor = self._reproductor(marco, ruta)
            tope = time.monotonic() + 10
            while time.monotonic() < tope:
                if fotograma.muestra_video(reproductor):
                    break
                time.sleep(0.1)
            self.assertTrue(fotograma.muestra_video(reproductor))
            jpeg, ancho, _alto = fotograma.capturar(reproductor)
        self.assertTrue(jpeg.startswith(b"\xff\xd8"))
        self.assertLessEqual(ancho, 1280)

    def test_en_modo_solo_audio_no_hay_imagen(self):
        ffmpeg = ffmpeg_bin.ruta_ffmpeg()
        if not ffmpeg:
            self.skipTest("sin ffmpeg")
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = Path(carpeta) / "video.mp4"
            if not self._generar_video(ffmpeg, ruta):
                self.skipTest("ffmpeg no pudo generar el video")
            app_de_prueba()
            marco = wx.Frame(None)
            self.addCleanup(destruir, marco)
            reproductor = self._reproductor(marco, ruta, sin_imagen=True)
            time.sleep(2)
            self.assertFalse(fotograma.muestra_video(reproductor))


if __name__ == "__main__":
    unittest.main()
