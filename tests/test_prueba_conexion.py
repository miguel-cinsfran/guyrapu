# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de la prueba de conexión contra dobles de OBS y YouTube, sin red."""

import tempfile
import threading
import unittest
from dataclasses import replace
from pathlib import Path

from guyrapu.obs import ajustes_perfil, obs_cliente, prueba_conexion


def _ajustes(**cambios):
    base = ajustes_perfil.AjustesPerfil(
        ancho_lienzo=1920, alto_lienzo=1080,
        ancho_salida=1280, alto_salida=720,
        fps=30, codificador="x264", preset="veryfast",
        bitrate_video=2500, servidor="viejo", clave="vieja")
    return replace(base, **cambios)


class DobleObs:
    """Emula lo que la prueba pide a OBS, con pérdida según el bitrate."""

    def __init__(self, ajustes, carpeta, avanzado=False, activos=(),
                 tasas=None):
        self.ajustes = replace(ajustes, carpeta_grabacion=str(carpeta))
        self.carpeta = Path(carpeta)
        self.modo = "advanced" if avanzado else "simple"
        self.activos = set(activos)
        self.transmitiendo = False
        self.tasas = dict(tasas or {})
        self.servicio = {
            "streamServiceType": "rtmp_custom",
            "streamServiceSettings": {"server": "viejo", "key": "vieja"}}
        self.perfiles = ["Principal", "Otro"]
        self.actual = "Principal"
        self.consultas = 0
        self.llamadas = []
        self.pedidos = []
        self.fallar_en = None
        self.veces = {}

    def _falla(self, tipo):
        veces = self.veces.get(tipo, 0) + 1
        self.veces[tipo] = veces
        return self.fallar_en == (tipo, veces)

    def _parametros(self):
        datos = {(categoria, nombre): valor
                 for categoria, nombre, valor
                 in ajustes_perfil.parametros_obs(self.ajustes)}
        datos[("Output", "Mode")] = self.modo
        return datos

    def _progreso(self):
        perdidos, totales = self.tasas.get(self.ajustes.bitrate_video, (0, 100))
        total = self.consultas * 1000
        perdidos = int(total * perdidos / totales) if totales else 0
        return {"outputSkippedFrames": perdidos, "outputTotalFrames": total}

    def pedir(self, tipo, datos=None, parada=None):
        self.llamadas.append(tipo)
        self.pedidos.append((tipo, dict(datos or {})))
        if self._falla(tipo):
            raise obs_cliente.ObsError("Fallo simulado en " + tipo)
        datos = datos or {}
        if tipo == "GetStreamStatus":
            if self.transmitiendo:
                self.consultas += 1
                progreso = self._progreso()
            else:
                progreso = {"outputSkippedFrames": 0, "outputTotalFrames": 0}
            return {"responseData": dict(progreso,
                                         outputActive=self.transmitiendo)}
        if tipo == "StartStream":
            self.transmitiendo = True
            return {"responseData": {}}
        if tipo == "StopStream":
            self.transmitiendo = False
            return {"responseData": {}}
        if tipo == "GetRecordStatus":
            return {"responseData": {"outputActive": "GetRecordStatus"
                                     in self.activos}}
        if tipo == "GetReplayBufferStatus":
            return {"responseData": {"outputActive":
                                     "GetReplayBufferStatus" in self.activos}}
        if tipo == "GetProfileList":
            return {"responseData": {"profiles": list(self.perfiles),
                                     "currentProfileName": self.actual}}
        if tipo == "SetCurrentProfile":
            self.actual = datos["profileName"]
            return {"responseData": {}}
        if tipo in ("CreateProfile", "RemoveProfile"):
            return {"responseData": {}}
        if tipo == "GetVideoSettings":
            return {"responseData": ajustes_perfil.datos_video(self.ajustes)}
        if tipo == "SetVideoSettings":
            self.ajustes = replace(
                self.ajustes,
                ancho_lienzo=datos["baseWidth"],
                alto_lienzo=datos["baseHeight"],
                ancho_salida=datos["outputWidth"],
                alto_salida=datos["outputHeight"],
                fps=datos["fpsNumerator"] // datos["fpsDenominator"])
            return {"responseData": {}}
        if tipo == "GetStreamServiceSettings":
            return {"responseData": {
                "streamServiceType": self.servicio["streamServiceType"],
                "streamServiceSettings": dict(
                    self.servicio["streamServiceSettings"])}}
        if tipo == "SetStreamServiceSettings":
            self.servicio = {
                "streamServiceType": datos["streamServiceType"],
                "streamServiceSettings": dict(
                    datos["streamServiceSettings"])}
            return {"responseData": {}}
        if tipo == "GetRecordDirectory":
            return {"responseData": {"recordDirectory": str(self.carpeta)}}
        if tipo == "GetProfileParameter":
            clave = (datos["parameterCategory"], datos["parameterName"])
            return {"responseData": {"parameterValue": self._parametros(
                ).get(clave, "")}}
        if tipo == "SetProfileParameter":
            self._fijar(datos)
            return {"responseData": {}}
        return {"responseData": {}}

    def _fijar(self, datos):
        categoria = datos["parameterCategory"]
        nombre = datos["parameterName"]
        valor = datos["parameterValue"]
        if categoria == "SimpleOutput" and nombre == "VBitrate":
            self.ajustes = replace(self.ajustes, bitrate_video=int(valor))
        elif categoria == "Output" and nombre == "Mode":
            self.modo = valor


class ServicioEscrituraFalso:
    """El servicio de escritura mínimo que usa la prueba del flujo."""

    def __init__(self, youtube):
        self._youtube = youtube
        self._pendiente = {}

    def liveStreams(self):
        return self

    def insert(self, **kwargs):
        self._youtube.inserciones_flujo.append(kwargs)
        self._pendiente = {
            "id": self._youtube.id_flujo,
            "cdn": {"ingestionInfo": {
                "ingestionAddress": self._youtube.servidor,
                "streamName": self._youtube.clave}}}
        return self

    def delete(self, **kwargs):
        self._youtube.flujos_borrados.append(kwargs["id"])
        return self

    def execute(self):
        return self._pendiente


class DobleYouTube:
    """Cuenta lo que la prueba crea, vincula y borra en YouTube."""

    def __init__(self, fallar_en=None):
        self.cuerpos = []
        self.vinculados = []
        self.emisiones_borradas = []
        self.flujos_borrados = []
        self.inserciones_flujo = []
        self.transiciones = []
        self.id_flujo = "flujo-1"
        self.servidor = "rtmp://prueba"
        self.clave = "clave-prueba"
        self.fallar_en = fallar_en
        self.veces = {}

    def _falla(self, tipo):
        veces = self.veces.get(tipo, 0) + 1
        self.veces[tipo] = veces
        return self.fallar_en == (tipo, veces)

    def _escritura(self):
        return ServicioEscrituraFalso(self)

    def crear_emision(self, cuerpo):
        if self._falla("crear_emision"):
            raise RuntimeError("fallo de YouTube")
        self.cuerpos.append(cuerpo)
        return "video-1"

    def vincular_emision(self, id_video, id_flujo):
        if self._falla("vincular_emision"):
            raise RuntimeError("fallo de YouTube")
        self.vinculados.append((id_video, id_flujo))

    def borrar_emision(self, id_video):
        self.emisiones_borradas.append(id_video)

    def finalizar_emision(self, id_video):
        self.transiciones.append(id_video)


class BasePrueba(unittest.TestCase):

    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)
        self.carpeta = Path(self.temporal.name)

    def _doblar(self, **kwargs):
        return DobleObs(kwargs.pop("ajustes", _ajustes()), self.carpeta,
                        **kwargs)

    def _ejecutar(self, doble, youtube=None, **kwargs):
        return prueba_conexion.ejecutar(
            doble, youtube or DobleYouTube(), calentamiento=0, medicion=0,
            dormir=lambda _segundos: None, **kwargs)

    def _comprobar_restaurado(self, doble):
        self.assertEqual(doble.ajustes,
                         replace(_ajustes(),
                                 carpeta_grabacion=str(self.carpeta)))
        self.assertEqual(doble.servicio, {
            "streamServiceType": "rtmp_custom",
            "streamServiceSettings": {"server": "viejo", "key": "vieja"}})
        self.assertFalse(doble.transmitiendo)


