# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""El registro de un mensaje de ensayo y sus destinos."""

import unittest
from datetime import datetime
from types import SimpleNamespace

from guyrapu.core import plataformas
from guyrapu.core.config import TIPO_SUPERCHAT, TIPO_TEXTO
from guyrapu.interaction import ensayo


class TestRegistro(unittest.TestCase):

    def test_mensaje_usa_el_tipo_de_texto_y_sin_monto(self):
        registro = ensayo.registro(
            "Público de prueba", "hola", plataformas.YOUTUBE,
            ensayo.MENSAJE, ahora=datetime(2026, 11, 19, 12, 30, 5))
        self.assertEqual(registro.autor, "Público de prueba")
        self.assertEqual(registro.texto, "hola")
        self.assertEqual(registro.plataforma, plataformas.YOUTUBE)
        self.assertEqual(registro.tipo, TIPO_TEXTO)
        self.assertEqual(registro.monto, "")
        self.assertEqual(registro.hora, "12:30:05")

    def test_super_chat_lleva_la_cantidad_con_su_moneda(self):
        registro = ensayo.registro(
            "Ana", "gracias", plataformas.YOUTUBE,
            ensayo.SUPER_CHAT, "5,00 €",
            ahora=datetime(2026, 11, 19, 12, 30, 5))
        self.assertEqual(registro.tipo, TIPO_SUPERCHAT)
        self.assertEqual(registro.monto, "5,00 €")
        self.assertEqual(registro.plataforma, plataformas.YOUTUBE)

    def test_regalo_lleva_los_diamantes_y_la_plataforma_de_tiktok(self):
        registro = ensayo.registro(
            "Ana", "un regalo", plataformas.TIKTOK,
            ensayo.REGALO, "100",
            ahora=datetime(2026, 11, 19, 12, 30, 5))
        self.assertEqual(registro.tipo, TIPO_SUPERCHAT)
        self.assertEqual(registro.monto, "100 diamantes")
        self.assertEqual(registro.plataforma, plataformas.TIKTOK)


class TestDestinos(unittest.TestCase):

    def test_el_ensayo_solo_va_al_video(self):
        self.assertEqual(ensayo.destinos(), {"video"})


class TestEstado(unittest.TestCase):

    def test_en_ensayo_sin_directo_cuenta_como_activo(self):
        frame = SimpleNamespace(_conectado=False, _ensayo=True)
        self.assertTrue(ensayo.en_vivo_o_ensayo(frame))

    def test_sin_ensayo_ni_directo_no_cuenta_como_activo(self):
        frame = SimpleNamespace(_conectado=False, _ensayo=False)
        self.assertFalse(ensayo.en_vivo_o_ensayo(frame))

    def test_con_directo_cuenta_como_activo(self):
        frame = SimpleNamespace(_conectado=True, _ensayo=False)
        self.assertTrue(ensayo.en_vivo_o_ensayo(frame))
