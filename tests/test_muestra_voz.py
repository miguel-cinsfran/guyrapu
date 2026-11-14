# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""La vista previa de voz contra libVLC de verdad."""

import os
import time
import unittest
from pathlib import Path

from guyrapu.core import config, paquetes_catalogo, red
from guyrapu.player import motor_vlc
from guyrapu.voice import muestra_voz
from guyrapu.voice.proveedores import PROVEEDORES

RAIZ = Path(__file__).resolve().parent.parent
_ARCHIVO = RAIZ / "sounds" / "themes" / "default" / "copiar.wav"
_HABIL_RED = os.environ.get("GUYRAPU_PRUEBAS_CON_RED") == "1"


def _esperar(funcion, valor, segundos=5.0):
    limite = time.monotonic() + segundos
    while time.monotonic() < limite:
        if bool(funcion()) == valor:
            return True
        time.sleep(0.1)
    return bool(funcion()) == valor


@unittest.skipUnless(motor_vlc.disponible(), "libVLC no está disponible")
class TestVistaPreviaReal(unittest.TestCase):

    def test_reproduce_y_detener_lo_corta(self):
        self.addCleanup(muestra_voz.detener)
        reproductor = muestra_voz.reproducir(str(_ARCHIVO), volumen=0)
        self.assertTrue(_esperar(reproductor.is_playing, True))
        muestra_voz.detener()
        self.assertTrue(_esperar(reproductor.is_playing, False))


@unittest.skipUnless(_HABIL_RED,
                     "prueba real desactivada: GUYRAPU_PRUEBAS_CON_RED=1")
class TestCatalogoReal(unittest.TestCase):

    def test_hay_paquetes_de_phonon_y_de_piper(self):
        texto = red.pedir_texto(paquetes_catalogo.URL_CATALOGO)
        paquetes, _descartes = paquetes_catalogo.leer(
            texto, config.APP_VERSION, {"voz"},
            tuple(proveedor.id for proveedor in PROVEEDORES))
        proveedores = {paquete["proveedor"] for paquete in paquetes}
        self.assertIn("phonon", proveedores)
        self.assertIn("piper", proveedores)


if __name__ == "__main__":
    unittest.main()
