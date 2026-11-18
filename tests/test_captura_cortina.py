# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de captura_cortina: qué ajuste de OBS arregla una captura negra."""

import os
import unittest

from guyrapu.obs import captura_cortina, obs_activacion, obs_cliente


class ClienteFalso:
    def __init__(self):
        self.llamadas = []

    def pedir(self, tipo, datos=None, parada=None):
        self.llamadas.append((tipo, datos, parada))
        return {"responseData": {}}


class CambiarTest(unittest.TestCase):
    def test_pide_el_metodo_windows_10_por_captura_sin_pisar_otros_ajustes(self):
        cliente = ClienteFalso()
        captura_cortina.cambiar(cliente, ("Pantalla", "Juego"))
        self.assertEqual(cliente.llamadas, [
            ("SetInputSettings",
             {"inputName": "Pantalla", "inputSettings": {"method": 2},
              "overlay": True}, None),
            ("SetInputSettings",
             {"inputName": "Juego", "inputSettings": {"method": 2},
              "overlay": True}, None)])

    def test_sin_nombres_no_pide_nada(self):
        cliente = ClienteFalso()
        captura_cortina.cambiar(cliente, ())
        self.assertEqual(cliente.llamadas, [])


@unittest.skipUnless(os.environ.get("GUYRAPU_PRUEBAS_CON_RED") == "1",
                     "prueba real contra OBS: GUYRAPU_PRUEBAS_CON_RED=1")
class ObsRealTest(unittest.TestCase):
    """Crea una captura de pantalla, la cambia y lee el método que quedó."""

    def setUp(self):
        if not obs_activacion.obs_esta_en_ejecucion():
            self.skipTest("OBS no está abierto")
        self.cliente = obs_cliente.ClienteObs(obs_cliente.leer_ajustes())
        self.cliente.conectar()
        self.addCleanup(self.cliente.cerrar)
        datos = self.cliente.pedir("GetCurrentProgramScene").get(
            "responseData", {}) or {}
        self.escena = datos.get("currentProgramSceneName", "")
        self.nombre = "Guyrapu prueba captura cortina"
        self.cliente.pedir("CreateInput", {
            "sceneName": self.escena, "inputName": self.nombre,
            "inputKind": "monitor_capture",
            "inputSettings": {"method": 0},
            "sceneItemEnabled": False})
        self.addCleanup(self.cliente.pedir, "RemoveInput",
                        {"inputName": self.nombre})

    def test_cambia_el_metodo_y_obs_lo_deja_en_windows_10(self):
        captura_cortina.cambiar(self.cliente, (self.nombre,))
        ajustes = self.cliente.pedir(
            "GetInputSettings", {"inputName": self.nombre}).get(
                "responseData", {}).get("inputSettings", {}) or {}
        self.assertEqual(ajustes.get("method"), 2)


if __name__ == "__main__":
    unittest.main()
