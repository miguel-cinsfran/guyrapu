# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de la lectura y escritura de un perfil de OBS en disco."""

import contextlib
import dataclasses
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from guyrapu.core import paths
from guyrapu.obs import ajustes_perfil, obs_cliente, perfil_en_disco


@contextlib.contextmanager
def carpeta_de_perfiles():
    """Una carpeta de perfiles temporal, ya apuntada por paths."""
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp) / "profiles"
        base.mkdir()
        with mock.patch.object(paths, "carpeta_obs", return_value=base):
            yield base


def crear_perfil(base, nombre, secciones=None, servicio=None, bitrate=None):
    """Escribe un basic.ini con la forma real: BOM, LF y barras dobles."""
    carpeta = Path(base) / ("perfil-" + nombre.lower().replace(" ", "-"))
    carpeta.mkdir(parents=True)
    lineas = ["[General]", f"Name={nombre}", ""]
    for seccion, claves in (secciones or {}).items():
        lineas.append(f"[{seccion}]")
        for clave, valor in claves.items():
            lineas.append(
                f"{clave}={str(valor).replace(chr(92), chr(92) * 2)}")
        lineas.append("")
    texto = "\n".join(lineas)
    (carpeta / "basic.ini").write_bytes(
        b"\xef\xbb\xbf" + texto.encode("utf-8"))
    if servicio is not None:
        (carpeta / "service.json").write_text(
            json.dumps(servicio, separators=(",", ":")), encoding="utf-8")
    if bitrate is not None:
        (carpeta / "streamEncoder.json").write_text(
            json.dumps({"bitrate": bitrate}), encoding="utf-8")
    return carpeta


def secciones_reales():
    """Un perfil como los de casa, con los valores iniciales de la app."""
    return {
        "Output": {"Mode": "Simple", "Reconnect": "true",
                   "RetryDelay": "2", "MaxRetries": "25"},
        "SimpleOutput": {
            "FilePath": r"C:\Users\ic_ma\Videos",
            "StreamEncoder": "x264", "VBitrate": "2500", "ABitrate": "160",
            "Preset": "veryfast", "DynamicBitrate": "false",
            "RecFormat2": "mkv", "RecQuality": "Stream", "RecRB": "false",
            "RecRBTime": "30",
        },
        "Video": {"BaseCX": "1920", "BaseCY": "1080",
                  "OutputCX": "1280", "OutputCY": "720",
                  "FPSType": "2", "FPSNum": "30", "FPSDen": "1",
                  "ColorFormat": "NV12"},
        "Audio": {"SampleRate": "48000", "ChannelSetup": "Stereo",
                  "MonitoringDeviceId": "default",
                  "MonitoringDeviceName": "Por defecto"},
        "Panels": {"CookieId": "D700C1A9BE6F24F8"},
        "Hotkeys": {"OBSBasic.SaveReplayBuffer": '{"bindings":[]}'},
    }


def ajustes_de_prueba(**cambios):
    return dataclasses.replace(
        ajustes_perfil.valores_iniciales(False, "x264"), **cambios)


@contextlib.contextmanager
def lectura_que_falla(ruta):
    """Hace fallar la lectura de ese archivo, como unos bytes inválidos."""
    original = Path.read_text

    def leer_texto(camino, *args, **kwargs):
        if camino == ruta:
            raise UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalido")
        return original(camino, *args, **kwargs)

    with mock.patch.object(Path, "read_text", leer_texto):
        yield


