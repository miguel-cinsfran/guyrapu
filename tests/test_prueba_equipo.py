# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de la prueba del equipo contra un doble de OBS, sin ventanas."""

import tempfile
import threading
import unittest
from dataclasses import replace
from pathlib import Path
from unittest import mock

from guyrapu.obs import ajustes_perfil, obs_cliente, prueba_equipo


def _ajustes(**cambios):
    base = ajustes_perfil.AjustesPerfil(
        ancho_lienzo=1920, alto_lienzo=1080,
        ancho_salida=1920, alto_salida=1080,
        fps=60, codificador="x264", preset="veryfast",
        calidad_grabacion="HQ")
    return replace(base, **cambios)


class DobleObs:
    """Cuenta fotogramas según los ajustes que OBS tiene en cada momento."""

    def __init__(self, ajustes, carpeta, avanzado=False, grabando=False,
                 tasas=None):
        self.ajustes = ajustes
        self.avanzado = avanzado
        self.grabando = grabando
        self.activos = set()
        self.tasas = dict(tasas or {})
        self.perfiles = ["Principal"]
        self.actual = "Principal"
        self.modo = "advanced" if avanzado else "simple"
        self.escena_al_aire = "Escena"
        self.escenas = {"Escena": [{
            "sceneItemId": 1, "sourceName": "Cámara",
            "sceneItemIndex": 0, "sceneItemEnabled": True}]}
        self.carpeta = Path(carpeta)
        self.liberado = True
        self.consultas = 0
        self.llamadas = []
        self.pedidos = []
        self.veces = {}
        self.fallar_en = None
        self._siguiente_id = 2

    def _id(self):
        self._siguiente_id += 1
        return self._siguiente_id

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

    def pedir(self, tipo, datos=None, parada=None):
        self.llamadas.append(tipo)
        self.pedidos.append((tipo, dict(datos or {})))
        if self._falla(tipo):
            raise obs_cliente.ObsError("Fallo simulado en " + tipo)
        datos = datos or {}
        if tipo == "GetStreamStatus":
            return {"responseData": {"outputActive": tipo in self.activos}}
        if tipo == "GetRecordStatus":
            activo = self.grabando or tipo in self.activos
            if not activo:
                self.liberado = True
            return {"responseData": {"outputActive": activo}}
        if tipo == "GetReplayBufferStatus":
            return {"responseData": {"outputActive": tipo in self.activos}}
        if tipo == "GetProfileList":
            return {"responseData": {"profiles": list(self.perfiles),
                                     "currentProfileName": self.actual}}
        if tipo == "GetCurrentProgramScene":
            return {"responseData": {
                "currentProgramSceneName": self.escena_al_aire}}
        if tipo == "SetCurrentProgramScene":
            self.escena_al_aire = datos["sceneName"]
            return {"responseData": {}}
        if tipo == "GetVideoSettings":
            return {"responseData": ajustes_perfil.datos_video(
                self.ajustes)}
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
                "streamServiceType": "rtmp_custom",
                "streamServiceSettings": {}}}
        if tipo == "GetRecordDirectory":
            return {"responseData": {"recordDirectory": str(self.carpeta)}}
        if tipo == "GetProfileParameter":
            clave = (datos["parameterCategory"], datos["parameterName"])
            return {"responseData": {"parameterValue": self._parametros(
                ).get(clave, "")}}
        if tipo == "SetProfileParameter":
            self._fijar(datos)
            return {"responseData": {}}
        if tipo == "SetCurrentProfile":
            self.actual = datos["profileName"]
            return {"responseData": {}}
        if tipo == "CreateProfile":
            self.perfiles.append(datos["profileName"])
            return {"responseData": {}}
        if tipo == "RemoveProfile":
            self.perfiles.remove(datos["profileName"])
            return {"responseData": {}}
        if tipo == "CreateScene":
            self.escenas[datos["sceneName"]] = []
            return {"responseData": {}}
        if tipo == "GetSceneItemList":
            return {"responseData": {"sceneItems": list(
                self.escenas.get(datos["sceneName"], ()))}}
        if tipo == "DuplicateSceneItem":
            return {"responseData": self._duplicar(datos)}
        if tipo == "CreateInput":
            item = {"sceneItemId": self._id(),
                    "sourceName": datos["inputName"],
                    "sceneItemIndex": len(self.escenas[datos["sceneName"]]),
                    "sceneItemEnabled": True}
            self.escenas[datos["sceneName"]].append(item)
            return {"responseData": {"sceneItemId": item["sceneItemId"]}}
        if tipo in ("SetSceneItemIndex", "SetSceneItemTransform",
                    "SetSceneItemEnabled", "SetInputSettings"):
            return {"responseData": {}}
        if tipo == "RemoveScene":
            self.escenas.pop(datos["sceneName"], None)
            return {"responseData": {}}
        if tipo == "RemoveInput":
            for items in self.escenas.values():
                items[:] = [item for item in items
                            if item["sourceName"] != datos["inputName"]]
            return {"responseData": {}}
        if tipo == "StartRecord":
            self.grabando = True
            return {"responseData": {}}
        if tipo == "StopRecord":
            self.grabando = False
            self.liberado = False
            ruta = self.carpeta / ("prueba-%d.mkv" % self.veces[tipo])
            ruta.write_bytes(b"video")
            return {"responseData": {"outputPath": str(ruta)}}
        if tipo == "GetStats":
            return {"responseData": self._estadisticas()}
        return {"responseData": {}}

    def _fijar(self, datos):
        categoria = datos["parameterCategory"]
        nombre = datos["parameterName"]
        valor = datos["parameterValue"]
        if categoria == "Output" and nombre == "Mode":
            self.modo = valor
        elif categoria == "SimpleOutput" and nombre == "StreamEncoder":
            self.ajustes = replace(self.ajustes, codificador=valor,
                                   preset=ajustes_perfil.preset_intermedio(
                                       valor))
        elif categoria == "SimpleOutput" and nombre == "RecQuality":
            self.ajustes = replace(self.ajustes, calidad_grabacion=valor)
        else:
            for codificador in ajustes_perfil.CODIFICADORES:
                if nombre == ajustes_perfil.clave_preset(codificador):
                    self.ajustes = replace(self.ajustes, preset=valor)

    def _duplicar(self, datos):
        origen = self.escenas.get(datos["sceneName"], [])
        item = next(item for item in origen
                    if item["sceneItemId"] == datos["sceneItemId"])
        copia = dict(item, sceneItemId=self._id())
        self.escenas[datos["destinationSceneName"]].append(copia)
        return {"sceneItemId": copia["sceneItemId"]}

    def _estadisticas(self):
        self.consultas += 1
        clave = (self.ajustes.codificador, self.ajustes.fps,
                 self.ajustes.alto_salida)
        dibujar, codificar = self.tasas.get(clave, (0.0, 0.0))
        total = self.consultas * self.ajustes.fps * 10
        return {"renderTotalFrames": total,
                "renderSkippedFrames": int(total * dibujar),
                "outputTotalFrames": total,
                "outputSkippedFrames": int(total * codificar)}


