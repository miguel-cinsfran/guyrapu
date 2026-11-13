# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de los caminos de plazo y error de las esperas cortas de OBS.

Complementan las pruebas de cada módulo con los casos que no cubrían: el
vencimiento del plazo, la parada y el error de la consulta.
"""

import threading
import unittest
from pathlib import Path
from unittest import mock

from guyrapu.core import tiempo as tiempo_core
from guyrapu.obs import (
    fuente_nueva,
    obs_camara_nueva,
    obs_cliente,
    obs_clips,
    obs_grabacion,
    perfiles_obs,
    prueba_conexion,
    prueba_equipo,
    prueba_vertical,
)


class RelojFalso:
    def __init__(self):
        self.ahora = 0.0
        self.pausas = []

    def leer(self):
        return self.ahora

    def dormir(self, segundos, parada=None):
        self.pausas.append(segundos)
        self.ahora += segundos


class SondaFuente:
    """`pedir` falso con la sonda visible mientras no se indique lo contrario."""

    def __init__(self, desaparece_en=None):
        self.desaparece_en = desaparece_en
        self.consultas = 0

    def pedir(self, tipo, datos=None, parada=None):
        if tipo == "GetInputList":
            self.consultas += 1
            presente = (self.desaparece_en is None
                        or self.consultas < self.desaparece_en)
            entradas = ([{"inputName": fuente_nueva.NOMBRE_SONDA}]
                        if presente else [])
            return {"responseData": {"inputs": entradas}}
        if tipo == "GetSceneItemList":
            return {"responseData": {"sceneItems": []}}
        raise AssertionError(tipo)


class SondaCamara:
    """Cliente falso con la sonda de la lista de cámaras."""

    def __init__(self, desaparece_en=None):
        self.desaparece_en = desaparece_en
        self.consultas = 0

    def pedir(self, tipo, datos=None, parada=None):
        if tipo == "GetInputList":
            self.consultas += 1
            presente = (self.desaparece_en is None
                        or self.consultas < self.desaparece_en)
            entradas = ([{"inputName": obs_camara_nueva.NOMBRE_SONDA}]
                        if presente else [])
            return {"responseData": {"inputs": entradas}}
        if tipo == "GetSceneItemList":
            return {"responseData": {"sceneItems": []}}
        raise AssertionError(tipo)


class Perfiles:
    def __init__(self, perfiles, actual):
        self.perfiles = list(perfiles)
        self.actual = actual

    def pedir(self, tipo, datos=None, parada=None):
        if tipo == "GetProfileList":
            return {"responseData": {"profiles": list(self.perfiles),
                                     "currentProfileName": self.actual}}
        raise AssertionError(tipo)


class EstadoStream:
    def __init__(self, activo, falla=False):
        self.activo = activo
        self.falla = falla
        self.consultas = 0

    def pedir(self, tipo, datos=None, parada=None):
        self.consultas += 1
        if self.falla:
            raise obs_cliente.ObsError("OBS sin responder")
        return {"responseData": {"outputActive": self.activo}}


class Clips:
    def __init__(self, fallos, ruta):
        self.fallos = fallos
        self.ruta = ruta
        self.consultas = 0

    def pedir(self, tipo, datos=None, parada=None):
        if tipo == "SaveReplayBuffer":
            return {}
        if tipo == "GetLastReplayBufferReplay":
            self.consultas += 1
            if self.consultas <= self.fallos:
                raise obs_cliente.ObsError("todavía no está")
            return {"responseData": {"savedReplayPath": self.ruta}}
        raise AssertionError(tipo)


class SondaFueraTest(unittest.TestCase):
    """La espera de la sonda termina en silencio por plazo o por éxito."""

    def test_fuente_nueva_vuelve_cuando_la_sonda_desaparece(self):
        reloj = RelojFalso()
        fuente_nueva._esperar_sonda_fuera(
            SondaFuente(desaparece_en=2).pedir, "Escena",
            dormir=reloj.dormir, reloj=reloj.leer)
        self.assertEqual(reloj.pausas, [0.05])

    def test_fuente_nueva_vence_el_plazo_sin_error(self):
        reloj = RelojFalso()
        fuente_nueva._esperar_sonda_fuera(
            SondaFuente().pedir, "Escena", dormir=reloj.dormir,
            reloj=reloj.leer)
        self.assertGreaterEqual(reloj.ahora, 3.0)
        self.assertTrue(all(0 < pausa <= 0.05 for pausa in reloj.pausas))

    def test_obs_camara_nueva_vuelve_cuando_la_sonda_desaparece(self):
        reloj = RelojFalso()
        obs_camara_nueva._esperar_sonda_fuera(
            SondaCamara(desaparece_en=2), "Escena",
            dormir=reloj.dormir, reloj=reloj.leer)
        self.assertEqual(reloj.pausas, [0.05])

    def test_obs_camara_nueva_vence_el_plazo_sin_error(self):
        reloj = RelojFalso()
        obs_camara_nueva._esperar_sonda_fuera(
            SondaCamara(), "Escena", dormir=reloj.dormir, reloj=reloj.leer)
        self.assertGreaterEqual(reloj.ahora, 3.0)
        self.assertTrue(all(0 < pausa <= 0.05 for pausa in reloj.pausas))


class PerfilesEsperaTest(unittest.TestCase):
    """La espera de perfiles devuelve, vence el plazo o atiende la parada."""

    def test_devuelve_cuando_la_condicion_se_cumple(self):
        doble = Perfiles(["A"], "A")
        self.assertIsNone(perfiles_obs._esperar(
            doble, lambda perfiles, actual: actual == "A", None))

    def test_al_vencer_lanza_el_mensaje_de_cambio(self):
        doble = Perfiles(["A"], "A")
        reloj = RelojFalso()
        with mock.patch.object(perfiles_obs, "_ESPERA_CAMBIO", 0.05), \
                mock.patch.object(perfiles_obs, "_INTERVALO_CAMBIO", 0.01), \
                mock.patch.object(perfiles_obs.time, "monotonic",
                                  reloj.leer), \
                mock.patch.object(perfiles_obs.time, "sleep", reloj.dormir):
            with self.assertRaisesRegex(obs_cliente.ObsError, "no terminó"):
                perfiles_obs._esperar(
                    doble, lambda perfiles, actual: False, None)
        self.assertTrue(reloj.pausas)

    def test_con_la_parada_puesta_lanza_cancelada(self):
        parada = threading.Event()
        parada.set()
        with self.assertRaisesRegex(obs_cliente.ObsError, "cancelada"):
            perfiles_obs._esperar(
                Perfiles(["A"], "A"), lambda perfiles, actual: True, parada)


class EsperaDetencionTest(unittest.TestCase):
    """Las esperas de detención vuelven True, False por plazo o por error."""

    def test_prueba_conexion_vuelve_true_cuando_la_salida_esta_inactiva(self):
        self.assertTrue(prueba_conexion._esperar_detencion(
            EstadoStream(activo=False)))

    def test_prueba_conexion_el_plazo_devuelve_false(self):
        reloj = RelojFalso()
        doble = EstadoStream(activo=True)
        with mock.patch.object(prueba_conexion, "_ESPERA_DETENCION", 0.05), \
                mock.patch.object(prueba_conexion, "_PASO_DETENCION", 0.01), \
                mock.patch.object(prueba_conexion.time, "monotonic",
                                  reloj.leer):
            self.assertFalse(prueba_conexion._esperar_detencion(
                doble, dormir=reloj.dormir))
        self.assertGreaterEqual(doble.consultas, 2)

    def test_prueba_conexion_un_error_devuelve_false_y_lo_registra(self):
        with self.assertLogs("guyrapu.prueba_conexion",
                             level="DEBUG") as registro:
            self.assertFalse(prueba_conexion._esperar_detencion(
                EstadoStream(activo=True, falla=True)))
        self.assertIn("no informó el fin de la transmisión",
                      "\n".join(registro.output))

    def test_equipo_vuelve_true_cuando_la_grabacion_esta_inactiva(self):
        self.assertTrue(prueba_equipo._esperar_detencion(
            EstadoStream(activo=False)))

    def test_equipo_el_plazo_devuelve_false(self):
        reloj = RelojFalso()
        doble = EstadoStream(activo=True)
        with mock.patch.object(prueba_equipo, "_ESPERA_DETENCION", 0.05), \
                mock.patch.object(prueba_equipo, "_PASO_DETENCION", 0.01), \
                mock.patch.object(tiempo_core.time, "monotonic", reloj.leer), \
                mock.patch.object(tiempo_core.time, "sleep", reloj.dormir):
            self.assertFalse(prueba_equipo._esperar_detencion(doble))
        self.assertGreaterEqual(doble.consultas, 2)

    def test_equipo_un_error_devuelve_false_y_lo_registra(self):
        with self.assertLogs("guyrapu.prueba_equipo",
                             level="DEBUG") as registro:
            self.assertFalse(prueba_equipo._esperar_detencion(
                EstadoStream(activo=True, falla=True)))
        self.assertIn("no informó el fin de la grabación",
                      "\n".join(registro.output))


class VerticalTest(unittest.TestCase):
    """Detención y borrado del vertical con plazo y error."""

    def test_detencion_vuelve_true_cuando_deja_de_grabar(self):
        cliente = prueba_vertical.ClienteVertical(object())
        with mock.patch.object(prueba_vertical.lienzo_vertical, "estado",
                               lambda _cliente: {"grabando": False}):
            self.assertTrue(cliente._esperar_detencion())

    def test_detencion_el_plazo_devuelve_false(self):
        reloj = RelojFalso()
        cliente = prueba_vertical.ClienteVertical(object())
        with mock.patch.object(prueba_vertical, "_ESPERA_DETENCION", 0.05), \
                mock.patch.object(prueba_vertical, "_PASO_DETENCION", 0.01), \
                mock.patch.object(prueba_vertical.lienzo_vertical, "estado",
                                  lambda _cliente: {"grabando": True}), \
                mock.patch.object(tiempo_core.time, "monotonic", reloj.leer), \
                mock.patch.object(tiempo_core.time, "sleep", reloj.dormir):
            self.assertFalse(cliente._esperar_detencion())

    def test_detencion_un_error_devuelve_false_y_lo_registra(self):
        cliente = prueba_vertical.ClienteVertical(object())
        with mock.patch.object(prueba_vertical.lienzo_vertical, "estado",
                               side_effect=obs_cliente.ObsError("sin estado")), \
                self.assertLogs("guyrapu.prueba_vertical",
                                level="DEBUG") as registro:
            self.assertFalse(cliente._esperar_detencion())
        self.assertIn("no se pudo leer el estado vertical",
                      "\n".join(registro.output))

    def test_borrar_vence_el_plazo_con_el_archivo_tomado(self):
        reloj = RelojFalso()
        with mock.patch.object(prueba_vertical, "_ESPERA_BORRADO", 0.05), \
                mock.patch.object(prueba_vertical, "_PASO_BORRADO", 0.01), \
                mock.patch.object(tiempo_core.time, "monotonic", reloj.leer), \
                mock.patch.object(tiempo_core.time, "sleep", reloj.dormir), \
                mock.patch.object(Path, "unlink",
                                  side_effect=PermissionError(13, "en uso")), \
                self.assertLogs("guyrapu.prueba_vertical",
                                level="WARNING") as registro:
            self.assertFalse(prueba_vertical._borrar(Path("clip.mp4")))
        self.assertIn("la grabación vertical quedó en",
                      "\n".join(registro.output))


class GuardarClipTest(unittest.TestCase):
    """Un error de OBS en la consulta no corta la espera de la ruta."""

    def test_un_error_de_obs_no_corta_la_espera(self):
        reloj = RelojFalso()
        doble = Clips(fallos=2, ruta="C:/clips/clip.mkv")
        with self.assertLogs("guyrapu.obs_clips",
                             level="DEBUG") as registro:
            ruta = obs_clips.guardar(
                doble, dormir=reloj.dormir, reloj=reloj.leer,
                intervalo=0.2, limite=1.0)
        self.assertEqual(ruta, "C:/clips/clip.mkv")
        self.assertIn("OBS todavía no devolvió el clip",
                      "\n".join(registro.output))


class ConfirmarGrabacionTest(unittest.TestCase):
    """La primera consulta de la grabación sale una décima después."""

    def test_consulta_una_decima_despues_y_no_antes(self):
        reloj = RelojFalso()
        instantes = []

        def pedir(tipo, datos=None, parada=None):
            instantes.append(reloj.ahora)
            return {"outputActive": True}

        with mock.patch.object(tiempo_core.time, "monotonic", reloj.leer), \
                mock.patch.object(tiempo_core.time, "sleep", reloj.dormir):
            obs_grabacion._confirmar_grabacion(pedir, True)
        self.assertEqual(instantes, [0.1])


if __name__ == "__main__":
    unittest.main()
