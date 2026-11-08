# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de la relación entre una escena de OBS y su versión vertical.

Sin ventanas y sin OBS real: un cliente falso guarda perfil, lienzo y
escena al aire como lo haría el websocket.
"""

import unittest

from guyrapu.obs import escena_gemela, obs_cliente


class ObsFalso:

    def __init__(self, perfil="Horizontal", ancho=1920, alto=1080,
                 escena="Escena", escenas=("Escena",), salida=False):
        self.perfil = perfil
        self.ancho = ancho
        self.alto = alto
        self.escena = escena
        self.escenas = list(escenas)
        self.salida = salida
        self.llamadas = []

    def pedir(self, tipo, datos=None, parada=None):
        datos = datos or {}
        self.llamadas.append((tipo, dict(datos)))
        if tipo in ("GetStreamStatus", "GetRecordStatus",
                    "GetReplayBufferStatus"):
            return {"responseData": {"outputActive": self.salida}}
        if tipo == "GetProfileList":
            return {"responseData": {"profiles": ["Horizontal", "Vertical"],
                                     "currentProfileName": self.perfil}}
        if tipo == "SetCurrentProfile":
            self.perfil = datos["profileName"]
            return {"responseData": {}}
        if tipo == "GetVideoSettings":
            return {"responseData": {"baseWidth": self.ancho,
                                     "baseHeight": self.alto}}
        if tipo == "GetSceneList":
            return {"responseData": {"scenes": [
                {"sceneName": nombre} for nombre in self.escenas]}}
        if tipo == "GetCurrentProgramScene":
            return {"responseData": {"currentProgramSceneName": self.escena}}
        if tipo == "SetCurrentProgramScene":
            self.escena = datos["sceneName"]
            return {"responseData": {}}
        return {"responseData": {}}

    def tipos(self):
        return [tipo for tipo, _datos in self.llamadas]


class NombreGemelaTest(unittest.TestCase):

    def test_agrega_el_sufijo_fijo(self):
        self.assertEqual(escena_gemela.nombre_gemela("Principal"),
                         "Principal vertical")
        self.assertEqual(escena_gemela.SUFIJO, " vertical")

    def test_original_solo_si_termina_en_el_sufijo_y_existe(self):
        escenas = ("Principal", "Principal vertical")
        self.assertEqual(
            escena_gemela.original_de("Principal vertical", escenas),
            "Principal")
        self.assertIsNone(escena_gemela.original_de("Principal", escenas))
        self.assertIsNone(
            escena_gemela.original_de("Otra vertical", escenas))


class EnPerfilTest(unittest.TestCase):

    def test_corre_la_accion_con_el_perfil_y_vuelve_al_de_antes(self):
        cliente = ObsFalso(perfil="Horizontal")
        vistas = []

        def accion():
            vistas.append(cliente.perfil)
            return "hecho"

        self.assertEqual(
            escena_gemela.en_perfil(cliente, "Vertical", accion), "hecho")
        self.assertEqual(vistas, ["Vertical"])
        self.assertEqual(cliente.perfil, "Horizontal")

    def test_vuelve_al_perfil_aunque_la_accion_falle(self):
        cliente = ObsFalso(perfil="Horizontal")

        def accion():
            raise RuntimeError("falló el diseño")

        with self.assertRaisesRegex(RuntimeError, "falló el diseño"):
            escena_gemela.en_perfil(cliente, "Vertical", accion)
        self.assertEqual(cliente.perfil, "Horizontal")

    def test_con_una_salida_en_marcha_no_toca_el_perfil(self):
        cliente = ObsFalso(perfil="Horizontal", salida=True)
        with self.assertRaisesRegex(obs_cliente.ObsError, "salida en marcha"):
            escena_gemela.en_perfil(cliente, "Vertical", lambda: None)
        self.assertEqual(cliente.perfil, "Horizontal")
        self.assertNotIn("SetCurrentProfile", cliente.tipos())


class PonerSegunLienzoTest(unittest.TestCase):

    def test_lienzo_vertical_con_gemela_pone_la_gemela_al_aire(self):
        cliente = ObsFalso(ancho=720, alto=1280, escena="Principal",
                           escenas=("Principal", "Principal vertical"))
        self.assertEqual(escena_gemela.poner_segun_lienzo(cliente),
                         "Principal")
        self.assertEqual(cliente.escena, "Principal vertical")

    def test_lienzo_vertical_sin_gemela_no_cambia_nada(self):
        cliente = ObsFalso(ancho=720, alto=1280, escena="Principal",
                           escenas=("Principal",))
        self.assertIsNone(escena_gemela.poner_segun_lienzo(cliente))
        self.assertEqual(cliente.escena, "Principal")

    def test_lienzo_horizontal_con_gemela_al_aire_pone_la_original(self):
        cliente = ObsFalso(ancho=1920, alto=1080,
                           escena="Principal vertical",
                           escenas=("Principal", "Principal vertical"))
        self.assertEqual(escena_gemela.poner_segun_lienzo(cliente),
                         "Principal vertical")
        self.assertEqual(cliente.escena, "Principal")

    def test_lienzo_horizontal_con_una_escena_normal_no_cambia_nada(self):
        cliente = ObsFalso(ancho=1920, alto=1080, escena="Principal",
                           escenas=("Principal",))
        self.assertIsNone(escena_gemela.poner_segun_lienzo(cliente))
        self.assertEqual(cliente.escena, "Principal")

    def test_lienzo_horizontal_con_gemela_sin_original_no_cambia_nada(self):
        cliente = ObsFalso(ancho=1920, alto=1080,
                           escena="Principal vertical",
                           escenas=("Principal vertical",))
        self.assertIsNone(escena_gemela.poner_segun_lienzo(cliente))
        self.assertEqual(cliente.escena, "Principal vertical")


if __name__ == "__main__":
    unittest.main()