class BasePrueba(unittest.TestCase):

    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)
        self.carpeta = Path(self.temporal.name)

    def _doblar(self, **kwargs):
        return DobleObs(kwargs.pop("ajustes", _ajustes()), self.carpeta,
                        **kwargs)

    def _ejecutar(self, doble, **kwargs):
        return prueba_equipo.ejecutar(
            doble, calentamiento=0, medicion=0,
            dormir=lambda _segundos: None, **kwargs)

    def _comprobar_restaurado(self, doble, original):
        self.assertEqual(doble.ajustes, original)
        self.assertEqual(doble.escena_al_aire, "Escena")
        self.assertNotIn(prueba_equipo.NOMBRE_ESCENA, doble.escenas)
        for items in doble.escenas.values():
            self.assertFalse(any(item["sourceName"] == prueba_equipo.NOMBRE_FUENTE
                                 for item in items))
        self.assertEqual(list(self.carpeta.glob("*.mkv")), [])


class TestRecorrido(BasePrueba):

    def test_llega_al_escalon_que_aguanta_y_restaura_todo(self):
        original = _ajustes()
        doble = self._doblar(tasas={
            ("x264", 60, 1080): (0.10, 0.29),
            ("qsv", 60, 1080): (0.0, 0.0)})
        resultado = self._ejecutar(doble, disponibles=("qsv", "x264"))

        self.assertEqual(len(resultado.pasos), 2)
        self.assertEqual(resultado.pasos[0].porcentaje_codificar, 29)
        self.assertEqual(resultado.aguantaron.codificador, "qsv")
        self.assertEqual(resultado.aguantaron.calidad_grabacion, "HQ")
        entrada = next(datos for tipo, datos in doble.pedidos
                       if tipo == "CreateInput")
        self.assertTrue(entrada["inputSettings"]["url"].startswith(
            "data:text/html;base64,"))
        self.assertLess(doble.llamadas.index("SetCurrentProgramScene"),
                        doble.llamadas.index("StartRecord"))
        self._comprobar_restaurado(doble, original)

    def test_la_fuente_acompana_los_fotogramas_del_escalon(self):
        doble = self._doblar(tasas={
            ("x264", 60, 1080): (0.0, 1.0),
            ("x264", 30, 1080): (0.0, 0.0)})
        resultado = self._ejecutar(doble, disponibles=("x264",))

        self.assertEqual(resultado.aguantaron.fps, 30)
        entrada = next(datos for tipo, datos in doble.pedidos
                       if tipo == "CreateInput")
        self.assertEqual(entrada["inputSettings"]["fps"], 60)
        self.assertTrue(entrada["inputSettings"]["fps_custom"])
        ajustes = [datos for tipo, datos in doble.pedidos
                   if tipo == "SetInputSettings"]
        self.assertEqual(ajustes[-1]["inputSettings"]["fps"], 30)
        self.assertTrue(ajustes[-1]["inputSettings"]["fps_custom"])

    def test_termina_sin_aguantar_cuando_se_acaban_los_escalones(self):
        original = _ajustes(fps=30, ancho_salida=1280, alto_salida=720)
        doble = self._doblar(ajustes=original, tasas={
            ("x264", 30, 720): (0.10, 0.20)})
        resultado = self._ejecutar(doble, disponibles=("x264",))

        self.assertIsNone(resultado.aguantaron)
        self.assertEqual(len(resultado.pasos), 1)
        self._comprobar_restaurado(doble, original)


