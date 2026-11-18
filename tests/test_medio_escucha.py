# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""La escucha previa con libVLC de verdad, con un WAV corto de sounds/.

No abre ventanas. Se salta si libVLC no está.
"""

import unittest

from guyrapu.core import paths
from guyrapu.player import motor_vlc
from guyrapu.ui.medio_escucha import EscuchaPrevia


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


if __name__ == "__main__":
    unittest.main()
