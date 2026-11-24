# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""La escucha previa y la duración con libVLC de verdad, con WAV de sounds/.

También prueba el volumen con un reproductor falso. No abre ventanas. Las
pruebas con VLC de verdad se saltan si libVLC no está.
"""

import unittest
import wave
from unittest import mock

from guyrapu.core import paths
from guyrapu.music import sonoridad
from guyrapu.player import motor_vlc
from guyrapu.ui import medio_escucha, medios_medicion
from guyrapu.ui.medio_escucha import EscuchaPrevia


def _wav_con_duracion():
    """Un WAV de sounds/ de al menos dos segundos, con sus segundos."""
    for wav in sorted(paths.carpeta_sonidos().rglob("*.wav")):
        try:
            with wave.open(str(wav), "rb") as archivo:
                segundos = archivo.getnframes() / archivo.getframerate()
        except (wave.Error, OSError):
            continue
        if round(segundos) >= 2:
            return wav, round(segundos)
    return None, 0


@unittest.skipUnless(motor_vlc.disponible(), "libVLC no está disponible")
class TestEscuchaPrevia(unittest.TestCase):

    def test_un_wav_arranca_y_se_detiene(self):
        wav = next(iter(sorted(paths.carpeta_sonidos().rglob("*.wav"))), None)
        if wav is None:
            self.skipTest("no hay un WAV en sounds/")
        escucha = EscuchaPrevia()
        self.addCleanup(escucha.detener)
        self.assertTrue(escucha.reproducir(wav))
        escucha.detener()
        self.assertFalse(escucha.sonando())


@unittest.skipUnless(motor_vlc.disponible(), "libVLC no está disponible")
class TestDuracion(unittest.TestCase):

    def test_la_duracion_de_un_wav_coincide_con_wave(self):
        wav, esperado = _wav_con_duracion()
        if wav is None:
            self.skipTest("no hay un WAV de dos segundos en sounds/")
        motor_vlc.instancia()
        self.assertEqual(medios_medicion.duracion_de(wav), esperado)


class TestVolumenDeEscucha(unittest.TestCase):

    def test_la_ganancia_baja_y_sube_el_volumen_que_pide_vlc(self):
        reproductor = mock.Mock()
        reproductor.play.return_value = 0
        instancia = mock.Mock()
        with mock.patch.object(medio_escucha.motor_vlc, "instancia",
                               return_value=instancia), \
             mock.patch.object(medio_escucha.motor_vlc, "nuevo_reproductor",
                               return_value=reproductor):
            escucha = EscuchaPrevia()
            self.addCleanup(escucha.detener)
            self.assertTrue(escucha.reproducir("risa.wav", 0.0))
            normal = reproductor.audio_set_volume.call_args.args[0]
            self.assertTrue(escucha.reproducir("risa.wav", -6.0))
            bajado = reproductor.audio_set_volume.call_args.args[0]
            self.assertTrue(escucha.reproducir("risa.wav", 6.0))
            subido = reproductor.audio_set_volume.call_args.args[0]
        self.assertLess(bajado, normal)
        self.assertGreater(subido, normal)
        self.assertEqual(normal, sonoridad.volumen_efectivo(100, 0.0))
        self.assertEqual(bajado, sonoridad.volumen_efectivo(100, -6.0))
        self.assertEqual(subido, sonoridad.volumen_efectivo(100, 6.0))


if __name__ == "__main__":
    unittest.main()