class TestRecorrido(BasePrueba):

    def test_el_perfil_aguanta_y_sube_hasta_el_primero_que_no(self):
        doble = self._doblar(tasas={2500: (0, 100), 3800: (0, 100),
                                    5000: (2, 100)})
        youtube = DobleYouTube()
        resultado = self._ejecutar(doble, youtube)

        self.assertEqual([paso.bitrate for paso in resultado.pasos],
                         [2500, 3800, 5000])
        self.assertEqual(resultado.aguantaron, 2500)
        self.assertEqual(resultado.mayor, 3800)
        self.assertTrue(resultado.aguanta_tal_cual)
        self.assertFalse(resultado.puede_guardar)
        self.assertEqual(youtube.emisiones_borradas, ["video-1"])
        self.assertEqual(youtube.flujos_borrados, ["flujo-1"])
        self.assertEqual(youtube.transiciones, [])
        self._comprobar_restaurado(doble)

    def test_si_el_perfil_no_aguanta_baja_hasta_el_que_aguanta(self):
        doble = self._doblar(tasas={2500: (5, 100), 1800: (4, 100),
                                    1300: (1, 100)})
        youtube = DobleYouTube()
        resultado = self._ejecutar(doble, youtube)

        self.assertEqual([paso.bitrate for paso in resultado.pasos],
                         [2500, 1800, 1300])
        self.assertEqual(resultado.aguantaron, 1300)
        self.assertFalse(resultado.aguanta_tal_cual)
        self.assertTrue(resultado.puede_guardar)
        self.assertEqual(youtube.emisiones_borradas, ["video-1"])
        self.assertEqual(youtube.flujos_borrados, ["flujo-1"])
        self._comprobar_restaurado(doble)

    def test_el_directo_se_crea_privado_y_no_sale_al_aire(self):
        doble = self._doblar(tasas={2500: (0, 100)})
        youtube = DobleYouTube()
        self._ejecutar(doble, youtube)

        cuerpo = youtube.cuerpos[0]
        self.assertEqual(cuerpo["status"]["privacyStatus"], "private")
        self.assertFalse(cuerpo["contentDetails"]["enableAutoStart"])
        self.assertFalse(cuerpo["contentDetails"]["enableAutoStop"])
        self.assertEqual(youtube.vinculados, [("video-1", "flujo-1")])
        self.assertEqual(youtube.transiciones, [])

    def test_sin_aguantar_ninguno_lo_dice_con_el_ultimo_porcentaje(self):
        doble = self._doblar(tasas={2500: (5, 100), 1800: (4, 100),
                                    1300: (3, 100)})
        resultado = self._ejecutar(doble)

        self.assertIsNone(resultado.aguantaron)
        self.assertEqual(resultado.ultimo.bitrate, 1300)
        self.assertEqual(resultado.ultimo.porcentaje, 3)
        self.assertFalse(resultado.puede_guardar)


