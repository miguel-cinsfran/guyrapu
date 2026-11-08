"""Pruebas de los tonos de la guía, armados en memoria.

Sin wx ni winmm: cada función devuelve un WAV completo que se abre con
`wave` de la biblioteca estándar.
"""

import hashlib
import io
import unittest
import wave

import numpy as np

from guyrapu.camera import tono_guia


def _muestras(datos):
    with wave.open(io.BytesIO(datos), "rb") as wav:
        canales = wav.getnchannels()
        ancho = wav.getsampwidth()
        frecuencia = wav.getframerate()
        cuadros = wav.readframes(wav.getnframes())
    enteros = np.frombuffer(cuadros, dtype="<i2")
    return canales, ancho, frecuencia, enteros.reshape(-1, canales)


class TestPitido(unittest.TestCase):

    def test_es_un_wav_estereo_de_60_ms(self):
        canales, ancho, frecuencia, muestras = _muestras(
            tono_guia.pitido(0.0, 440.0, "normal"))
        self.assertEqual(canales, 2)
        self.assertEqual(ancho, 2)
        self.assertEqual(frecuencia, 44100)
        self.assertAlmostEqual(len(muestras) / frecuencia, 0.06, delta=0.002)

    def test_el_paneo_izquierdo_calla_el_canal_derecho(self):
        _, _, _, muestras = _muestras(tono_guia.pitido(-1.0, 440.0, "normal"))
        self.assertGreater(int(np.abs(muestras[:, 0]).max()), 1000)
        self.assertEqual(int(np.abs(muestras[:, 1]).max()), 0)

    def test_el_paneo_derecho_calla_el_canal_izquierdo(self):
        _, _, _, muestras = _muestras(tono_guia.pitido(1.0, 440.0, "normal"))
        self.assertGreater(int(np.abs(muestras[:, 1]).max()), 1000)
        self.assertEqual(int(np.abs(muestras[:, 0]).max()), 0)

    def test_un_timbre_desconocido_suena_como_el_normal(self):
        self.assertEqual(tono_guia.pitido(0.2, 440.0, "raro"),
                         tono_guia.pitido(0.2, 440.0, "normal"))


class TestTonoCentro(unittest.TestCase):

    def test_el_bucle_no_salta_mas_que_la_propia_onda(self):
        for timbre in tono_guia.TIMBRES:
            with self.subTest(timbre=timbre):
                _, _, frecuencia, muestras = _muestras(
                    tono_guia.tono_centro(timbre))
                canal = muestras[:, 0].astype(int)
                saltos = np.abs(np.diff(canal))
                salto_bucle = abs(int(canal[0]) - int(canal[-1]))
                self.assertLessEqual(salto_bucle, int(saltos.max()))
                ciclos = len(canal) * tono_guia.FRECUENCIA_CENTRO / frecuencia
                self.assertAlmostEqual(ciclos, round(ciclos), places=6)

    def test_dura_medio_segundo_y_suena_centrado(self):
        _, _, frecuencia, muestras = _muestras(
            tono_guia.tono_centro("normal"))
        self.assertAlmostEqual(len(muestras) / frecuencia, 0.5, delta=0.002)
        self.assertAlmostEqual(int(muestras[:, 0].max()),
                               int(muestras[:, 1].max()), delta=2)


class TestMuestra(unittest.TestCase):

    def test_los_tres_timbres_dan_muestras_distintas(self):
        datos = {timbre: tono_guia.muestra(timbre)
                 for timbre in tono_guia.TIMBRES}
        self.assertEqual(len(set(datos.values())), len(tono_guia.TIMBRES))

    def test_la_lista_de_timbres_es_la_esperada(self):
        self.assertEqual(tono_guia.TIMBRES, ("normal", "calido", "8bits"))

    def test_ningun_timbre_pasa_del_pico_de_los_wav_de_hoy(self):
        pico_hoy = int(round(0.6 * 32767))
        for timbre in tono_guia.TIMBRES:
            with self.subTest(timbre=timbre):
                for datos in (tono_guia.pitido(0.0, 440.0, timbre),
                              tono_guia.tono_centro(timbre),
                              tono_guia.muestra(timbre)):
                    _, _, _, muestras = _muestras(datos)
                    self.assertLessEqual(int(np.abs(muestras).max()),
                                         pico_hoy)


class TestWavsDeHoy(unittest.TestCase):
    """Los WAV suenan igual que antes de diferir la importación de numpy."""

    RESUMENES = {
        ("pitido", "normal"): "deb0639968ab3b8db3d7a4040c6467f271279a339134a5ee85c5dd48ff042071",
        ("tono_centro", "normal"): "3933268bb32ecad546d4e53da1e20c9d9c486c2c13996830febad9b354d6fc5a",
        ("muestra", "normal"): "8b9f99d5b086409e55be96d6baab933a10f707fa6bec0c0a65319968f69ae1b3",
        ("pitido", "calido"): "d5452db641964eff404dc11442bb7655b0c4eb271e6763da70a96c3ffb93b5ed",
        ("tono_centro", "calido"): "636f37ef187798bfdd829b7ccdee0a4cd57550678cae8d355035ccd870a5a8f6",
        ("muestra", "calido"): "67ed93da5fb6ca0867dcdcf4f02c04ba6e36cff4faa137556b94e34a8a1c4722",
        ("pitido", "8bits"): "b685fa6f4aaee354791a84156a62685006a026df33b23b9dda94bc5bc67207c7",
        ("tono_centro", "8bits"): "ccb9f17731af04602f5b65b81b279fbbd5bc2c1aa4cf195dc57c144939bf2963",
        ("muestra", "8bits"): "9bb5e1d2437be2ca1f2787cc53b2903c508efa40322c8e24a272e2aa86cf7e81",
    }

    def test_los_nueve_wav_coinciden_byte_a_byte(self):
        for timbre in tono_guia.TIMBRES:
            for nombre in ("pitido", "tono_centro", "muestra"):
                with self.subTest(timbre=timbre, nombre=nombre):
                    if nombre == "pitido":
                        datos = tono_guia.pitido(0.0, 440.0, timbre)
                    elif nombre == "tono_centro":
                        datos = tono_guia.tono_centro(timbre)
                    else:
                        datos = tono_guia.muestra(timbre)
                    self.assertEqual(
                        hashlib.sha256(datos).hexdigest(),
                        self.RESUMENES[(nombre, timbre)])


if __name__ == "__main__":
    unittest.main()
