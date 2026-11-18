# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Medición de la sonoridad de un medio, en segundo plano."""

import math
import struct
import tempfile
import threading
import unittest
import wave
from pathlib import Path
from unittest import mock

from guyrapu.downloads.ffmpeg_bin import ruta_ffmpeg
from guyrapu.interaction import medios_guardados
from guyrapu.music import sonoridad
from guyrapu.ui import medios_medicion


def _generar_seno(ruta, segundos=3):
    cuadros = bytearray()
    for i in range(44100 * segundos):
        muestra = int(0.4 * 32767 * math.sin(2 * math.pi * 1000 * i / 44100))
        cuadros += struct.pack("<h", muestra)
    with wave.open(str(ruta), "w") as canal:
        canal.setnchannels(1)
        canal.setsampwidth(2)
        canal.setframerate(44100)
        canal.writeframes(bytes(cuadros))


class TestMedirReal(unittest.TestCase):

    def test_mide_de_verdad_un_wav_generado(self):
        if ruta_ffmpeg() is None:
            self.skipTest("ruta_ffmpeg() devolvió None: sin ffmpeg para medir")
        with tempfile.TemporaryDirectory() as tmp:
            ruta = str(Path(tmp) / "tono.wav")
            _generar_seno(ruta)
            recibidas = []
            listo = threading.Event()

            def al_terminar(ganancia):
                recibidas.append(ganancia)
                listo.set()

            with mock.patch.object(
                    medios_medicion.wx, "CallAfter",
                    side_effect=lambda funcion, *datos: funcion(*datos)):
                medios_medicion.medir(ruta, al_terminar)
                self.assertTrue(listo.wait(120), "la medición no terminó")

            self.assertEqual(len(recibidas), 1)
            self.assertIsNotNone(recibidas[0])
            self.assertGreaterEqual(recibidas[0],
                                    sonoridad.GANANCIA_MINIMA_DB)
            self.assertLessEqual(recibidas[0],
                                 sonoridad.GANANCIA_MAXIMA_DB)


class TestMedicionTardia(unittest.TestCase):

    def test_un_medio_eliminado_descarta_la_ganancia(self):
        guardados = [medios_guardados.normalizar({
            "nombre": "Risa", "tipo": "sonido", "archivo": "risa.wav"})]
        anotadas = []
        listo = threading.Event()

        def medidor(_ruta_ffmpeg, _ruta):
            guardados.clear()
            return -6.5

        def al_terminar(ganancia):
            indice = medios_guardados.indice_de_archivo(
                guardados, "risa.wav")
            if indice is not None:
                guardados[indice]["ganancia_db"] = ganancia
                anotadas.append(ganancia)
            listo.set()

        with mock.patch.object(medios_medicion.sonoridad, "medir",
                               side_effect=medidor), \
                mock.patch.object(medios_medicion.ffmpeg_bin, "ruta_ffmpeg",
                                  return_value="ffmpeg"), \
                mock.patch.object(
                    medios_medicion.wx, "CallAfter",
                    side_effect=lambda funcion, *datos: funcion(*datos)):
            medios_medicion.medir("C:/medios/risa.wav", al_terminar)
            self.assertTrue(listo.wait(10), "la medición no terminó")

        self.assertEqual(guardados, [])
        self.assertEqual(anotadas, [])


if __name__ == "__main__":
    unittest.main()
