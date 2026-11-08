"""Pruebas del arranque liviano: nada pesado se importa antes de usarse.

Cada comprobación corre en un proceso nuevo de Python, sin ventanas, sobre
una copia temporal del INI de fábrica.
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]


GUION = """
import json
import os
import sys

sys.path.insert(0, os.getcwd())

import wx
from guyrapu.ui import gui

estados = {}


def foto(etapa):
    estados[etapa] = {
        "numpy": "numpy" in sys.modules,
        "googleapiclient": "googleapiclient.discovery" in sys.modules,
    }


foto("gui")

from guyrapu.core import config
from tests.rutas_temporales import redirigir_rutas

with redirigir_rutas(sys.argv[1]):
    config.cargar_configuracion()
foto("config")

from guyrapu.youtube import youtube_api

estados["google"] = {
    "disponible": youtube_api.google_disponible(),
    "numpy": "numpy" in sys.modules,
    "googleapiclient": "googleapiclient.discovery" in sys.modules,
}
print(json.dumps(estados))
"""


def _correr():
    with tempfile.TemporaryDirectory() as tmp:
        ini = RAIZ / "config.predeterminado.ini"
        (Path(tmp) / "config.ini").write_text(
            ini.read_text(encoding="utf-8"), encoding="utf-8")
        resultado = subprocess.run(
            [sys.executable, "-I", "-c", GUION, tmp],
            cwd=str(RAIZ), capture_output=True, timeout=180)
    if resultado.returncode != 0:
        raise AssertionError(resultado.stderr.decode("utf-8", "replace"))
    return json.loads(resultado.stdout.decode("utf-8"))


class TestArranqueLiviano(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.estados = _correr()

    @classmethod
    def tearDownClass(cls):
        del cls.estados

    def test_gui_y_config_no_cargan_numpy_ni_google(self):
        for etapa in ("gui", "config"):
            with self.subTest(etapa=etapa):
                self.assertFalse(self.estados[etapa]["numpy"])
                self.assertFalse(self.estados[etapa]["googleapiclient"])

    def test_google_disponible_da_bien_sin_importar_discovery(self):
        self.assertTrue(self.estados["google"]["disponible"])
        self.assertFalse(self.estados["google"]["googleapiclient"])


if __name__ == "__main__":
    unittest.main()
