# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Contratos entre la configuración y el generador de sonidos."""

import ast
import contextlib
import io
import os
import struct
import subprocess
import sys
import tempfile
import unittest
import wave
from pathlib import Path

from guyrapu.core import config, eventos_sonido
from scripts import sound_gen

# Medidos sobre sounds/themes/*/espera.wav de la base el 18/11/2026.
DURACION_ESPERA = 0.32
PICO_ESPERA = 0.379974365234375


def _canal_izquierdo(ruta):
    with wave.open(str(ruta), "rb") as wav:
        canales = wav.getnchannels()
        frecuencia = wav.getframerate()
        crudo = wav.readframes(wav.getnframes())
    enteros = struct.unpack(f"<{len(crudo) // 2}h", crudo)
    return list(enteros[0::canales]), frecuencia


def _notas_de_espera(muestras, frecuencia):
    # El respiro es el primer tramo de ceros de al menos 20 ms: separa las dos
    # notas sin depender de sus duraciones exactas.
    minimo = int(frecuencia * 0.02)
    inicio = None
    for i, muestra in enumerate(muestras):
        if muestra != 0:
            if inicio is not None and i - inicio >= minimo:
                return muestras[:inicio], muestras[i:]
            inicio = None
        elif inicio is None:
            inicio = i
    return [], []


def _frecuencia_de_nota(muestras, frecuencia):
    cruces = sum(
        1 for anterior, siguiente in zip(muestras, muestras[1:])
        if (anterior < 0 <= siguiente) or (anterior >= 0 > siguiente))
    return cruces * frecuencia / (2 * len(muestras))


