# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Ruta del archivo de cada evento dentro de un tema de sonidos.

Sin ventanas: usa una carpeta de tema temporal y la tabla de sonidos.
"""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from guyrapu.core import config
from guyrapu.core import eventos_sonido
from guyrapu.core import sonidos_tema
from tests.rutas_temporales import redirigir_rutas


def _tocar(carpeta: Path, nombre: str) -> Path:
    ruta = carpeta / f"{nombre}.wav"
    ruta.write_bytes(b"RIFF")
    return ruta


class TestRutaEvento(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.carpeta = Path(self._tmp.name)
        self.evento = eventos_sonido.EVENTOS[0]

    def test_archivo_del_evento_gana_al_asignado(self):
        propia = _tocar(self.carpeta, self.evento)
        _tocar(self.carpeta, "otro")
        with mock.patch.dict(eventos_sonido.SONIDOS,
                             {self.evento: "otro"}):
            self.assertEqual(
                sonidos_tema.ruta_evento(self.carpeta, self.evento), propia)

    def test_sin_archivo_del_evento_suena_el_asignado(self):
        asignada = _tocar(self.carpeta, "otro")
        with mock.patch.dict(eventos_sonido.SONIDOS,
                             {self.evento: "otro"}):
            self.assertEqual(
                sonidos_tema.ruta_evento(self.carpeta, self.evento), asignada)

    def test_sin_ningun_archivo_devuelve_la_ruta_del_evento(self):
        with mock.patch.dict(eventos_sonido.SONIDOS,
                             {self.evento: "otro"}):
            self.assertEqual(
                sonidos_tema.ruta_evento(self.carpeta, self.evento),
                self.carpeta / f"{self.evento}.wav")

    def test_evento_fuera_de_la_tabla_suena_con_su_archivo(self):
        propia = _tocar(self.carpeta, self.evento)
        self.assertEqual(
            sonidos_tema.ruta_evento(self.carpeta, self.evento), propia)

    def test_un_tema_propio_conserva_el_archivo_de_un_evento_asignado(self):
        evento = "conectado"
        self.assertIn(evento, eventos_sonido.SONIDOS)
        propia = _tocar(self.carpeta, evento)
        self.assertEqual(
            sonidos_tema.ruta_evento(self.carpeta, evento), propia)


class TestRespaldoDelTemaPredeterminado(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.temas = Path(self._tmp.name) / "themes"
        self.propio = self.temas / "propio"
        self.predeterminado = self.temas / "default"
        self.propio.mkdir(parents=True)
        self.predeterminado.mkdir()
        self.evento = eventos_sonido.EVENTOS[0]

    def test_evento_en_el_predeterminado_respalda_al_tema_propio(self):
        respaldo = _tocar(self.predeterminado, self.evento)
        with mock.patch.dict(eventos_sonido.SONIDOS,
                             {self.evento: "otro"}):
            self.assertEqual(
                sonidos_tema.ruta_evento(self.propio, self.evento), respaldo)

    def test_asignado_en_el_predeterminado_respalda_al_tema_propio(self):
        respaldo = _tocar(self.predeterminado, "otro")
        with mock.patch.dict(eventos_sonido.SONIDOS,
                             {self.evento: "otro"}):
            self.assertEqual(
                sonidos_tema.ruta_evento(self.propio, self.evento), respaldo)

    def test_asignado_del_tema_propio_gana_sobre_el_evento_predeterminado(self):
        propia = _tocar(self.propio, "otro")
        _tocar(self.predeterminado, self.evento)
        with mock.patch.dict(eventos_sonido.SONIDOS,
                             {self.evento: "otro"}):
            self.assertEqual(
                sonidos_tema.ruta_evento(self.propio, self.evento), propia)

    def test_sin_archivos_en_ningun_tema_devuelve_la_ruta_del_evento(self):
        with mock.patch.dict(eventos_sonido.SONIDOS,
                             {self.evento: "otro"}):
            self.assertEqual(
                sonidos_tema.ruta_evento(self.propio, self.evento),
                self.propio / f"{self.evento}.wav")


class TestCableadoConfig(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.raiz = Path(self._tmp.name)
        self.tema = self.raiz / "sounds" / "themes" / "default"
        self.tema.mkdir(parents=True)
        (self.raiz / "sounds.ini").write_text(
            "[sonidos]\nactivar = true\ntema = default\n", encoding="utf-8")

    def test_cargar_sonidos_usa_el_sonido_asignado(self):
        evento = eventos_sonido.EVENTOS[0]
        asignada = _tocar(self.tema, "otro")
        with redirigir_rutas(self.raiz), \
                mock.patch.dict(eventos_sonido.SONIDOS, {evento: "otro"}):
            sonidos = config.cargar_sonidos()
        self.assertEqual(sonidos["eventos"][evento], asignada)


if __name__ == "__main__":
    unittest.main()