class TestErroresYParada(BasePrueba):

    def test_con_error_a_mitad_restaura_y_borra_lo_grabado(self):
        original = _ajustes()
        doble = self._doblar(tasas={
            ("x264", 60, 1080): (0.10, 0.29),
            ("qsv", 60, 1080): (0.0, 0.0)})
        doble.fallar_en = ("StartRecord", 2)
        with self.assertRaises(obs_cliente.ObsError):
            self._ejecutar(doble, disponibles=("qsv", "x264"))
        self._comprobar_restaurado(doble, original)

    def test_la_parada_corta_la_prueba_y_restaura(self):
        original = _ajustes()
        doble = self._doblar(tasas={
            ("x264", 60, 1080): (0.10, 0.29)})
        parada = threading.Event()

        def al_escalon(ajustes):
            if ajustes.codificador == "qsv":
                parada.set()

        resultado = self._ejecutar(
            doble, disponibles=("qsv", "x264"), parada=parada,
            al_escalon=al_escalon)
        self.assertTrue(resultado.cancelada)
        self.assertEqual(len(resultado.pasos), 1)
        self._comprobar_restaurado(doble, original)


class TestArchivoGrabado(BasePrueba):

    def test_borra_cuando_obs_suelta_el_archivo(self):
        original = _ajustes(fps=30, ancho_salida=1280, alto_salida=720)
        doble = self._doblar(ajustes=original, tasas={
            ("x264", 30, 720): (0.0, 0.0)})
        unlink_original = Path.unlink

        def unlink(ruta, missing_ok=False):
            if not doble.liberado:
                raise PermissionError(13, "archivo en uso")
            return unlink_original(ruta, missing_ok=missing_ok)

        with mock.patch.object(prueba_equipo.Path, "unlink", unlink):
            self._ejecutar(doble, disponibles=("x264",))
        self.assertEqual(list(self.carpeta.glob("*.mkv")), [])

    def test_detener_tambien_espera_y_borra(self):
        doble = self._doblar()
        doble.grabando = True
        unlink_original = Path.unlink

        def unlink(ruta, missing_ok=False):
            if not doble.liberado:
                raise PermissionError(13, "archivo en uso")
            return unlink_original(ruta, missing_ok=missing_ok)

        sobrantes = []
        with mock.patch.object(prueba_equipo.Path, "unlink", unlink):
            prueba_equipo._detener(doble, sobrantes)
        self.assertEqual(sobrantes, [])
        self.assertEqual(list(self.carpeta.glob("*.mkv")), [])

    def test_si_no_puede_borrar_lo_deja_en_el_resultado(self):
        original = _ajustes(fps=30, ancho_salida=1280, alto_salida=720)
        doble = self._doblar(ajustes=original, tasas={
            ("x264", 30, 720): (0.0, 0.0)})

        def unlink(_ruta, missing_ok=False):
            raise PermissionError(13, "archivo en uso")

        with mock.patch.object(prueba_equipo.Path, "unlink", unlink), \
                mock.patch.object(prueba_equipo, "_ESPERA_BORRADO", 0.05), \
                mock.patch.object(prueba_equipo, "_PASO_BORRADO", 0.01):
            resultado = self._ejecutar(doble, disponibles=("x264",))
        self.assertEqual(len(resultado.grabaciones), 1)
        self.assertTrue(resultado.grabaciones[0].endswith(".mkv"))
        self.assertTrue(Path(resultado.grabaciones[0]).is_file())