class TestErroresYParada(BasePrueba):

    def test_con_error_a_mitad_restaura_y_borra(self):
        doble = self._doblar(tasas={2500: (0, 100), 3800: (0, 100)})
        doble.fallar_en = ("StartStream", 2)
        youtube = DobleYouTube()

        with self.assertRaises(obs_cliente.ObsError):
            self._ejecutar(doble, youtube)
        self._comprobar_restaurado(doble)
        self.assertEqual(youtube.emisiones_borradas, ["video-1"])
        self.assertEqual(youtube.flujos_borrados, ["flujo-1"])
        self.assertEqual(youtube.transiciones, [])

    def test_la_parada_corta_la_prueba_y_restaura(self):
        doble = self._doblar(tasas={2500: (0, 100), 3800: (0, 100)})
        youtube = DobleYouTube()
        parada = threading.Event()

        def al_bitrate(bitrate):
            if bitrate == 3800:
                parada.set()

        resultado = self._ejecutar(doble, youtube, parada=parada,
                                   al_bitrate=al_bitrate)
        self.assertTrue(resultado.cancelada)
        self.assertEqual([paso.bitrate for paso in resultado.pasos], [2500])
        self._comprobar_restaurado(doble)
        self.assertEqual(youtube.emisiones_borradas, ["video-1"])
        self.assertEqual(youtube.flujos_borrados, ["flujo-1"])

    def test_si_no_puede_borrar_el_directo_lo_deja_dicho_con_su_titulo(self):
        doble = self._doblar(tasas={2500: (0, 100)})
        youtube = DobleYouTube()

        def sin_borrar(_id_video):
            raise RuntimeError("permiso denegado")

        youtube.borrar_emision = sin_borrar
        resultado = self._ejecutar(doble, youtube)

        self.assertEqual(len(resultado.errores), 1)
        self.assertIn("Prueba de conexión de Guyrapu", resultado.errores[0])
        self.assertIn("permiso denegado", resultado.errores[0])
        self._comprobar_restaurado(doble)
        self.assertEqual(youtube.flujos_borrados, ["flujo-1"])


class TestNoSePuedeProbar(BasePrueba):

    def test_sin_sesion_no_empieza(self):
        doble = self._doblar()
        with self.assertRaises(prueba_conexion.ErrorPruebaConexion):
            prueba_conexion.preparar(doble, hay_sesion=False)
        self.assertNotIn("StartStream", doble.llamadas)
        self.assertNotIn("SetStreamServiceSettings", doble.llamadas)

    def test_en_modo_avanzado_no_empieza(self):
        doble = self._doblar(avanzado=True)
        with self.assertRaises(prueba_conexion.ErrorPruebaConexion):
            prueba_conexion.preparar(doble)
        self.assertNotIn("StartStream", doble.llamadas)

    def test_con_cualquier_salida_en_marcha_no_empieza(self):
        for activa in ("GetStreamStatus", "GetRecordStatus",
                       "GetReplayBufferStatus"):
            with self.subTest(salida=activa):
                doble = self._doblar(activos=(activa,))
                if activa == "GetStreamStatus":
                    doble.transmitiendo = True
                with self.assertRaises(obs_cliente.ObsError):
                    prueba_conexion.preparar(doble)
                self.assertNotIn("StartStream", doble.llamadas)


class TestPreparacion(BasePrueba):

    def test_devuelve_perfil_bitrate_y_duracion_maxima(self):
        doble = self._doblar()
        preparacion = prueba_conexion.preparar(
            doble, calentamiento=5, medicion=15)
        self.assertEqual(preparacion.perfil, "Principal")
        self.assertEqual(preparacion.bitrate, 2500)
        self.assertEqual(preparacion.segundos_maximos, 60)


if __name__ == "__main__":
    unittest.main()