class PruebasSoundGen(unittest.TestCase):
    def test_la_espera_son_dos_notas_iguales_en_g5_en_los_dos_temas(self):
        for tema in ("default", "suave"):
            ruta = sound_gen.THEMES_DIR / tema / "espera.wav"
            generador = sound_gen.TEMAS[tema]["espera.wav"]
            with self.subTest(tema=tema):
                fuentes = (
                    ("wav", _canal_izquierdo(ruta)),
                    ("generador", (generador(), sound_gen.SR)),
                )
                for origen, (muestras, frecuencia) in fuentes:
                    with self.subTest(origen=origen):
                        primera, segunda = _notas_de_espera(muestras, frecuencia)
                        self.assertTrue(primera and segunda, ruta.name)
                        f1 = _frecuencia_de_nota(primera, frecuencia)
                        f2 = _frecuencia_de_nota(segunda, frecuencia)
                        self.assertGreaterEqual(f2, f1, ruta.name)
                        self.assertAlmostEqual(f1, sound_gen.G5,
                                               delta=sound_gen.G5 * 0.05)
                        self.assertAlmostEqual(f2, sound_gen.G5,
                                               delta=sound_gen.G5 * 0.05)

    def test_la_espera_no_supera_la_duracion_ni_el_pico_de_antes(self):
        for tema in ("default", "suave"):
            ruta = sound_gen.THEMES_DIR / tema / "espera.wav"
            with self.subTest(tema=tema):
                muestras, frecuencia = _canal_izquierdo(ruta)
                duracion = len(muestras) / frecuencia
                pico = max(abs(m) for m in muestras) / 32768.0
                self.assertLessEqual(duracion, DURACION_ESPERA, ruta.name)
                self.assertLessEqual(pico, PICO_ESPERA, ruta.name)

    def test_eventos_del_tema_default_coinciden_con_configuracion(self):
        generados = {Path(nombre).stem for nombre in sound_gen.TEMAS["default"]}
        configurados = set(config._EVENTOS_SONIDO) - set(eventos_sonido.SONIDOS)
        sobrantes = sorted(generados - configurados)
        faltantes = sorted(configurados - generados)

        self.assertEqual(
            generados,
            configurados,
            f"Sobran: {sobrantes}; faltan: {faltantes}",
        )

    def test_los_dos_temas_tienen_las_mismas_claves(self):
        self.assertEqual(set(sound_gen.TEMAS["suave"]), set(sound_gen.TEMAS["default"]))

    def test_los_generadores_suaves_son_distintos_a_los_del_tema_default(self):
        for nombre, generador_default in sound_gen.TEMAS["default"].items():
            generador_suave = sound_gen.TEMAS["suave"][nombre]
            self.assertTrue(callable(generador_default), nombre)
            self.assertTrue(callable(generador_suave), nombre)
            self.assertIsNot(generador_suave, generador_default, nombre)

    def test_no_queda_generador_sin_tema(self):
        arbol = ast.parse(Path(sound_gen.__file__).read_text(encoding="utf-8"))
        definidas = {
            nodo.name for nodo in arbol.body
            if isinstance(nodo, ast.FunctionDef)
            and (nodo.name.startswith("gen_") or nodo.name.startswith("s_"))}
        usadas = {
            nodo.id for nodo in ast.walk(arbol)
            if isinstance(nodo, ast.Name) and isinstance(nodo.ctx, ast.Load)}
        self.assertEqual(sorted(definidas - usadas), [])

    def test_el_paneo_solo_refiere_eventos_validos_y_esta_en_rango(self):
        eventos = set(sound_gen.TEMAS["default"])
        self.assertTrue(set(sound_gen.PANEO).issubset(eventos))
        for nombre, valor in sound_gen.PANEO.items():
            self.assertGreaterEqual(valor, -1, nombre)
            self.assertLessEqual(valor, 1, nombre)

    def test_generar_los_dos_temas_crea_wav_estereo(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as directorio:
            raiz = Path(directorio)
            with contextlib.redirect_stdout(io.StringIO()):
                for tema, sonidos in sound_gen.TEMAS.items():
                    destino = raiz / tema
                    self.assertEqual(sound_gen.generar_tema(tema, destino),
                                     len(sonidos))
                    for nombre in sonidos:
                        ruta = destino / nombre
                        self.assertGreater(ruta.stat().st_size, 0, nombre)
                        with wave.open(str(ruta), "rb") as wav:
                            self.assertEqual(wav.getnchannels(), 2, nombre)

    def test_genera_tema_default_con_consola_cp1252(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as directorio:
            destino = Path(directorio) / "salida"
            entorno = dict(os.environ)
            entorno["PYTHONIOENCODING"] = "cp1252"
            guion = Path(sound_gen.__file__)
            proc = subprocess.run(
                [sys.executable, str(guion), "-t", "default", "-d", str(destino)],
                capture_output=True, text=True, env=entorno, timeout=60)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            generados = list(destino.glob("*.wav"))
            self.assertEqual(len(generados), len(sound_gen.TEMAS["default"]))

    def test_la_guia_se_genera_igual_desde_su_modulo(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as directorio:
            destino = Path(directorio)
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(sound_gen.generar_guia(destino), 2)
                self.assertEqual(sound_gen.generar_guia(destino), 0)
            for nombre in ("listo.wav", "sin_rostro.wav"):
                self.assertEqual((destino / nombre).read_bytes(),
                                 (sound_gen.GUIA_DIR / nombre).read_bytes())

    def test_el_guion_genera_la_guia_en_la_carpeta_indicada(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as directorio:
            destino = Path(directorio) / "guia"
            guion = Path(sound_gen.__file__)
            proc = subprocess.run(
                [sys.executable, str(guion), "-t", "guia", "-d", str(destino)],
                capture_output=True, text=True, timeout=60)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            for nombre in ("listo.wav", "sin_rostro.wav"):
                self.assertEqual((destino / nombre).read_bytes(),
                                 (sound_gen.GUIA_DIR / nombre).read_bytes())

    def test_generar_tema_omite_archivos_ya_existentes(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as directorio:
            destino = Path(directorio)
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(sound_gen.generar_tema("default", destino),
                                 len(sound_gen.TEMAS["default"]))
                self.assertEqual(sound_gen.generar_tema("default", destino), 0)


if __name__ == "__main__":
    unittest.main()
