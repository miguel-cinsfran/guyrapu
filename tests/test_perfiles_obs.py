# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de las acciones sobre perfiles de OBS, con un doble que guarda
los pedidos como lo haría el WebSocket."""

import dataclasses
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from guyrapu.core import paths
from guyrapu.obs import ajustes_perfil, codificadores_obs, obs_cliente, perfiles_obs

PARAMETROS_DE_FABRICA = {
    ("Output", "Mode"): "Simple",
    ("SimpleOutput", "StreamEncoder"): "x264",
    ("SimpleOutput", "VBitrate"): "2500",
    ("SimpleOutput", "ABitrate"): "160",
    ("SimpleOutput", "Preset"): "veryfast",
    ("SimpleOutput", "DynamicBitrate"): "false",
    ("Output", "Reconnect"): "true",
    ("Output", "RetryDelay"): "2",
    ("Output", "MaxRetries"): "25",
    ("SimpleOutput", "RecFormat2"): "mkv",
    ("SimpleOutput", "RecQuality"): "Stream",
    ("SimpleOutput", "RecRB"): "false",
    ("SimpleOutput", "RecRBTime"): "20",
    ("Audio", "SampleRate"): "48000",
    ("Audio", "ChannelSetup"): "Stereo",
}

VIDEO_DE_FABRICA = {
    "baseWidth": 1920, "baseHeight": 1080,
    "outputWidth": 1280, "outputHeight": 720,
    "fpsNumerator": 30, "fpsDenominator": 1,
}


class ClienteFalso:
    """OBS falso: cada perfil tiene sus ajustes y los pedidos se registran."""

    def __init__(self, perfiles=("Uno",), actual="Uno", transmision=False,
                 grabacion=False, buffer=False):
        self.estado = {nombre: self._de_fabrica() for nombre in perfiles}
        self.actual = actual
        self.transmision = transmision
        self.grabacion = grabacion
        self.buffer = buffer
        self.llamadas = []
        self.fallar_en = None

    @staticmethod
    def _de_fabrica():
        return {
            "parametros": dict(PARAMETROS_DE_FABRICA),
            "video": dict(VIDEO_DE_FABRICA),
            "servicio": {
                "streamServiceType": "rtmp_custom",
                "streamServiceSettings": {"server": "", "key": ""},
            },
            "carpeta": "",
        }

    def configurar(self, perfil, *, parametros=None, video=None,
                   servicio=None, carpeta=None):
        estado = self.estado[perfil]
        if parametros:
            estado["parametros"].update(parametros)
        if video:
            estado["video"].update(video)
        if servicio is not None:
            estado["servicio"] = servicio
        if carpeta is not None:
            estado["carpeta"] = carpeta
        return self

    def _fallar(self, tipo):
        if self.fallar_en is None:
            return False
        tipo_falla, restantes = self.fallar_en
        if tipo != tipo_falla or restantes <= 0:
            return False
        self.fallar_en = None if restantes == 1 else (tipo_falla,
                                                       restantes - 1)
        return True

    def pedir(self, tipo, datos=None, parada=None):
        datos = dict(datos or {})
        self.llamadas.append((tipo, datos))
        if self._fallar(tipo):
            raise obs_cliente.ObsError("falla de prueba")
        estado = self.estado.get(self.actual, self._de_fabrica())
        if tipo == "GetStreamStatus":
            return {"responseData": {"outputActive": self.transmision}}
        if tipo == "GetRecordStatus":
            return {"responseData": {"outputActive": self.grabacion}}
        if tipo == "GetReplayBufferStatus":
            return {"responseData": {"outputActive": self.buffer}}
        if tipo == "GetProfileList":
            return {"responseData": {
                "profiles": list(self.estado),
                "currentProfileName": self.actual}}
        if tipo == "SetCurrentProfile":
            nombre = datos["profileName"]
            if nombre not in self.estado:
                raise obs_cliente.ObsError("600 not found")
            self.actual = nombre
            return {"responseData": {}}
        if tipo == "CreateProfile":
            nombre = datos["profileName"]
            if nombre in self.estado:
                raise obs_cliente.ObsError("601 already exists")
            self.estado[nombre] = self._de_fabrica()
            self.actual = nombre
            return {"responseData": {}}
        if tipo == "RemoveProfile":
            nombre = datos["profileName"]
            if nombre not in self.estado:
                raise obs_cliente.ObsError("600 not found")
            if self.actual == nombre:
                self.actual = next(n for n in self.estado if n != nombre)
            del self.estado[nombre]
            return {"responseData": {}}
        if tipo == "GetVideoSettings":
            return {"responseData": dict(estado["video"])}
        if tipo == "SetVideoSettings":
            estado["video"].update(datos)
            return {"responseData": {}}
        if tipo == "GetStreamServiceSettings":
            return {"responseData": {
                "streamServiceType": estado["servicio"]["streamServiceType"],
                "streamServiceSettings": dict(
                    estado["servicio"]["streamServiceSettings"])}}
        if tipo == "SetStreamServiceSettings":
            estado["servicio"] = {
                "streamServiceType": datos["streamServiceType"],
                "streamServiceSettings": dict(
                    datos.get("streamServiceSettings", {})),
            }
            return {"responseData": {}}
        if tipo == "GetProfileParameter":
            clave = (datos.get("parameterCategory"),
                     datos.get("parameterName"))
            return {"responseData": {
                "parameterValue": estado["parametros"].get(clave, ""),
                "defaultParameterValue": ""}}
        if tipo == "SetProfileParameter":
            clave = (datos.get("parameterCategory"),
                     datos.get("parameterName"))
            estado["parametros"][clave] = datos.get("parameterValue")
            return {"responseData": {}}
        if tipo == "GetRecordDirectory":
            return {"responseData": {"recordDirectory": estado["carpeta"]}}
        if tipo == "SetRecordDirectory":
            estado["carpeta"] = datos["recordDirectory"]
            return {"responseData": {}}
        return {"responseData": {}}

    def tipos(self):
        return [tipo for tipo, _ in self.llamadas]

    def cambios_de_perfil(self):
        return [datos["profileName"] for tipo, datos in self.llamadas
                if tipo == "SetCurrentProfile"]


def ajustes_de_prueba(**cambios):
    return dataclasses.replace(ajustes_perfil.valores_iniciales(False, "x264"),
                               **cambios)


class TestLeer(unittest.TestCase):

    def test_p2_lee_otro_perfil_y_vuelve_al_anterior(self):
        cliente = ClienteFalso(("A", "B"), actual="A")
        cliente.configurar("A", parametros={("SimpleOutput", "VBitrate"): "1111"})
        cliente.configurar(
            "B",
            parametros={
                ("SimpleOutput", "StreamEncoder"): "qsv",
                ("SimpleOutput", "VBitrate"): "4000",
                ("SimpleOutput", "ABitrate"): "192",
                ("SimpleOutput", "QSVPreset"): "quality",
            },
            video={"baseWidth": 1080, "baseHeight": 1920,
                   "outputWidth": 720, "outputHeight": 1280,
                   "fpsNumerator": 60, "fpsDenominator": 1},
            servicio={"streamServiceType": "rtmp_custom",
                      "streamServiceSettings": {"server": "rtmp://b",
                                                "key": "clave-b"}},
            carpeta="C:\\Grabaciones\\B")
        ajustes = perfiles_obs.leer_ajustes(cliente, "B")
        self.assertEqual(cliente.actual, "A")
        self.assertEqual(cliente.cambios_de_perfil(), ["B", "A"])
        self.assertEqual((ajustes.ancho_lienzo, ajustes.alto_lienzo),
                         (1080, 1920))
        self.assertEqual((ajustes.ancho_salida, ajustes.alto_salida),
                         (720, 1280))
        self.assertEqual(ajustes.fps, 60)
        self.assertEqual(ajustes.servidor, "rtmp://b")
        self.assertEqual(ajustes.clave, "clave-b")
        self.assertEqual(ajustes.codificador, "qsv")
        self.assertEqual(ajustes.bitrate_video, 4000)
        self.assertEqual(ajustes.bitrate_audio, 192)
        self.assertEqual(ajustes.preset, "quality")
        self.assertEqual(ajustes.carpeta_grabacion, "C:\\Grabaciones\\B")

    def test_p2_lee_el_actual_sin_cambiar_de_perfil(self):
        cliente = ClienteFalso(("A", "B"), actual="B")
        ajustes = perfiles_obs.leer_ajustes(cliente, "B")
        self.assertEqual(ajustes.codificador, "x264")
        self.assertEqual(cliente.cambios_de_perfil(), [])

    def test_p2_falla_si_el_perfil_no_existe(self):
        cliente = ClienteFalso(("A",), actual="A")
        with self.assertRaisesRegex(obs_cliente.ObsError, "no tiene un perfil"):
            perfiles_obs.leer_ajustes(cliente, "Fantasma")
        self.assertEqual(cliente.actual, "A")

    def test_p2_vuelve_al_perfil_si_falla_a_mitad(self):
        cliente = ClienteFalso(("A", "B"), actual="A")
        cliente.fallar_en = ("GetProfileParameter", 1)
        with self.assertRaises(obs_cliente.ObsError):
            perfiles_obs.leer_ajustes(cliente, "B")
        self.assertEqual(cliente.actual, "A")


class TestGuardar(unittest.TestCase):

    def test_p3_guarda_en_otro_perfil_y_vuelve_al_anterior(self):
        cliente = ClienteFalso(("A", "B"), actual="A")
        ajustes = ajustes_de_prueba(
            codificador="qsv", preset="quality", bitrate_video=3500,
            bitrate_audio=192, fps=50, ancho_lienzo=1600, alto_lienzo=900,
            ancho_salida=1280, alto_salida=720,
            servidor="rtmp://nuevo", clave="clave-nueva",
            carpeta_grabacion="C:\\Nueva")
        perfiles_obs.guardar_ajustes(cliente, ajustes, "B")
        self.assertEqual(cliente.actual, "A")
        self.assertEqual(cliente.cambios_de_perfil(), ["B", "A"])
        guardado = cliente.estado["B"]
        self.assertEqual(guardado["parametros"][
            ("SimpleOutput", "StreamEncoder")], "qsv")
        self.assertEqual(guardado["parametros"][
            ("SimpleOutput", "VBitrate")], "3500")
        self.assertEqual(guardado["parametros"][
            ("SimpleOutput", "QSVPreset")], "quality")
        self.assertEqual(guardado["video"]["baseWidth"], 1600)
        self.assertEqual(guardado["video"]["fpsNumerator"], 50)
        self.assertEqual(guardado["servicio"]["streamServiceSettings"],
                         {"server": "rtmp://nuevo", "key": "clave-nueva"})
        self.assertEqual(guardado["carpeta"], "C:\\Nueva")

    def test_p3_guardar_en_el_actual_lo_recarga(self):
        cliente = ClienteFalso(("A", "B"), actual="A")
        perfiles_obs.guardar_ajustes(cliente, ajustes_de_prueba(), "A")
        self.assertEqual(cliente.actual, "A")
        self.assertEqual(cliente.cambios_de_perfil(), ["B", "A"])

    def test_p3_con_un_solo_perfil_recarga_con_uno_temporal(self):
        cliente = ClienteFalso(("A",), actual="A")
        perfiles_obs.guardar_ajustes(cliente, ajustes_de_prueba(), "A")
        creados = [datos["profileName"] for tipo, datos in cliente.llamadas
                   if tipo == "CreateProfile"]
        borrados = [datos["profileName"] for tipo, datos in cliente.llamadas
                    if tipo == "RemoveProfile"]
        self.assertEqual(len(creados), 1)
        self.assertEqual(borrados, creados)
        self.assertNotIn(creados[0], cliente.estado)
        self.assertEqual(cliente.actual, "A")

    def test_p3_falla_si_el_perfil_no_existe(self):
        cliente = ClienteFalso(("A",), actual="A")
        with self.assertRaisesRegex(obs_cliente.ObsError, "no tiene un perfil"):
            perfiles_obs.guardar_ajustes(cliente, ajustes_de_prueba(),
                                         "Fantasma")
        self.assertNotIn("SetCurrentProfile", cliente.tipos())

    def test_p3_vuelve_al_perfil_si_falla_a_mitad(self):
        cliente = ClienteFalso(("A", "B"), actual="A")
        cliente.fallar_en = ("SetProfileParameter", 2)
        with self.assertRaises(obs_cliente.ObsError):
            perfiles_obs.guardar_ajustes(cliente, ajustes_de_prueba(), "B")
        self.assertEqual(cliente.actual, "A")

    def test_p3_servicio_personalizado_escribe_servidor_y_clave(self):
        cliente = ClienteFalso(("A",), actual="A")
        ajustes = ajustes_de_prueba(servidor="rtmp://x", clave="k")
        perfiles_obs.guardar_ajustes(cliente, ajustes, "A")
        self.assertEqual(cliente.estado["A"]["servicio"], {
            "streamServiceType": "rtmp_custom",
            "streamServiceSettings": {"server": "rtmp://x", "key": "k"},
        })

    def test_p3_servicio_conocido_conserva_tipo_y_servidor(self):
        cliente = ClienteFalso(("A",), actual="A")
        cliente.configurar("A", servicio={
            "streamServiceType": "YouTube",
            "streamServiceSettings": {"server": "rtmp://yt", "key": "vieja",
                                      "extra": "se conserva"}})
        ajustes = ajustes_de_prueba(servidor="rtmp://otro", clave="nueva")
        perfiles_obs.guardar_ajustes(cliente, ajustes, "A")
        self.assertEqual(cliente.estado["A"]["servicio"], {
            "streamServiceType": "YouTube",
            "streamServiceSettings": {"server": "rtmp://yt", "key": "nueva",
                                      "extra": "se conserva"},
        })


class TestCrear(unittest.TestCase):

    def test_p4_crea_horizontal_con_valores_iniciales(self):
        cliente = ClienteFalso(("Viejo",), actual="Viejo")
        ajustes = perfiles_obs.crear_perfil(
            cliente, "Nuevo", vertical=False,
            codificadores=("x264", "amd", "qsv"))
        self.assertEqual(cliente.actual, "Nuevo")
        self.assertIn("Nuevo", cliente.estado)
        self.assertEqual((ajustes.ancho_lienzo, ajustes.alto_lienzo),
                         (1920, 1080))
        self.assertEqual((ajustes.ancho_salida, ajustes.alto_salida),
                         (1280, 720))
        guardado = cliente.estado["Nuevo"]
        self.assertEqual(guardado["video"]["baseWidth"], 1920)
        self.assertEqual(guardado["video"]["fpsNumerator"], 30)
        self.assertEqual(guardado["parametros"][
            ("SimpleOutput", "StreamEncoder")], "qsv")
        self.assertEqual(guardado["parametros"][
            ("SimpleOutput", "QSVPreset")], "balanced")
        self.assertEqual(guardado["parametros"][
            ("SimpleOutput", "VBitrate")], "2500")
        self.assertEqual(guardado["parametros"][
            ("SimpleOutput", "ABitrate")], "160")
        self.assertEqual(guardado["parametros"][
            ("SimpleOutput", "RecFormat2")], "mkv")
        self.assertEqual(guardado["parametros"][
            ("SimpleOutput", "RecQuality")], "Stream")
        self.assertEqual(guardado["parametros"][
            ("SimpleOutput", "RecRB")], "false")
        self.assertEqual(guardado["parametros"][
            ("SimpleOutput", "RecRBTime")], "30")
        self.assertEqual(guardado["parametros"][
            ("Audio", "SampleRate")], "48000")
        self.assertEqual(guardado["parametros"][
            ("Audio", "ChannelSetup")], "Stereo")

    def test_p4_crea_vertical(self):
        cliente = ClienteFalso(("Viejo",), actual="Viejo")
        ajustes = perfiles_obs.crear_perfil(
            cliente, "Vertical", vertical=True, codificadores=("x264",))
        self.assertEqual((ajustes.ancho_lienzo, ajustes.alto_lienzo),
                         (1080, 1920))
        self.assertEqual((ajustes.ancho_salida, ajustes.alto_salida),
                         (720, 1280))
        self.assertEqual(cliente.estado["Vertical"]["video"]["baseWidth"],
                         1080)

    def test_p4_usa_los_codificadores_disponibles_si_no_se_los_dan(self):
        cliente = ClienteFalso(("Viejo",), actual="Viejo")
        with mock.patch.object(codificadores_obs, "codificadores_disponibles",
                               return_value=("x264", "nvenc")):
            ajustes = perfiles_obs.crear_perfil(cliente, "Nuevo")
        self.assertEqual(ajustes.codificador, "nvenc")
        self.assertEqual(cliente.estado["Nuevo"]["parametros"][
            ("SimpleOutput", "NVENCPreset2")], "p4")

    def test_p4_falla_si_el_nombre_ya_existe(self):
        cliente = ClienteFalso(("A", "B"), actual="A")
        with self.assertRaisesRegex(obs_cliente.ObsError, "Ya existe"):
            perfiles_obs.crear_perfil(cliente, "B",
                                      codificadores=("x264",))
        self.assertNotIn("CreateProfile", cliente.tipos())
        self.assertEqual(cliente.actual, "A")


class TestDuplicar(unittest.TestCase):

    def test_p5_duplica_con_todos_los_ajustes(self):
        cliente = ClienteFalso(("A", "Origen"), actual="A")
        cliente.configurar(
            "Origen",
            parametros={
                ("SimpleOutput", "StreamEncoder"): "nvenc",
                ("SimpleOutput", "NVENCPreset2"): "p6",
                ("SimpleOutput", "VBitrate"): "5000",
                ("SimpleOutput", "ABitrate"): "256",
                ("SimpleOutput", "DynamicBitrate"): "true",
                ("Output", "Reconnect"): "false",
                ("Output", "RetryDelay"): "8",
                ("Output", "MaxRetries"): "10",
                ("SimpleOutput", "RecFormat2"): "mov",
                ("SimpleOutput", "RecQuality"): "HQ",
                ("SimpleOutput", "RecRB"): "true",
                ("SimpleOutput", "RecRBTime"): "45",
                ("Audio", "SampleRate"): "44100",
                ("Audio", "ChannelSetup"): "Mono",
            },
            video={"baseWidth": 1080, "baseHeight": 1920,
                   "outputWidth": 720, "outputHeight": 1280,
                   "fpsNumerator": 48, "fpsDenominator": 1},
            servicio={"streamServiceType": "rtmp_custom",
                      "streamServiceSettings": {"server": "rtmp://origen",
                                                "key": "clave-origen"}},
            carpeta="C:\\Origen")
        ajustes = perfiles_obs.duplicar_perfil(cliente, "Origen", "Copia")
        self.assertEqual(cliente.actual, "A")
        self.assertEqual(ajustes.codificador, "nvenc")
        self.assertEqual(ajustes.preset, "p6")
        destino = cliente.estado["Copia"]
        for categoria, nombre, valor in ajustes_perfil.parametros_obs(ajustes):
            self.assertEqual(destino["parametros"][(categoria, nombre)],
                             valor,
                             f"{categoria}/{nombre}")
        self.assertEqual(destino["video"], cliente.estado["Origen"]["video"])
        self.assertEqual(destino["servicio"], cliente.estado["Origen"]["servicio"])
        self.assertEqual(destino["carpeta"], "C:\\Origen")

    def test_p5_falla_si_el_nuevo_ya_existe(self):
        cliente = ClienteFalso(("A", "Origen", "Copia"), actual="A")
        with self.assertRaisesRegex(obs_cliente.ObsError, "Ya existe"):
            perfiles_obs.duplicar_perfil(cliente, "Origen", "Copia")
        self.assertEqual(cliente.actual, "A")
        self.assertNotIn("CreateProfile", cliente.tipos())


class TestEliminar(unittest.TestCase):

    def test_p6_elimina_otro_perfil(self):
        cliente = ClienteFalso(("A", "B"), actual="A")
        perfiles_obs.eliminar_perfil(cliente, "B")
        self.assertNotIn("B", cliente.estado)
        self.assertEqual(cliente.actual, "A")
        self.assertIn("RemoveProfile", cliente.tipos())

    def test_p6_no_elimina_el_actual(self):
        cliente = ClienteFalso(("A", "B"), actual="A")
        with self.assertRaisesRegex(obs_cliente.ObsError, "está en uso"):
            perfiles_obs.eliminar_perfil(cliente, "A")
        self.assertNotIn("RemoveProfile", cliente.tipos())

    def test_p6_no_elimina_el_unico(self):
        cliente = ClienteFalso(("A",), actual="A")
        with self.assertRaisesRegex(obs_cliente.ObsError, "el único"):
            perfiles_obs.eliminar_perfil(cliente, "A")
        self.assertNotIn("RemoveProfile", cliente.tipos())

    def test_p6_falla_si_el_perfil_no_existe(self):
        cliente = ClienteFalso(("A", "B"), actual="A")
        with self.assertRaisesRegex(obs_cliente.ObsError, "no tiene un perfil"):
            perfiles_obs.eliminar_perfil(cliente, "Fantasma")
        self.assertNotIn("RemoveProfile", cliente.tipos())


class TestCambiar(unittest.TestCase):

    def test_p7_cambia_al_perfil_elegido(self):
        cliente = ClienteFalso(("A", "B"), actual="A")
        perfiles_obs.cambiar_perfil(cliente, "B")
        self.assertEqual(cliente.actual, "B")
        self.assertEqual(cliente.cambios_de_perfil(), ["B"])

    def test_p7_falla_si_el_perfil_no_existe(self):
        cliente = ClienteFalso(("A",), actual="A")
        with self.assertRaisesRegex(obs_cliente.ObsError, "no tiene un perfil"):
            perfiles_obs.cambiar_perfil(cliente, "Fantasma")
        self.assertEqual(cliente.actual, "A")
        self.assertNotIn("SetCurrentProfile", cliente.tipos())


class TestAvanzado(unittest.TestCase):

    def _carpeta_de_perfiles(self, temporal, nombre, bitrate):
        base = Path(temporal) / "profiles"
        carpeta = base / "carpeta-cualquiera"
        carpeta.mkdir(parents=True)
        (carpeta / "basic.ini").write_text(
            "[General]\nName=" + nombre + "\n", encoding="utf-8-sig")
        (carpeta / "streamEncoder.json").write_text(
            '{"bitrate": ' + str(bitrate) + ', "rate_control": "CBR"}',
            encoding="utf-8")
        return base

    def test_p8_detecta_avanzado_y_pasa_a_sencillo(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = self._carpeta_de_perfiles(tmp, "Avanzado", 4500)
            cliente = ClienteFalso(("A", "Avanzado"), actual="A")
            cliente.configurar("Avanzado", parametros={
                ("Output", "Mode"): "Advanced",
                ("AdvOut", "Encoder"): "obs_nvenc_h264_tex"})
            with mock.patch.object(paths, "carpeta_obs",
                                   return_value=base):
                convertido = perfiles_obs.pasar_a_sencillo(cliente, "Avanzado")
            self.assertTrue(convertido)
            self.assertEqual(cliente.actual, "A")
            guardado = cliente.estado["Avanzado"]["parametros"]
            self.assertEqual(guardado[("Output", "Mode")], "Simple")
            self.assertEqual(guardado[("SimpleOutput", "StreamEncoder")],
                             "nvenc")
            self.assertEqual(guardado[("SimpleOutput", "VBitrate")], "4500")
            escritos = [datos.get("parameterName") for tipo, datos
                        in cliente.llamadas if tipo == "SetProfileParameter"]
            self.assertEqual(escritos,
                             ["StreamEncoder", "VBitrate", "Mode"])

    def test_p8_perfil_sencillo_no_cambia_nada(self):
        cliente = ClienteFalso(("A", "Sencillo"), actual="A")
        cliente.configurar("Sencillo", parametros={("Output", "Mode"): "Simple"})
        convertido = perfiles_obs.pasar_a_sencillo(cliente, "Sencillo")
        self.assertFalse(convertido)
        self.assertEqual(cliente.actual, "A")
        self.assertNotIn("SetProfileParameter", cliente.tipos())

    def test_p8_codificador_desconocido_deja_x264(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = self._carpeta_de_perfiles(tmp, "Avanzado", 3000)
            cliente = ClienteFalso(("A", "Avanzado"), actual="A")
            cliente.configurar("Avanzado", parametros={
                ("Output", "Mode"): "Advanced",
                ("AdvOut", "Encoder"): "obs_desconocido"})
            with mock.patch.object(paths, "carpeta_obs",
                                   return_value=base):
                perfiles_obs.pasar_a_sencillo(cliente, "Avanzado")
            self.assertEqual(cliente.estado["Avanzado"]["parametros"][
                ("SimpleOutput", "StreamEncoder")], "x264")
            self.assertEqual(cliente.estado["Avanzado"]["parametros"][
                ("SimpleOutput", "VBitrate")], "3000")

    def test_p8_sin_streamencoder_usa_el_bitrate_inicial(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "profiles"
            (base / "otra").mkdir(parents=True)
            cliente = ClienteFalso(("A", "Avanzado"), actual="A")
            cliente.configurar("Avanzado", parametros={
                ("Output", "Mode"): "Advanced",
                ("AdvOut", "Encoder"): "obs_x264"})
            with mock.patch.object(paths, "carpeta_obs",
                                   return_value=base):
                perfiles_obs.pasar_a_sencillo(cliente, "Avanzado")
            self.assertEqual(cliente.estado["Avanzado"]["parametros"][
                ("SimpleOutput", "VBitrate")], "2500")

    def test_p8_en_el_perfil_actual_lo_recarga(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = self._carpeta_de_perfiles(tmp, "Avanzado", 4000)
            cliente = ClienteFalso(("A", "Avanzado"), actual="Avanzado")
            cliente.configurar("Avanzado", parametros={
                ("Output", "Mode"): "Advanced",
                ("AdvOut", "Encoder"): "obs_x264"})
            with mock.patch.object(paths, "carpeta_obs",
                                   return_value=base):
                perfiles_obs.pasar_a_sencillo(cliente)
            self.assertEqual(cliente.actual, "Avanzado")
            self.assertEqual(cliente.cambios_de_perfil(), ["A", "Avanzado"])

    def test_p8_dice_si_esta_en_avanzado_y_vuelve(self):
        cliente = ClienteFalso(("A", "Avanzado", "Sencillo"), actual="A")
        cliente.configurar("Avanzado", parametros={
            ("Output", "Mode"): "Advanced"})
        cliente.configurar("Sencillo", parametros={
            ("Output", "Mode"): "Simple"})
        self.assertTrue(perfiles_obs.esta_en_avanzado(cliente, "Avanzado"))
        self.assertEqual(cliente.actual, "A")
        self.assertFalse(perfiles_obs.esta_en_avanzado(cliente, "Sencillo"))
        self.assertEqual(cliente.actual, "A")


class TestSinSalidas(unittest.TestCase):

    ACCIONES = (
        ("leer", lambda cliente, ajustes: perfiles_obs.leer_ajustes(
            cliente, "B")),
        ("guardar", lambda cliente, ajustes: perfiles_obs.guardar_ajustes(
            cliente, ajustes, "B")),
        ("crear", lambda cliente, ajustes: perfiles_obs.crear_perfil(
            cliente, "C", codificadores=("x264",))),
        ("duplicar", lambda cliente, ajustes: perfiles_obs.duplicar_perfil(
            cliente, "A", "C")),
        ("eliminar", lambda cliente, ajustes: perfiles_obs.eliminar_perfil(
            cliente, "B")),
        ("cambiar", lambda cliente, ajustes: perfiles_obs.cambiar_perfil(
            cliente, "B")),
        ("avanzado", lambda cliente, ajustes: perfiles_obs.esta_en_avanzado(
            cliente, "B")),
        ("sencillo", lambda cliente, ajustes: perfiles_obs.pasar_a_sencillo(
            cliente, "B")),
    )
    PERMISIONES = frozenset({"GetStreamStatus", "GetRecordStatus",
                             "GetReplayBufferStatus"})

    def test_p10_ninguna_accion_con_una_salida_en_marcha(self):
        for salida in ("transmision", "grabacion", "buffer"):
            for nombre, accion in self.ACCIONES:
                with self.subTest(salida=salida, accion=nombre):
                    cliente = ClienteFalso(("A", "B"), actual="A",
                                           **{salida: True})
                    with self.assertRaises(obs_cliente.ObsError) as contexto:
                        accion(cliente, ajustes_de_prueba())
                    self.assertIn("perfil de OBS", str(contexto.exception))
                    self.assertLessEqual(set(cliente.tipos()),
                                         self.PERMISIONES)


if __name__ == "__main__":
    unittest.main()