class TestLectura(unittest.TestCase):

    def _leer(self, nombre, secciones, servicio=None, bitrate=None):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "profiles"
            base.mkdir()
            crear_perfil(base, nombre, secciones, servicio, bitrate)
            with mock.patch.object(paths, "carpeta_obs", return_value=base):
                return perfil_en_disco.leer_ajustes(nombre)

    def test_lee_cada_tipo_de_fps(self):
        casos = (
            ({"FPSType": "0", "FPSCommon": "29.97"}, 30),
            ({"FPSType": "1", "FPSInt": "48"}, 48),
            ({"FPSType": "2", "FPSNum": "60000", "FPSDen": "1001"}, 60),
            ({}, 30),
            ({"FPSCommon": ""}, 30),
        )
        for video, esperado in casos:
            with self.subTest(video=video):
                self.assertEqual(self._leer("Perfil", {"Video": video}).fps,
                                 esperado)

    def test_lee_video_y_parametros_del_formato_real(self):
        ajustes = self._leer("Perfil", {
            "Video": {"BaseCX": "1080", "BaseCY": "1920",
                      "OutputCX": "720", "OutputCY": "1280",
                      "FPSType": "2", "FPSNum": "60", "FPSDen": "1"},
            "SimpleOutput": {"StreamEncoder": "qsv", "VBitrate": "4000",
                             "ABitrate": "192", "QSVPreset": "quality"},
            "Audio": {"SampleRate": "44100", "ChannelSetup": "Mono"},
        })
        self.assertEqual((ajustes.ancho_lienzo, ajustes.alto_lienzo),
                         (1080, 1920))
        self.assertEqual((ajustes.ancho_salida, ajustes.alto_salida),
                         (720, 1280))
        self.assertEqual(ajustes.fps, 60)
        self.assertEqual(ajustes.codificador, "qsv")
        self.assertEqual(ajustes.preset, "quality")
        self.assertEqual(ajustes.bitrate_video, 4000)
        self.assertEqual(ajustes.bitrate_audio, 192)
        self.assertEqual(ajustes.muestreo, 44100)
        self.assertEqual(ajustes.canales, "Mono")

    def test_servicio_con_y_sin_archivo(self):
        with carpeta_de_perfiles() as base:
            crear_perfil(base, "Con", {}, servicio={
                "type": "rtmp_custom",
                "settings": {"server": "rtmp://x", "key": "k"}})
            crear_perfil(base, "Sin", {})
            crear_perfil(base, "Conocido", {}, servicio={
                "type": "YouTube",
                "settings": {"server": "rtmp://yt", "key": "k"}})
            con = perfil_en_disco.leer_ajustes("Con")
            sin = perfil_en_disco.leer_ajustes("Sin")
            _a, _av, personalizado = perfil_en_disco.leer_para_editar("Con")
            _b, _av2, personalizado2 = perfil_en_disco.leer_para_editar("Sin")
            _c, _av3, personalizado3 = perfil_en_disco.leer_para_editar(
                "Conocido")
        self.assertEqual((con.servidor, con.clave), ("rtmp://x", "k"))
        self.assertTrue(personalizado)
        self.assertEqual((sin.servidor, sin.clave), ("", ""))
        self.assertFalse(personalizado2)
        self.assertFalse(personalizado3)

    def test_lee_el_dispositivo_de_monitoreo(self):
        with carpeta_de_perfiles() as base:
            crear_perfil(base, "Perfil", {"Audio": {
                "MonitoringDeviceId": "{0.0.0.3}",
                "MonitoringDeviceName": "Auriculares",
            }})
            ajustes = perfil_en_disco.leer_ajustes("Perfil")
        self.assertEqual(ajustes.monitoreo_id, "{0.0.0.3}")
        self.assertEqual(ajustes.monitoreo_nombre, "Auriculares")

    def test_carpeta_de_grabacion_en_los_dos_modos(self):
        simple = self._leer("Simple", {
            "Output": {"Mode": "Simple"},
            "SimpleOutput": {"FilePath": r"C:\Simple"}})
        avanzado = self._leer("Avanzado", {
            "Output": {"Mode": "Advanced"},
            "AdvOut": {"RecFilePath": r"C:\Avanzado"}})
        self.assertEqual(simple.carpeta_grabacion, r"C:\Simple")
        self.assertEqual(avanzado.carpeta_grabacion, r"C:\Avanzado")

    def test_lee_el_modo(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "profiles"
            base.mkdir()
            crear_perfil(base, "Avanzado", {"Output": {"Mode": "Advanced"}})
            crear_perfil(base, "Sencillo", {"Output": {"Mode": "Simple"}})
            crear_perfil(base, "Sin", {})
            with mock.patch.object(paths, "carpeta_obs", return_value=base):
                self.assertTrue(
                    perfil_en_disco.esta_en_avanzado("Avanzado"))
                self.assertFalse(
                    perfil_en_disco.esta_en_avanzado("Sencillo"))
                self.assertFalse(perfil_en_disco.esta_en_avanzado("Sin"))


class TestEscritura(unittest.TestCase):

    def test_escribe_y_vuelve_a_leer_lo_mismo(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "profiles"
            base.mkdir()
            crear_perfil(base, "Perfil", secciones_reales())
            ajustes = ajustes_de_prueba(
                ancho_lienzo=1600, alto_lienzo=900,
                ancho_salida=1280, alto_salida=720, fps=50,
                codificador="qsv", preset="quality", bitrate_video=3500,
                bitrate_audio=192, carpeta_grabacion=r"C:\Grabaciones",
                servidor="rtmp://nuevo", clave="clave-nueva")
            with mock.patch.object(paths, "carpeta_obs", return_value=base):
                perfil_en_disco.guardar_ajustes("Perfil", ajustes)
                leidos = perfil_en_disco.leer_ajustes("Perfil")
        self.assertEqual((leidos.ancho_lienzo, leidos.alto_lienzo),
                         (1600, 900))
        self.assertEqual((leidos.ancho_salida, leidos.alto_salida),
                         (1280, 720))
        self.assertEqual(leidos.fps, 50)
        self.assertEqual(leidos.codificador, "qsv")
        self.assertEqual(leidos.preset, "quality")
        self.assertEqual(leidos.bitrate_video, 3500)
        self.assertEqual(leidos.bitrate_audio, 192)
        self.assertEqual(leidos.carpeta_grabacion, r"C:\Grabaciones")
        self.assertEqual((leidos.servidor, leidos.clave),
                         ("rtmp://nuevo", "clave-nueva"))

    def test_guarda_fps_sobre_un_perfil_con_fps_por_defecto(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "profiles"
            base.mkdir()
            crear_perfil(base, "Perfil", {
                "Video": {"BaseCX": "1920", "BaseCY": "1080",
                          "OutputCX": "1280", "OutputCY": "720",
                          "FPSType": "0", "FPSCommon": "30"},
            })
            with mock.patch.object(paths, "carpeta_obs", return_value=base):
                perfil_en_disco.guardar_ajustes(
                    "Perfil", ajustes_de_prueba(fps=20))
                leidos = perfil_en_disco.leer_ajustes("Perfil")
        self.assertEqual(leidos.fps, 20)

    def test_una_linea_que_no_se_toca_queda_igual_byte_a_byte(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "profiles"
            base.mkdir()
            carpeta = crear_perfil(base, "Perfil", secciones_reales())
            antes = (carpeta / "basic.ini").read_bytes()
            with mock.patch.object(paths, "carpeta_obs", return_value=base):
                perfil_en_disco.guardar_ajustes(
                    "Perfil", ajustes_de_prueba(bitrate_video=3500))
            despues = (carpeta / "basic.ini").read_bytes()
        self.assertTrue(despues.startswith(b"\xef\xbb\xbf"))
        self.assertNotIn(b"\r\n", despues)
        lineas_antes = antes.decode("utf-8-sig").splitlines()
        lineas_despues = despues.decode("utf-8-sig").splitlines()
        self.assertEqual([linea for linea in lineas_despues
                          if linea not in lineas_antes],
                         ["VBitrate=3500"])
        self.assertEqual([linea for linea in lineas_antes
                          if linea not in lineas_despues],
                         ["VBitrate=2500"])
        for intacta in ("ColorFormat=NV12", "[Panels]",
                        'OBSBasic.SaveReplayBuffer={"bindings":[]}'):
            self.assertIn(intacta, lineas_despues)

    def test_agrega_una_clave_y_una_seccion_que_faltan(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "profiles"
            base.mkdir()
            carpeta = crear_perfil(base, "Perfil", {
                "Video": {"BaseCX": "1920", "BaseCY": "1080",
                          "OutputCX": "1280", "OutputCY": "720",
                          "FPSType": "2", "FPSNum": "30"},
                "SimpleOutput": {"StreamEncoder": "x264",
                                 "VBitrate": "2500"},
            })
            with mock.patch.object(paths, "carpeta_obs", return_value=base):
                perfil_en_disco.guardar_ajustes(
                    "Perfil", ajustes_de_prueba())
                leidos = perfil_en_disco.leer_ajustes("Perfil")
            texto = (carpeta / "basic.ini").read_text(encoding="utf-8-sig")
        self.assertEqual(leidos.fps, 30)
        self.assertEqual(leidos.muestreo, 48000)
        self.assertEqual(leidos.canales, "Stereo")
        self.assertIn("FPSDen=1", texto)
        self.assertIn("[Output]", texto)
        self.assertIn("Reconnect=true", texto)
        self.assertIn("[Audio]", texto)
        self.assertIn("SampleRate=48000", texto)

    def test_conserva_el_tipo_de_servicio_conocido(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "profiles"
            base.mkdir()
            carpeta = crear_perfil(base, "Perfil", {}, servicio={
                "type": "YouTube",
                "settings": {"server": "rtmp://yt", "key": "vieja",
                             "extra": "se conserva"}})
            with mock.patch.object(paths, "carpeta_obs", return_value=base):
                perfil_en_disco.guardar_ajustes(
                    "Perfil", ajustes_de_prueba(
                        servidor="rtmp://otro", clave="nueva"))
            datos = json.loads((carpeta / "service.json").read_text(
                encoding="utf-8"))
        self.assertEqual(datos, {
            "type": "YouTube",
            "settings": {"server": "rtmp://yt", "key": "nueva",
                         "extra": "se conserva"},
        })

    def test_sin_servidor_ni_clave_no_crea_el_servicio(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "profiles"
            base.mkdir()
            carpeta = crear_perfil(base, "Perfil", secciones_reales())
            with mock.patch.object(paths, "carpeta_obs", return_value=base):
                perfil_en_disco.guardar_ajustes(
                    "Perfil", ajustes_de_prueba(servidor="", clave=""))
            self.assertFalse((carpeta / "service.json").exists())

    def test_pasar_a_sencillo_escribe_mode_y_codificador(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "profiles"
            base.mkdir()
            crear_perfil(base, "Avanzado", {
                "Output": {"Mode": "Advanced"},
                "AdvOut": {"Encoder": "obs_nvenc_h264_tex"},
                "SimpleOutput": {"StreamEncoder": "x264",
                                 "VBitrate": "2500"},
            }, bitrate=4500)
            with mock.patch.object(paths, "carpeta_obs", return_value=base):
                self.assertEqual(
                    perfil_en_disco.encoder_avanzado("Avanzado"),
                    "obs_nvenc_h264_tex")
                perfil_en_disco.pasar_a_sencillo("Avanzado", "nvenc", 4500)
                self.assertFalse(
                    perfil_en_disco.esta_en_avanzado("Avanzado"))
                leidos = perfil_en_disco.leer_ajustes("Avanzado")
        self.assertEqual(leidos.codificador, "nvenc")
        self.assertEqual(leidos.bitrate_video, 4500)

    def test_carpeta_que_no_aparece_da_el_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "profiles"
            base.mkdir()
            with mock.patch.object(paths, "carpeta_obs", return_value=base):
                with self.assertRaisesRegex(obs_cliente.ObsError,
                                            "perfil Fantasma"):
                    perfil_en_disco.leer_ajustes("Fantasma")
                with self.assertRaisesRegex(obs_cliente.ObsError,
                                            "perfil Fantasma"):
                    perfil_en_disco.guardar_ajustes(
                        "Fantasma", ajustes_de_prueba())


class TestEscrituraSinLectura(unittest.TestCase):

    def _comprobar(self, accion):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "profiles"
            base.mkdir()
            carpeta = crear_perfil(base, "Perfil", secciones_reales())
            basic = carpeta / "basic.ini"
            antes = basic.read_bytes()
            with mock.patch.object(paths, "carpeta_obs", return_value=base):
                with lectura_que_falla(basic):
                    with self.assertRaises(obs_cliente.ObsError):
                        accion("Perfil")
            self.assertEqual(basic.read_bytes(), antes)

    def test_guardar_falla_y_no_escribe(self):
        self._comprobar(lambda nombre: perfil_en_disco.guardar_ajustes(
            nombre, ajustes_de_prueba(fps=60)))

    def test_pasar_a_sencillo_falla_y_no_escribe(self):
        self._comprobar(lambda nombre: perfil_en_disco.pasar_a_sencillo(
            nombre, "nvenc", 4000))


if __name__ == "__main__":
    unittest.main()
