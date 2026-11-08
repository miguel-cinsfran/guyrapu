# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de `guyrapu/obs/perfil_grabacion.py`, sin ventanas ni OBS real."""

import unittest
from unittest import mock

from guyrapu.obs import obs_grabacion, perfil_grabacion, perfil_previo


class ClienteFalso:
    """Cliente de OBS que registra los pedidos y cambia el perfil si se lo piden."""

    def __init__(self, actual="Directo", perfiles=("Directo", "Grabar"),
                 grabando=False, transmitiendo=False, buffer=False,
                 ruta="C:/Videos/x.mkv"):
        self.actual = actual
        self.perfiles = list(perfiles)
        self.grabando = grabando
        self.transmitiendo = transmitiendo
        self.buffer = buffer
        self.ruta = ruta
        self.pedidos = []

    def pedir(self, tipo, datos=None, parada=None):
        self.pedidos.append((tipo, datos))
        if tipo == "GetRecordStatus":
            return {"responseData": {"outputActive": self.grabando,
                                     "outputPaused": False}}
        if tipo == "GetStreamStatus":
            return {"responseData": {"outputActive": self.transmitiendo}}
        if tipo == "GetReplayBufferStatus":
            return {"responseData": {"outputActive": self.buffer}}
        if tipo == "GetProfileList":
            return {"responseData": {"profiles": list(self.perfiles),
                                     "currentProfileName": self.actual}}
        if tipo == "SetCurrentProfile":
            self.actual = datos["profileName"]
            return {"responseData": {}}
        if tipo == "StartRecord":
            self.grabando = True
            return {"responseData": {}}
        if tipo == "StopRecord":
            self.grabando = False
            return {"responseData": {"outputPath": self.ruta}}
        return {"responseData": {}}

    def pedidos_de(self, tipo):
        return [datos for pedido, datos in self.pedidos if pedido == tipo]


class TestPerfilGrabacion(unittest.TestCase):

    def setUp(self):
        with perfil_previo._CERROJO:
            perfil_previo._PENDIENTE = ""
        dormir = mock.patch.object(obs_grabacion.time, "sleep")
        dormir.start()
        self.addCleanup(dormir.stop)

    def test_sin_perfil_inicia_sin_cambiar_el_de_obs(self):
        cliente = ClienteFalso()
        activa, ruta, aviso = perfil_grabacion.alternar(cliente, "")

        self.assertTrue(activa)
        self.assertEqual(ruta, "")
        self.assertEqual(aviso, "")
        self.assertEqual(cliente.pedidos_de("SetCurrentProfile"), [])

    def test_el_perfil_elegido_va_antes_de_iniciar_y_se_vuelve_al_detener(self):
        cliente = ClienteFalso()
        activa, _ruta, aviso = perfil_grabacion.alternar(cliente, "Grabar")

        self.assertTrue(activa)
        self.assertEqual(aviso, "")
        tipos = [tipo for tipo, _datos in cliente.pedidos]
        self.assertLess(tipos.index("SetCurrentProfile"), tipos.index("StartRecord"))
        self.assertEqual(cliente.pedidos_de("SetCurrentProfile"),
                         [{"profileName": "Grabar"}])

        activa, ruta, aviso = perfil_grabacion.alternar(cliente, "Grabar")

        self.assertFalse(activa)
        self.assertEqual(ruta, "C:/Videos/x.mkv")
        self.assertEqual(aviso, "")
        self.assertEqual(cliente.pedidos_de("SetCurrentProfile")[-1],
                         {"profileName": "Directo"})

    def test_con_el_directo_en_marcha_graba_con_el_actual_y_avisa(self):
        cliente = ClienteFalso(transmitiendo=True)
        activa, _ruta, aviso = perfil_grabacion.alternar(cliente, "Grabar")

        self.assertTrue(activa)
        self.assertEqual(
            aviso, "Con el directo en marcha, se graba con el perfil Directo.")
        self.assertEqual(cliente.pedidos_de("SetCurrentProfile"), [])

    def test_con_los_clips_en_marcha_graba_con_el_actual_y_avisa(self):
        cliente = ClienteFalso(buffer=True)
        activa, _ruta, aviso = perfil_grabacion.alternar(cliente, "Grabar")

        self.assertTrue(activa)
        self.assertEqual(
            aviso, "Con los clips en marcha, se graba con el perfil Directo.")
        self.assertEqual(cliente.pedidos_de("SetCurrentProfile"), [])

    def test_si_el_perfil_ya_no_existe_graba_con_el_actual_y_avisa(self):
        cliente = ClienteFalso(perfiles=("Directo",))
        activa, _ruta, aviso = perfil_grabacion.alternar(cliente, "Grabar")

        self.assertTrue(activa)
        self.assertEqual(
            aviso, "OBS no tiene el perfil Grabar: se graba con el perfil Directo.")
        self.assertEqual(cliente.pedidos_de("SetCurrentProfile"), [])

    def test_con_el_mismo_perfil_que_el_actual_no_cambia_ni_avisa(self):
        cliente = ClienteFalso()
        activa, _ruta, aviso = perfil_grabacion.alternar(cliente, "Directo")

        self.assertTrue(activa)
        self.assertEqual(aviso, "")
        self.assertEqual(cliente.pedidos_de("SetCurrentProfile"), [])

    def test_un_perfil_de_grabar_llamado_youtube_no_se_traduce(self):
        cliente = ClienteFalso(perfiles=("Directo", "YouTube"))
        with mock.patch("guyrapu.obs.perfil_por_uso.perfil_elegido",
                        return_value="Mi horizontal"):
            activa, _ruta, aviso = perfil_grabacion.alternar(
                cliente, "YouTube")

        self.assertTrue(activa)
        self.assertEqual(aviso, "")
        self.assertEqual(cliente.pedidos_de("SetCurrentProfile"),
                         [{"profileName": "YouTube"}])

    def test_si_el_buffer_falla_se_toma_como_apagado(self):
        cliente = ClienteFalso()

        def pedir(tipo, datos=None, parada=None):
            if tipo == "GetReplayBufferStatus":
                cliente.pedidos.append((tipo, datos))
                from guyrapu.obs import obs_cliente
                raise obs_cliente.ObsError("sin búfer")
            return ClienteFalso.pedir(cliente, tipo, datos, parada)

        cliente.pedir = pedir
        activa, _ruta, aviso = perfil_grabacion.alternar(cliente, "Grabar")

        self.assertTrue(activa)
        self.assertEqual(aviso, "")
        self.assertEqual(cliente.pedidos_de("SetCurrentProfile"),
                         [{"profileName": "Grabar"}])


if __name__ == "__main__":
    unittest.main()
