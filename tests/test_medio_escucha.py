# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""La escucha previa y la duración con libVLC de verdad, con WAV de sounds/.

No abre ventanas. Se salta si libVLC no está.
"""

import unittest
import wave

from guyrapu.core import paths
from guyrapu.player import motor_vlc
from guyrapu.ui import medios_ventana
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
        self.assertEqual(medios_ventana.duracion_de(wav), esperado)


if __name__ == "__main__":
    unittest.main()
