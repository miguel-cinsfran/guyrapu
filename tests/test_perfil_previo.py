# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de la vuelta al perfil de OBS anterior a un directo.

Sin ventanas y sin OBS real: un cliente falso responde como el websocket
y la conexión del gestor se reemplaza por un doble.
"""

import unittest
from unittest import mock

from guyrapu.obs import obs_cliente, perfil_previo


class ObsFalso:
    """Cliente de OBS con salidas, búfer y lista de perfiles."""

    def __init__(self, perfiles=("YouTube", "TikTok"), actual="TikTok",
                 transmitiendo=False, grabando=False, buffer=False,
                 fallo="", escena="Escena", escenas=("Escena",)):
        self.perfiles = list(perfiles)
        self.actual = actual
        self.transmitiendo = transmitiendo
        self.grabando = grabando
        self.buffer = buffer
        self.fallo = fallo
        self.escena = escena
        self.escenas = list(escenas)
        self.llamadas = []

    def pedir(self, tipo, datos=None, parada=None):
        self.llamadas.append((tipo, dict(datos or {})))
        if tipo == self.fallo:
            raise obs_cliente.ObsError("OBS no responde.")
        if tipo == "GetStreamStatus":
            return {"responseData": {"outputActive": self.transmitiendo}}
        if tipo == "GetRecordStatus":
            return {"responseData": {"outputActive": self.grabando}}
        if tipo == "GetReplayBufferStatus":
            return {"responseData": {"outputActive": self.buffer}}
        if tipo == "GetProfileList":
            return {"responseData": {"profiles": list(self.perfiles),
                                     "currentProfileName": self.actual}}
        if tipo == "SetCurrentProfile":
            self.actual = datos["profileName"]
            return {"responseData": {}}
        if tipo == "GetCurrentProgramScene":
            return {"responseData": {"currentProgramSceneName": self.escena}}
        if tipo == "GetSceneList":
            return {"responseData": {"scenes": [
                {"sceneName": nombre} for nombre in self.escenas]}}
        if tipo == "SetCurrentProgramScene":
            self.escena = datos["sceneName"]
            return {"responseData": {}}
        return {"responseData": {}}

    def tipos(self):
        return [tipo for tipo, _datos in self.llamadas]

    def cambios(self):
        return [datos for tipo, datos in self.llamadas
                if tipo == "SetCurrentProfile"]


class GestorFalso:
    """Doble de GestorPanelObs para comprobar conexión y cierre."""

    def __init__(self):
        self._cliente = ObsFalso()
        self.conectado = False
        self.cerrado = False

    def conectar(self):
        self.conectado = True

    def cerrar(self):
        self.cerrado = True


class HiloFalso:
    def __init__(self, target, nombre):
        self.target = target
        self.nombre = nombre

    def start(self):
        self.target()


class PerfilPrevioTest(unittest.TestCase):

    def setUp(self):
        with perfil_previo._CERROJO:
            perfil_previo._PENDIENTE = ""
            perfil_previo._ESCENA_PENDIENTE = ()

    def test_recordar_y_volver_una_sola_vez(self):
        perfil_previo.recordar("YouTube", "TikTok")
        cliente = ObsFalso()
        self.assertEqual(perfil_previo.volver(cliente), "YouTube")
        self.assertEqual(cliente.cambios(), [{"profileName": "YouTube"}])
        self.assertEqual(perfil_previo.volver(cliente), "")
        self.assertEqual(cliente.cambios(), [{"profileName": "YouTube"}])

    def test_cualquier_salida_activa_o_buffer_frena_la_vuelta(self):
        for estado in ("transmitiendo", "grabando", "buffer"):
            with self.subTest(estado=estado):
                self.setUp()
                perfil_previo.recordar("YouTube", "TikTok")
                cliente = ObsFalso(**{estado: True})
                self.assertEqual(perfil_previo.volver(cliente), "")
                self.assertEqual(cliente.cambios(), [])
                setattr(cliente, estado, False)
                self.assertEqual(perfil_previo.volver(cliente), "YouTube")
                self.assertEqual(cliente.cambios(),
                                 [{"profileName": "YouTube"}])

    def test_buffer_que_falla_cuenta_como_apagado(self):
        perfil_previo.recordar("YouTube", "TikTok")
        cliente = ObsFalso(fallo="GetReplayBufferStatus")
        self.assertEqual(perfil_previo.volver(cliente), "YouTube")
        self.assertEqual(cliente.cambios(), [{"profileName": "YouTube"}])

    def test_perfil_que_ya_no_existe_se_olvida(self):
        perfil_previo.recordar("YouTube", "TikTok")
        cliente = ObsFalso(perfiles=("TikTok",), actual="TikTok")
        self.assertEqual(perfil_previo.volver(cliente), "")
        self.assertEqual(cliente.cambios(), [])
        cliente.perfiles.append("YouTube")
        self.assertEqual(perfil_previo.volver(cliente), "")

    def test_si_obs_no_responde_conserva_el_pendiente(self):
        perfil_previo.recordar("YouTube", "TikTok")
        cliente = ObsFalso(fallo="GetStreamStatus")
        self.assertEqual(perfil_previo.volver(cliente), "")
        cliente.fallo = ""
        self.assertEqual(perfil_previo.volver(cliente), "YouTube")

    def test_recordar_no_pisa_el_primero_ni_el_mismo_perfil(self):
        perfil_previo.recordar("YouTube", "YouTube")
        self.assertEqual(perfil_previo.volver(ObsFalso()), "")
        perfil_previo.recordar("YouTube", "TikTok")
        perfil_previo.recordar("Otro", "TikTok")
        cliente = ObsFalso()
        self.assertEqual(perfil_previo.volver(cliente), "YouTube")
        self.assertEqual(cliente.cambios(), [{"profileName": "YouTube"}])

    def test_recordar_sin_perfil_actual_no_guarda_nada(self):
        perfil_previo.recordar("", "TikTok")
        self.assertEqual(perfil_previo.volver(ObsFalso()), "")

    def test_volver_restaura_la_escena_despues_del_perfil(self):
        perfil_previo.recordar("YouTube", "TikTok")
        perfil_previo.recordar_escena("Escena", "Escena vertical")
        cliente = ObsFalso(escena="Escena vertical",
                           escenas=("Escena", "Escena vertical"))
        self.assertEqual(perfil_previo.volver(cliente), "YouTube")
        self.assertEqual(cliente.actual, "YouTube")
        self.assertEqual(cliente.escena, "Escena")
        tipos = cliente.tipos()
        self.assertLess(tipos.index("SetCurrentProfile"),
                        tipos.index("SetCurrentProgramScene"))

    def test_no_restaura_la_escena_si_la_del_aire_cambio(self):
        perfil_previo.recordar_escena("Escena", "Escena vertical")
        cliente = ObsFalso(escena="Otra",
                           escenas=("Escena", "Escena vertical", "Otra"))
        self.assertEqual(perfil_previo.volver(cliente), "")
        self.assertEqual(cliente.escena, "Otra")
        self.assertNotIn("SetCurrentProgramScene", cliente.tipos())

    def test_vuelve_a_la_escena_aunque_no_haya_perfil_pendiente(self):
        perfil_previo.recordar_escena("Escena", "Escena vertical")
        cliente = ObsFalso(escena="Escena vertical",
                           escenas=("Escena", "Escena vertical"))
        self.assertEqual(perfil_previo.volver(cliente), "")
        self.assertEqual(cliente.escena, "Escena")
        self.assertNotIn("SetCurrentProfile", cliente.tipos())
        self.assertEqual(perfil_previo._ESCENA_PENDIENTE, ())

    def test_una_escena_que_ya_no_existe_se_olvida(self):
        perfil_previo.recordar_escena("Escena", "Escena vertical")
        cliente = ObsFalso(escena="Escena vertical",
                           escenas=("Escena vertical",))
        self.assertEqual(perfil_previo.volver(cliente), "")
        self.assertEqual(cliente.escena, "Escena vertical")
        self.assertEqual(perfil_previo._ESCENA_PENDIENTE, ())

    def test_tras_supervision_llama_al_original_y_vuelve(self):
        original = mock.Mock()
        gestor = GestorFalso()
        hilos = []

        def crear_hilo(target, nombre, **kwargs):
            hilos.append((target, nombre))
            return HiloFalso(target, nombre)

        perfil_previo.recordar("YouTube", "TikTok")
        with mock.patch("guyrapu.obs.obs_panel.GestorPanelObs",
                        return_value=gestor), \
                mock.patch.object(perfil_previo.diagnostico, "crear_hilo",
                                  side_effect=crear_hilo), \
                mock.patch.object(perfil_previo, "volver",
                                  return_value="YouTube") as volver:
            perfil_previo.tras_supervision(original)()
        original.assert_called_once_with()
        self.assertEqual(hilos[0][1], "VolverPerfilObs")
        volver.assert_called_once_with(gestor._cliente)
        self.assertTrue(gestor.conectado)
        self.assertTrue(gestor.cerrado)

    def test_tras_supervision_sin_pendiente_no_conecta(self):
        original = mock.Mock()
        with mock.patch("guyrapu.obs.obs_panel.GestorPanelObs") as gestor, \
                mock.patch.object(perfil_previo.diagnostico,
                                  "crear_hilo") as crear_hilo:
            perfil_previo.tras_supervision(original)()
        original.assert_called_once_with()
        gestor.assert_not_called()
        crear_hilo.assert_not_called()


if __name__ == "__main__":
    unittest.main()