class TestNoSePuedeProbar(BasePrueba):

    def test_en_modo_avanzado_no_empieza(self):
        doble = self._doblar(avanzado=True)
        with self.assertRaises(obs_cliente.ObsError):
            self._ejecutar(doble, disponibles=("qsv", "x264"))
        self.assertNotIn("CreateScene", doble.llamadas)
        self.assertNotIn("StartRecord", doble.llamadas)

    def test_con_cualquier_salida_en_marcha_no_empieza(self):
        for tipo in ("GetStreamStatus", "GetRecordStatus",
                     "GetReplayBufferStatus"):
            with self.subTest(tipo=tipo):
                doble = self._doblar()
                doble.activos.add(tipo)
                with self.assertRaises(obs_cliente.ObsError):
                    self._ejecutar(doble, disponibles=("qsv", "x264"))
                self.assertNotIn("CreateScene", doble.llamadas)
                self.assertNotIn("StartRecord", doble.llamadas)


class TestPreparacion(BasePrueba):

    def test_devuelve_perfil_ajustes_y_duracion_maxima_sin_tocar_nada(self):
        doble = self._doblar()
        preparacion = prueba_equipo.preparar(
            doble, disponibles=("qsv", "x264"), calentamiento=2, medicion=10)
        self.assertEqual(preparacion.perfil, "Principal")
        self.assertEqual(preparacion.ajustes, replace(
            _ajustes(), carpeta_grabacion=str(self.carpeta)))
        self.assertEqual(preparacion.segundos_maximos, 48)
        self.assertNotIn("SetVideoSettings", doble.llamadas)
        self.assertNotIn("SetProfileParameter", doble.llamadas)
        self.assertNotIn("CreateScene", doble.llamadas)


if __name__ == "__main__":
    unittest.main()
