# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de las reacciones de la supervisión a lo que informa OBS."""

import threading
import unittest

from guyrapu.obs import reacciones_supervisor


class EsperaDeArranqueTest(unittest.TestCase):
    def test_anuncia_cada_veredicto_una_vez_y_recupera(self):
        veredictos = ["reconectando", "esperando", "reconectando", "enviando"]
        anuncios = []

        def esperar(cliente, parada):
            return veredictos.pop(0)

        veredicto, recuperado = reacciones_supervisor.esperar_arranque(
            esperar, None, threading.Event(), lambda *args: anuncios.append(args),
            lambda valor: "frase de " + valor)
        self.assertEqual(veredicto, "enviando")
        self.assertTrue(recuperado)
        self.assertEqual(anuncios, [
            ("frase de reconectando", "transmision_problema"),
            ("frase de esperando", "aviso"),
        ])

    def test_sin_salida_anuncia_con_importante_y_termina(self):
        anuncios = []

        def esperar(cliente, parada):
            return "sin_salida"

        veredicto, recuperado = reacciones_supervisor.esperar_arranque(
            esperar, None, threading.Event(), lambda *args: anuncios.append(args),
            lambda valor: "frase de " + valor)
        self.assertEqual(veredicto, "sin_salida")
        self.assertFalse(recuperado)
        self.assertEqual(anuncios, [
            ("frase de sin_salida", "transmision_problema", True)])


class LectorDeEstadoTest(unittest.TestCase):
    class Gestor:
        def __init__(self, fallos):
            self.fallos = fallos
            self.llamadas = []
            self.activo = True

        def conectar(self, parada):
            self.llamadas.append("conectar")

        def estado_transmision(self, parada):
            self.llamadas.append("estado")
            if self.fallos:
                self.fallos -= 1
                raise RuntimeError("sin respuesta")
            return {"outputActive": self.activo}

    def test_un_fallo_avisa_una_vez_y_la_vuelta_tambien(self):
        anuncios = []
        gestor = self.Gestor(fallos=1)
        lector = reacciones_supervisor.LectorDeEstado(
            gestor, threading.Event(), lambda *args: anuncios.append(args),
            en_ejecucion=lambda: True)
        estado, apagado = lector.leer()
        self.assertIsNone(estado)
        self.assertFalse(apagado)
        estado, apagado = lector.leer()
        self.assertTrue(estado["outputActive"])
        self.assertFalse(apagado)
        self.assertEqual(anuncios, [
            ("OBS no responde. Se sigue intentando.", "obs_sin_respuesta"),
            ("OBS volvió a responder.", "obs_responde"),
        ])
        self.assertEqual(gestor.llamadas.count("conectar"), 1)

    def test_con_obs_cerrado_avisa_el_fin_sin_anunciar_la_falla(self):
        anuncios = []
        gestor = self.Gestor(fallos=1)
        lector = reacciones_supervisor.LectorDeEstado(
            gestor, threading.Event(), lambda *args: anuncios.append(args),
            en_ejecucion=lambda: False)
        estado, apagado = lector.leer()
        self.assertIsNone(estado)
        self.assertTrue(apagado)
        self.assertEqual(anuncios, [])


class MarcarImportanteTest(unittest.TestCase):
    def test_despues_de_enviar_no_abre_cuadro(self):
        self.assertFalse(reacciones_supervisor.marcar_importante(
            True, "transmision_problema", "un aviso", True))
        self.assertTrue(reacciones_supervisor.marcar_importante(
            False, "transmision_problema", "un aviso", True))
        self.assertFalse(reacciones_supervisor.marcar_importante(
            True, "error", "un aviso", True))

    def test_el_aviso_del_fin_de_youtube_sigue_importante(self):
        self.assertTrue(reacciones_supervisor.marcar_importante(
            True, "transmision_problema",
            "YouTube no confirmó el fin del directo. Se reintentará durante "
            "10 minutos.", False))
