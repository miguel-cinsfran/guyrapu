# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas del recorrido del asistente de perfiles, con un OBS de mentira.

No abre ventanas ni habla con OBS: el cliente guarda perfiles, perfil en uso
y ajustes, y la prueba del equipo se inyecta.
"""

import threading
import unittest
from dataclasses import replace
from types import SimpleNamespace

from guyrapu.obs import ajustes_perfil, asistente_perfiles, obs_cliente


class ClienteFalso:
    """Lo mínimo del WebSocket de OBS para crear, guardar y borrar perfiles."""

    def __init__(self, perfiles=("Casa", "Copia"), actual="Casa"):
        self.perfiles = list(perfiles)
        self.actual = actual
        self.video = {nombre: {"baseWidth": 1920, "baseHeight": 1080,
                               "outputWidth": 1280, "outputHeight": 720,
                               "fpsNumerator": 30, "fpsDenominator": 1}
                      for nombre in self.perfiles}
        self.parametros = {nombre: {} for nombre in self.perfiles}

    def _exigir(self, nombre):
        if nombre not in self.perfiles:
            raise obs_cliente.ObsError("No hay perfil " + nombre)
        return nombre

    def pedir(self, tipo, datos=None, parada=None):
        datos = datos or {}
        if tipo in ("GetStreamStatus", "GetRecordStatus",
                    "GetReplayBufferStatus"):
            return {"responseData": {"outputActive": False}}
        if tipo == "GetProfileList":
            return {"responseData": {"profiles": list(self.perfiles),
                                     "currentProfileName": self.actual}}
        if tipo == "SetCurrentProfile":
            self.actual = self._exigir(datos["profileName"])
            return {"responseData": {}}
        if tipo == "CreateProfile":
            nombre = datos["profileName"]
            if nombre in self.perfiles:
                raise obs_cliente.ObsError("Ya existe " + nombre)
            self.perfiles.append(nombre)
            self.video[nombre] = {}
            self.parametros[nombre] = {}
            return {"responseData": {}}
        if tipo == "RemoveProfile":
            nombre = self._exigir(datos["profileName"])
            if nombre == self.actual:
                raise obs_cliente.ObsError("En uso " + nombre)
            self.perfiles.remove(nombre)
            self.video.pop(nombre, None)
            self.parametros.pop(nombre, None)
            return {"responseData": {}}
        if tipo == "SetVideoSettings":
            self.video[self.actual] = dict(datos)
            return {"responseData": {}}
        if tipo == "SetProfileParameter":
            clave = (datos["parameterCategory"], datos["parameterName"])
            self.parametros[self.actual][clave] = datos["parameterValue"]
            return {"responseData": {}}
        if tipo == "GetStreamServiceSettings":
            return {"responseData": {
                "streamServiceType": "rtmp_custom",
                "streamServiceSettings": {"server": "", "key": ""}}}
        raise AssertionError("OBS falso no esperaba " + tipo)


def _prueba_que_aguanta(fps=24):
    def prueba(cliente, parada=None, disponibles=None):
        original = ajustes_perfil.valores_iniciales(False, "x264")
        aguantaron = replace(original, fps=fps)
        return SimpleNamespace(original=original, aguantaron=aguantaron,
                               ultimo=None, cancelada=False,
                               aguanta_tal_cual=False)
    return prueba


def _prueba_cancelada(parada):
    def prueba(cliente, parada=None, disponibles=None):
        parada.set()
        return SimpleNamespace(original=None, aguantaron=None, ultimo=None,
                               cancelada=True, aguanta_tal_cual=False)
    return prueba


class BaseAsistente(unittest.TestCase):

    def setUp(self):
        self.cliente = ClienteFalso()

    def _preparar(self, usos, probar=False, **extra):
        return asistente_perfiles.preparar(
            self.cliente, usos, probar=probar,
            disponibles=("x264",), **extra)


class TestCreacion(BaseAsistente):

    def test_crea_solo_los_usos_marcados_con_nombres_libres(self):
        self.cliente.perfiles.append("Guyrapu horizontal")
        resultado = self._preparar(["perfil_horizontal"])
        self.assertEqual([perfil.nombre for perfil in resultado.perfiles],
                         ["Guyrapu horizontal 2"])
        self.assertIn("Guyrapu horizontal 2", self.cliente.perfiles)

    def test_no_toca_los_perfiles_que_ya_existian(self):
        self.cliente.parametros["Casa"] = {
            ("SimpleOutput", "VBitrate"): "4000"}
        self.cliente.video["Casa"] = {"baseWidth": 2560, "baseHeight": 1440,
                                      "outputWidth": 1920,
                                      "outputHeight": 1080,
                                      "fpsNumerator": 60,
                                      "fpsDenominator": 1}
        antes = {nombre: (dict(self.cliente.video[nombre]),
                          dict(self.cliente.parametros[nombre]))
                 for nombre in ("Casa", "Copia")}
        self._preparar(["perfil_horizontal", "perfil_vertical"])
        for nombre in ("Casa", "Copia"):
            self.assertEqual(
                (self.cliente.video[nombre],
                 self.cliente.parametros[nombre]), antes[nombre])

    def test_el_perfil_de_grabar_queda_horizontal_e_igual_al_lienzo(self):
        resultado = self._preparar(["perfil_grabar"])
        nombre = resultado.perfiles[0].nombre
        parametros = self.cliente.parametros[nombre]
        self.assertEqual(parametros[("SimpleOutput", "RecQuality")], "Small")
        self.assertEqual(parametros[("SimpleOutput", "RecFormat2")], "mkv")
        self.assertEqual(
            (self.cliente.video[nombre]["outputWidth"],
             self.cliente.video[nombre]["outputHeight"]),
            (self.cliente.video[nombre]["baseWidth"],
             self.cliente.video[nombre]["baseHeight"]))
        self.assertEqual(resultado.perfiles[0].ajustes.calidad_grabacion,
                         "Small")
        self.assertEqual(resultado.perfiles[0].ajustes.formato_grabacion,
                         "mkv")


class TestPruebaDelEquipo(BaseAsistente):

    def test_guarda_lo_que_aguanto(self):
        resultado = self._preparar(
            ["perfil_horizontal"], probar=True,
            prueba=_prueba_que_aguanta(fps=24))
        nombre = resultado.perfiles[0].nombre
        self.assertTrue(resultado.perfiles[0].probado)
        self.assertEqual(resultado.perfiles[0].ajustes.fps, 24)
        self.assertEqual(
            self.cliente.parametros[nombre][("SimpleOutput", "VBitrate")],
            "2500")
        self.assertIn("Fotogramas por segundo: 30 a 24.",
                      resultado.perfiles[0].cambios)


class TestCancelacion(BaseAsistente):

    def test_al_cancelar_elimina_lo_creado_y_vuelve_al_perfil_de_antes(self):
        parada = threading.Event()
        resultado = self._preparar(
            ["perfil_horizontal"], probar=True, parada=parada,
            prueba=_prueba_cancelada(parada))
        self.assertTrue(resultado.cancelada)
        self.assertEqual(resultado.perfiles, ())
        self.assertNotIn("Guyrapu horizontal", self.cliente.perfiles)
        self.assertEqual(self.cliente.actual, "Casa")


class TestResumen(unittest.TestCase):

    def test_dice_uso_ajustes_cambios_anterior_y_lo_que_falta(self):
        ajustes = ajustes_perfil.valores_iniciales(True, "nvenc")
        perfil = asistente_perfiles.PerfilPreparado(
            "Guyrapu vertical", "perfil_vertical", ajustes,
            anterior="Perfil viejo", probado=True,
            cambios="Fotogramas por segundo: 30 a 24.")
        resultado = asistente_perfiles.ResultadoAsistente((perfil,))
        texto = "\n".join(
            asistente_perfiles.lineas_resumen(resultado,
                                              tiktok_sin_restream=True))
        self.assertIn("Guyrapu vertical", texto)
        self.assertIn("para transmitir en vertical", texto)
        self.assertIn("Fotogramas por segundo: 30 a 24.", texto)
        self.assertIn("Perfil viejo", texto)
        self.assertIn("Editar ajustes", texto)
        self.assertIn("Crear la versión vertical", texto)


if __name__ == "__main__":
    unittest.main()
