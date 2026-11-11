# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de los ajustes de audio que tienen que coincidir entre perfiles."""

import unittest

from guyrapu.obs import audio_de_perfil
from tests.test_perfil_en_disco import (
    carpeta_de_perfiles, crear_perfil, lectura_que_falla)


class ClienteFalso:
    """OBS falso que responde el audio del perfil en uso y anota lo que fija."""

    def __init__(self, audio=None):
        self.audio = dict(audio or {})
        self.llamadas = []

    def pedir(self, tipo, datos=None, parada=None):
        datos = dict(datos or {})
        self.llamadas.append((tipo, datos))
        if tipo == "GetProfileParameter":
            valor = self.audio.get(datos.get("parameterName"), "")
            return {"responseData": {"parameterValue": valor,
                                     "defaultParameterValue": ""}}
        return {"responseData": {}}

    def fijados(self):
        return {(datos.get("parameterCategory"), datos.get("parameterName")):
                datos.get("parameterValue")
                for tipo, datos in self.llamadas
                if tipo == "SetProfileParameter"}


def audio_de(ruta):
    valores = {}
    for linea in ruta.read_text(encoding="utf-8-sig").splitlines():
        limpia = linea.strip()
        if "=" not in limpia:
            continue
        clave, valor = limpia.split("=", 1)
        if clave.strip() in ("SampleRate", "ChannelSetup"):
            valores[clave.strip()] = valor.strip()
    return valores


class TestIgualar(unittest.TestCase):

    def test_p1_destino_distinto_se_iguala_sin_tocar_lo_demas(self):
        with carpeta_de_perfiles() as base:
            carpeta = crear_perfil(base, "Perfil", {
                "Audio": {"SampleRate": "44100", "ChannelSetup": "Mono",
                          "MonitoringDeviceName": "Se queda"},
                "SimpleOutput": {"VBitrate": "2500"},
            })
            cliente = ClienteFalso({"SampleRate": "48000",
                                    "ChannelSetup": "Stereo"})
            audio_de_perfil.igualar(cliente, "Perfil")
            texto = (carpeta / "basic.ini").read_text(encoding="utf-8-sig")
            valores = audio_de(carpeta / "basic.ini")
        self.assertEqual(valores, {"SampleRate": "48000",
                                   "ChannelSetup": "Stereo"})
        self.assertIn("MonitoringDeviceName=Se queda", texto)
        self.assertIn("VBitrate=2500", texto)

    def test_p1_destino_igual_no_se_reescribe(self):
        with carpeta_de_perfiles() as base:
            carpeta = crear_perfil(base, "Perfil", {
                "Audio": {"SampleRate": "48000", "ChannelSetup": "Stereo"}})
            basic = carpeta / "basic.ini"
            antes = basic.read_bytes()
            cliente = ClienteFalso({"SampleRate": "48000",
                                    "ChannelSetup": "Stereo"})
            escrito = audio_de_perfil.igualar(cliente, "Perfil")
            despues = basic.read_bytes()
        self.assertFalse(escrito)
        self.assertEqual(antes, despues)

    def test_p1_destino_sin_la_clave_no_se_toca(self):
        with carpeta_de_perfiles() as base:
            carpeta = crear_perfil(base, "Perfil", {
                "Audio": {"SampleRate": "44100"}})
            cliente = ClienteFalso({"SampleRate": "48000",
                                    "ChannelSetup": "Stereo"})
            audio_de_perfil.igualar(cliente, "Perfil")
            texto = (carpeta / "basic.ini").read_text(encoding="utf-8-sig")
            valores = audio_de(carpeta / "basic.ini")
        self.assertEqual(valores, {"SampleRate": "48000"})
        self.assertNotIn("ChannelSetup", texto)

    def test_p3_archivo_ilegible_avisa_y_deja_seguir(self):
        with carpeta_de_perfiles() as base:
            carpeta = crear_perfil(base, "Perfil", {
                "Audio": {"SampleRate": "44100", "ChannelSetup": "Mono"}})
            cliente = ClienteFalso({"SampleRate": "48000",
                                    "ChannelSetup": "Stereo"})
            with lectura_que_falla(carpeta / "basic.ini"):
                with self.assertLogs("guyrapu.audio_de_perfil",
                                     level="WARNING"):
                    escrito = audio_de_perfil.igualar(cliente, "Perfil")
        self.assertFalse(escrito)

    def test_p2_el_creado_recibe_el_audio_fijado(self):
        cliente = ClienteFalso()
        audio_de_perfil.poner_en_uso(cliente, {"SampleRate": "48000",
                                               "ChannelSetup": "Stereo"})
        self.assertEqual(cliente.fijados(), {
            ("Audio", "SampleRate"): "48000",
            ("Audio", "ChannelSetup"): "Stereo",
        })


if __name__ == "__main__":
    unittest.main()
