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
from tests.test_perfil_en_disco import crear_perfil

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
                raise obs_cliente.ObsError("600 profile in use")
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


class ClienteQueMiraElArchivo(ClienteFalso):
    """Anota el audio del archivo del destino justo al cambiar de perfil."""

    def __init__(self, *args, ruta=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.ruta = ruta
        self.audio_al_cambiar = None

    def pedir(self, tipo, datos=None, parada=None):
        if tipo == "SetCurrentProfile":
            self.audio_al_cambiar = audio_de(self.ruta)
        return super().pedir(tipo, datos, parada)


class ClienteQueTardaEnQuitar(ClienteFalso):
    """Sigue listando el perfil eliminado durante una consulta, como OBS."""

    def __init__(self, *args, consultas=1, **kwargs):
        super().__init__(*args, **kwargs)
        self._retraso = consultas
        self._consultas_retraso = 0
        self._recien_eliminado = ""
        self.listados_despues = []

    def pedir(self, tipo, datos=None, parada=None):
        if tipo == "RemoveProfile":
            respuesta = super().pedir(tipo, datos, parada)
            self._recien_eliminado = (datos or {}).get("profileName", "")
            self._consultas_retraso = self._retraso
            return respuesta
        if tipo == "GetProfileList":
            respuesta = super().pedir(tipo, datos, parada)
            if self._recien_eliminado:
                if self._consultas_retraso > 0:
                    self._consultas_retraso -= 1
                    respuesta["responseData"]["profiles"].append(
                        self._recien_eliminado)
                self.listados_despues.append(
                    list(respuesta["responseData"]["profiles"]))
            return respuesta
        return super().pedir(tipo, datos, parada)


class ClienteConVideoTomado(ClienteFalso):
    """Rechaza SetVideoSettings con el 500 las primeras veces, como OBS."""

    def __init__(self, *args, veces=2, **kwargs):
        super().__init__(*args, **kwargs)
        self.veces_500 = veces

    def pedir(self, tipo, datos=None, parada=None):
        if tipo == "SetVideoSettings" and self.veces_500 > 0:
            self.veces_500 -= 1
            self.llamadas.append((tipo, dict(datos or {})))
            raise obs_cliente.ObsError("500 OutputRunning", codigo=500)
        return super().pedir(tipo, datos, parada)


def ajustes_de_prueba(**cambios):
    return dataclasses.replace(ajustes_perfil.valores_iniciales(False, "x264"),
                               **cambios)


class TestListar(unittest.TestCase):

    def test_listar_devuelve_los_perfiles_y_el_actual(self):
        cliente = ClienteFalso(("A", "B"), actual="B")
        self.assertEqual(perfiles_obs.listar_perfiles(cliente),
                         (["A", "B"], "B"))


class TestLeerParaEditar(unittest.TestCase):

    def test_devuelve_ajustes_avanzado_y_servicio_personalizado(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "profiles"
            base.mkdir()
            crear_perfil(base, "B", {
                "Output": {"Mode": "Advanced"},
                "SimpleOutput": {"VBitrate": "4000"},
            }, servicio={"type": "rtmp_custom",
                         "settings": {"server": "rtmp://b", "key": "kb"}})
            cliente = ClienteFalso(("A", "B"), actual="A")
            with mock.patch.object(paths, "carpeta_obs", return_value=base):
                ajustes, avanzado, personalizado = (
                    perfiles_obs.leer_para_editar(cliente, "B"))
        self.assertTrue(avanzado)
        self.assertTrue(personalizado)
        self.assertEqual(ajustes.bitrate_video, 4000)
        self.assertEqual(cliente.actual, "A")
        self.assertEqual(cliente.cambios_de_perfil(), [])


class TestMonitoreo(unittest.TestCase):

    def test_guardar_escribe_el_dispositivo_del_perfil(self):
        cliente = ClienteFalso(("A",), actual="A")
        ajustes = ajustes_de_prueba(monitoreo_id="{0.0.0.4}",
                                   monitoreo_nombre="Altavoces")
        perfiles_obs.guardar_ajustes(cliente, ajustes, "A")
        guardado = cliente.estado["A"]["parametros"]
        self.assertEqual(guardado[("Audio", "MonitoringDeviceId")],
                         "{0.0.0.4}")
        self.assertEqual(guardado[("Audio", "MonitoringDeviceName")],
                         "Altavoces")


class TestLeer(unittest.TestCase):

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


class TestGuardar(unittest.TestCase):

    def test_p3_guarda_en_otro_perfil_sin_cambiar_de_perfil(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "profiles"
            base.mkdir()
            crear_perfil(base, "B", {
                "SimpleOutput": {"StreamEncoder": "x264",
                                 "VBitrate": "2500"},
                "Video": {"BaseCX": "1920", "BaseCY": "1080",
                          "OutputCX": "1280", "OutputCY": "720",
                          "FPSType": "2", "FPSNum": "30", "FPSDen": "1"},
            })
            cliente = ClienteFalso(("A", "B"), actual="A")
            ajustes = ajustes_de_prueba(
                codificador="qsv", preset="quality", bitrate_video=3500,
                bitrate_audio=192, fps=50, ancho_lienzo=1600, alto_lienzo=900,
                ancho_salida=1280, alto_salida=720,
                servidor="rtmp://nuevo", clave="clave-nueva",
                carpeta_grabacion="C:\\Nueva")
            with mock.patch.object(paths, "carpeta_obs", return_value=base):
                perfiles_obs.guardar_ajustes(cliente, ajustes, "B")
                guardado = perfiles_obs.leer_ajustes(cliente, "B")
        self.assertEqual(cliente.actual, "A")
        self.assertEqual(cliente.cambios_de_perfil(), [])
        self.assertEqual(guardado.codificador, "qsv")
        self.assertEqual(guardado.bitrate_video, 3500)
        self.assertEqual(guardado.preset, "quality")
        self.assertEqual(guardado.ancho_lienzo, 1600)
        self.assertEqual(guardado.fps, 50)
        self.assertEqual((guardado.servidor, guardado.clave),
                         ("rtmp://nuevo", "clave-nueva"))
        self.assertEqual(guardado.carpeta_grabacion, "C:\\Nueva")

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

    def test_p3_vuelve_al_perfil_si_falla_a_mitad(self):
        cliente = ClienteFalso(("A",), actual="A")
        cliente.fallar_en = ("SetCurrentProfile", 1)
        with self.assertRaises(obs_cliente.ObsError):
            perfiles_obs.guardar_ajustes(cliente, ajustes_de_prueba(), "A")
        self.assertEqual(cliente.actual, "A")

    def test_p3_falla_si_el_perfil_no_existe(self):
        cliente = ClienteFalso(("A",), actual="A")
        with self.assertRaisesRegex(obs_cliente.ObsError, "no tiene un perfil"):
            perfiles_obs.guardar_ajustes(cliente, ajustes_de_prueba(),
                                         "Fantasma")
        self.assertNotIn("SetCurrentProfile", cliente.tipos())

    def test_p3_si_falta_la_carpeta_dice_que_perfil(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "profiles"
            base.mkdir()
            cliente = ClienteFalso(("A", "B"), actual="A")
            with mock.patch.object(paths, "carpeta_obs", return_value=base):
                with self.assertRaisesRegex(obs_cliente.ObsError,
                                            "perfil B"):
                    perfiles_obs.guardar_ajustes(
                        cliente, ajustes_de_prueba(), "B")
        self.assertEqual(cliente.actual, "A")
        self.assertEqual(cliente.cambios_de_perfil(), [])

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

    def test_p3_con_carpeta_vacia_no_pide_carpeta_de_grabacion(self):
        cliente = ClienteFalso(("A",), actual="A")
        perfiles_obs.guardar_ajustes(cliente, ajustes_de_prueba(), "A")
        self.assertNotIn("SetRecordDirectory", cliente.tipos())

    def test_p3_con_servidor_y_clave_vacios_no_cambia_el_servicio(self):
        cliente = ClienteFalso(("A",), actual="A")
        ajustes = ajustes_de_prueba(servidor="", clave="")
        perfiles_obs.guardar_ajustes(cliente, ajustes, "A")
        self.assertNotIn("SetStreamServiceSettings", cliente.tipos())

    def test_p3_reintenta_si_obs_todavia_tiene_tomado_el_video(self):
        cliente = ClienteConVideoTomado(("A",), actual="A")
        ajustes = ajustes_de_prueba(bitrate_video=3200)
        with mock.patch.object(obs_cliente.time, "sleep", lambda _segundos: None):
            perfiles_obs.guardar_ajustes(cliente, ajustes, "A")
        self.assertEqual(cliente.estado["A"]["parametros"][
            ("SimpleOutput", "VBitrate")], "3200")
        self.assertEqual(cliente.tipos().count("SetVideoSettings"), 3)


class TestCrear(unittest.TestCase):

    def test_p4_crea_horizontal_con_valores_iniciales(self):
        cliente = ClienteFalso(("Viejo",), actual="Viejo")
        ajustes = perfiles_obs.crear_perfil(
            cliente, "Nuevo", vertical=False,
            codificadores=("x264", "amd", "qsv"))
        self.assertEqual(cliente.actual, "Viejo")
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

    def test_p4_con_carpeta_vacia_no_pide_carpeta_de_grabacion(self):
        cliente = ClienteFalso(("A",), actual="A")
        ajustes = perfiles_obs.crear_perfil(
            cliente, "Nuevo", codificadores=("x264",))
        self.assertEqual(ajustes.carpeta_grabacion, "")
        self.assertNotIn("SetRecordDirectory", cliente.tipos())

    def test_p4_si_falla_a_medias_borra_el_perfil_nuevo(self):
        cliente = ClienteFalso(("A", "B"), actual="A")
        cliente.fallar_en = ("SetProfileParameter", 2)
        with self.assertRaises(obs_cliente.ObsError):
            perfiles_obs.crear_perfil(cliente, "Nuevo",
                                      codificadores=("x264",))
        self.assertEqual(set(cliente.estado), {"A", "B"})
        self.assertEqual(cliente.actual, "A")
        self.assertNotIn("Nuevo", cliente.estado)

    def test_p4_deja_el_perfil_que_estaba(self):
        cliente = ClienteFalso(("A", "B"), actual="B")
        perfiles_obs.crear_perfil(cliente, "Nuevo",
                                  codificadores=("x264",))
        self.assertEqual(cliente.actual, "B")
        self.assertIn("Nuevo", cliente.estado)

    def test_p2_el_creado_queda_con_el_audio_del_perfil_en_uso(self):
        cliente = ClienteFalso(("Viejo",), actual="Viejo")
        cliente.configurar("Viejo", parametros={
            ("Audio", "SampleRate"): "44100",
            ("Audio", "ChannelSetup"): "Mono"})
        perfiles_obs.crear_perfil(cliente, "Nuevo",
                                  codificadores=("x264",))
        self.assertEqual(cliente.estado["Nuevo"]["parametros"][
            ("Audio", "SampleRate")], "44100")
        self.assertEqual(cliente.estado["Nuevo"]["parametros"][
            ("Audio", "ChannelSetup")], "Mono")


class TestDuplicar(unittest.TestCase):

    def test_p5_duplica_con_todos_los_ajustes(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "profiles"
            base.mkdir()
            crear_perfil(base, "Origen", {
                "SimpleOutput": {
                    "StreamEncoder": "nvenc", "NVENCPreset2": "p6",
                    "VBitrate": "5000", "ABitrate": "256",
                    "DynamicBitrate": "true", "RecFormat2": "mov",
                    "RecQuality": "HQ", "RecRB": "true", "RecRBTime": "45",
                    "FilePath": r"C:\Origen",
                },
                "Output": {"Reconnect": "false", "RetryDelay": "8",
                           "MaxRetries": "10"},
                "Video": {"BaseCX": "1080", "BaseCY": "1920",
                          "OutputCX": "720", "OutputCY": "1280",
                          "FPSType": "2", "FPSNum": "48", "FPSDen": "1"},
                "Audio": {"SampleRate": "44100", "ChannelSetup": "Mono",
                          "MonitoringDeviceId": "{0.0.0.5}",
                          "MonitoringDeviceName": "Auriculares"},
            }, servicio={"type": "rtmp_custom",
                         "settings": {"server": "rtmp://origen",
                                      "key": "clave-origen"}})
            cliente = ClienteFalso(("A", "Origen"), actual="A")
            with mock.patch.object(paths, "carpeta_obs", return_value=base):
                ajustes = perfiles_obs.duplicar_perfil(
                    cliente, "Origen", "Copia")
        self.assertEqual(cliente.actual, "A")
        self.assertNotIn("Origen", cliente.cambios_de_perfil())
        self.assertEqual(ajustes.codificador, "nvenc")
        self.assertEqual(ajustes.preset, "p6")
        destino = cliente.estado["Copia"]
        for categoria, nombre, valor in ajustes_perfil.parametros_obs(ajustes):
            self.assertEqual(destino["parametros"][(categoria, nombre)],
                             valor,
                             f"{categoria}/{nombre}")
        self.assertEqual(destino["video"]["baseWidth"], 1080)
        self.assertEqual(destino["video"]["fpsNumerator"], 48)
        self.assertEqual(destino["servicio"]["streamServiceSettings"],
                         {"server": "rtmp://origen", "key": "clave-origen"})
        self.assertEqual(destino["carpeta"], "C:\\Origen")

    def test_p5_falla_si_el_nuevo_ya_existe(self):
        cliente = ClienteFalso(("A", "Origen", "Copia"), actual="A")
        with self.assertRaisesRegex(obs_cliente.ObsError, "Ya existe"):
            perfiles_obs.duplicar_perfil(cliente, "Origen", "Copia")
        self.assertEqual(cliente.actual, "A")
        self.assertNotIn("CreateProfile", cliente.tipos())

    def test_p5_si_falla_a_medias_borra_el_perfil_nuevo(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "profiles"
            base.mkdir()
            crear_perfil(base, "Origen", {})
            cliente = ClienteFalso(("A", "Origen"), actual="A")
            cliente.fallar_en = ("SetProfileParameter", 2)
            with mock.patch.object(paths, "carpeta_obs", return_value=base):
                with self.assertRaises(obs_cliente.ObsError):
                    perfiles_obs.duplicar_perfil(cliente, "Origen", "Copia")
        self.assertEqual(set(cliente.estado), {"A", "Origen"})
        self.assertEqual(cliente.actual, "A")
        self.assertNotIn("Copia", cliente.estado)


class TestEliminar(unittest.TestCase):

    def test_p6_elimina_otro_perfil(self):
        cliente = ClienteFalso(("A", "B"), actual="A")
        perfiles_obs.eliminar_perfil(cliente, "B")
        self.assertNotIn("B", cliente.estado)
        self.assertEqual(cliente.actual, "A")
        self.assertIn("RemoveProfile", cliente.tipos())

    def test_p6_espera_a_que_obs_saque_el_perfil_de_la_lista(self):
        cliente = ClienteQueTardaEnQuitar(("A", "B"), actual="A")
        perfiles_obs.eliminar_perfil(cliente, "B")
        self.assertNotIn("B", cliente.estado)
        self.assertGreaterEqual(len(cliente.listados_despues), 2)
        self.assertIn("B", cliente.listados_despues[0])
        self.assertNotIn("B", cliente.listados_despues[-1])

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

    def test_p1_igual_el_audio_del_destino_antes_de_cambiar(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "profiles"
            base.mkdir()
            carpeta = crear_perfil(base, "B", {
                "Audio": {"SampleRate": "44100", "ChannelSetup": "Mono"}})
            cliente = ClienteQueMiraElArchivo(
                ("A", "B"), actual="A", ruta=carpeta / "basic.ini")
            with mock.patch.object(paths, "carpeta_obs", return_value=base):
                perfiles_obs.cambiar_perfil(cliente, "B")
        self.assertEqual(cliente.audio_al_cambiar, {
            "SampleRate": "48000", "ChannelSetup": "Stereo"})
        self.assertEqual(cliente.actual, "B")


class TestAvanzado(unittest.TestCase):

    def test_p8_detecta_avanzado_y_pasa_a_sencillo(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "profiles"
            base.mkdir()
            crear_perfil(base, "Avanzado", {
                "Output": {"Mode": "Advanced"},
                "AdvOut": {"Encoder": "obs_nvenc_h264_tex"},
                "SimpleOutput": {"StreamEncoder": "x264",
                                 "VBitrate": "2500"},
            }, bitrate=4500)
            cliente = ClienteFalso(("A", "Avanzado"), actual="A")
            with mock.patch.object(paths, "carpeta_obs",
                                   return_value=base):
                convertido = perfiles_obs.pasar_a_sencillo(
                    cliente, "Avanzado")
                guardado = perfiles_obs.leer_ajustes(cliente, "Avanzado")
        self.assertTrue(convertido)
        self.assertEqual(cliente.actual, "A")
        self.assertEqual(cliente.cambios_de_perfil(), [])
        self.assertEqual(guardado.codificador, "nvenc")
        self.assertEqual(guardado.bitrate_video, 4500)

    def test_p8_perfil_sencillo_no_cambia_nada(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "profiles"
            base.mkdir()
            carpeta = crear_perfil(base, "Sencillo", {
                "Output": {"Mode": "Simple"}})
            antes = (carpeta / "basic.ini").read_bytes()
            cliente = ClienteFalso(("A", "Sencillo"), actual="A")
            with mock.patch.object(paths, "carpeta_obs", return_value=base):
                convertido = perfiles_obs.pasar_a_sencillo(
                    cliente, "Sencillo")
            despues = (carpeta / "basic.ini").read_bytes()
        self.assertFalse(convertido)
        self.assertEqual(cliente.actual, "A")
        self.assertEqual(cliente.cambios_de_perfil(), [])
        self.assertEqual(antes, despues)

    def test_p8_codificador_desconocido_deja_x264(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "profiles"
            base.mkdir()
            crear_perfil(base, "Avanzado", {
                "Output": {"Mode": "Advanced"},
                "AdvOut": {"Encoder": "obs_desconocido"},
                "SimpleOutput": {"StreamEncoder": "x264",
                                 "VBitrate": "2500"},
            }, bitrate=3000)
            cliente = ClienteFalso(("A", "Avanzado"), actual="A")
            with mock.patch.object(paths, "carpeta_obs",
                                   return_value=base):
                perfiles_obs.pasar_a_sencillo(cliente, "Avanzado")
                guardado = perfiles_obs.leer_ajustes(cliente, "Avanzado")
        self.assertEqual(guardado.codificador, "x264")
        self.assertEqual(guardado.bitrate_video, 3000)

    def test_p8_sin_streamencoder_usa_el_bitrate_inicial(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "profiles"
            base.mkdir()
            crear_perfil(base, "Avanzado", {
                "Output": {"Mode": "Advanced"},
                "AdvOut": {"Encoder": "obs_x264"},
                "SimpleOutput": {"StreamEncoder": "x264",
                                 "VBitrate": "2500"},
            })
            cliente = ClienteFalso(("A", "Avanzado"), actual="A")
            with mock.patch.object(paths, "carpeta_obs",
                                   return_value=base):
                perfiles_obs.pasar_a_sencillo(cliente, "Avanzado")
                guardado = perfiles_obs.leer_ajustes(cliente, "Avanzado")
        self.assertEqual(guardado.bitrate_video, 2500)

    def test_p8_en_el_perfil_actual_lo_recarga(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "profiles"
            base.mkdir()
            crear_perfil(base, "Avanzado", {
                "Output": {"Mode": "Advanced"},
                "AdvOut": {"Encoder": "obs_x264"}})
            cliente = ClienteFalso(("A", "Avanzado"), actual="Avanzado")
            cliente.configurar("Avanzado", parametros={
                ("Output", "Mode"): "Advanced",
                ("AdvOut", "Encoder"): "obs_x264"})
            with mock.patch.object(paths, "carpeta_obs",
                                   return_value=base):
                perfiles_obs.pasar_a_sencillo(cliente)
            self.assertEqual(cliente.actual, "Avanzado")
            self.assertEqual(cliente.cambios_de_perfil(), ["A", "Avanzado"])

    def test_p8_vuelve_al_perfil_si_falla_a_mitad(self):
        cliente = ClienteFalso(("A",), actual="A")
        cliente.configurar("A", parametros={
            ("Output", "Mode"): "Advanced"})
        cliente.fallar_en = ("SetCurrentProfile", 1)
        with self.assertRaises(obs_cliente.ObsError):
            perfiles_obs.pasar_a_sencillo(cliente, "A")
        self.assertEqual(cliente.actual, "A")

    def test_p8_dice_si_esta_en_avanzado_y_vuelve(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "profiles"
            base.mkdir()
            crear_perfil(base, "Avanzado", {"Output": {"Mode": "Advanced"}})
            crear_perfil(base, "Sencillo", {"Output": {"Mode": "Simple"}})
            cliente = ClienteFalso(("A", "Avanzado", "Sencillo"), actual="A")
            with mock.patch.object(paths, "carpeta_obs", return_value=base):
                self.assertTrue(
                    perfiles_obs.esta_en_avanzado(cliente, "Avanzado"))
                self.assertFalse(
                    perfiles_obs.esta_en_avanzado(cliente, "Sencillo"))
        self.assertEqual(cliente.actual, "A")
        self.assertEqual(cliente.cambios_de_perfil(), [])


class TestPerfilInactivoEnDisco(unittest.TestCase):

    def test_leer_un_perfil_inactivo_no_cambia_de_perfil(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "profiles"
            base.mkdir()
            crear_perfil(base, "B", {"SimpleOutput": {"VBitrate": "4000"}})
            cliente = ClienteFalso(("A", "B"), actual="A")
            with mock.patch.object(paths, "carpeta_obs", return_value=base):
                ajustes = perfiles_obs.leer_ajustes(cliente, "B")
            self.assertEqual(cliente.cambios_de_perfil(), [])
            self.assertEqual(cliente.actual, "A")
            self.assertEqual(ajustes.bitrate_video, 4000)

    def test_leer_sin_carpeta_dice_que_perfil_y_no_cambia(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "profiles"
            base.mkdir()
            cliente = ClienteFalso(("A", "B"), actual="A")
            with mock.patch.object(paths, "carpeta_obs", return_value=base):
                with self.assertRaisesRegex(obs_cliente.ObsError,
                                            "perfil B"):
                    perfiles_obs.leer_ajustes(cliente, "B")
        self.assertEqual(cliente.actual, "A")
        self.assertEqual(cliente.cambios_de_perfil(), [])


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
