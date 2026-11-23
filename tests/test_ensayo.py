# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""El registro de un mensaje de ensayo y sus destinos."""

import unittest
from datetime import datetime
from types import SimpleNamespace

from guyrapu.core import plataformas
from guyrapu.core.config import (
    TIPO_COMPARTIR, TIPO_ME_GUSTA, TIPO_MIEMBRO, TIPO_SEGUIR,
    TIPO_SUPERCHAT, TIPO_TEXTO)
from guyrapu.core.idioma import _
from guyrapu.core.sonidos_eventos import ROL_MODERADOR
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


class TestTipos(unittest.TestCase):

    def test_los_tipos_son_los_de_cada_plataforma(self):
        self.assertEqual(
            [(_(tipo.rotulo), tipo.clave)
             for tipo in ensayo.tipos_de(plataformas.YOUTUBE)],
            [("Mensaje", ensayo.MENSAJE), ("Super Chat", ensayo.SUPER_CHAT),
             ("Membresía", ensayo.MEMBRESIA)])
        self.assertEqual(
            [(_(tipo.rotulo), tipo.clave)
             for tipo in ensayo.tipos_de(plataformas.TIKTOK)],
            [("Mensaje", ensayo.MENSAJE), ("Regalo", ensayo.REGALO),
             ("Seguidor nuevo", ensayo.SEGUIDOR), ("Me gusta", ensayo.ME_GUSTA),
             ("Directo compartido", ensayo.COMPARTIR)])

    def test_cada_tipo_produce_el_registro_de_su_captura(self):
        casos = (
            (plataformas.YOUTUBE, ensayo.MENSAJE, TIPO_TEXTO, "hola", "", "100"),
            (plataformas.YOUTUBE, ensayo.SUPER_CHAT, TIPO_SUPERCHAT,
             "hola", "5,00 €", "5,00 €"),
            (plataformas.YOUTUBE, ensayo.MEMBRESIA, TIPO_MIEMBRO, "", "", "100"),
            (plataformas.TIKTOK, ensayo.MENSAJE, TIPO_TEXTO, "hola", "", "100"),
            (plataformas.TIKTOK, ensayo.REGALO, TIPO_SUPERCHAT,
             "Rosa", "100 diamantes", "100"),
            (plataformas.TIKTOK, ensayo.SEGUIDOR, TIPO_SEGUIR, "", "", "100"),
            (plataformas.TIKTOK, ensayo.ME_GUSTA, TIPO_ME_GUSTA, "", "1", "100"),
            (plataformas.TIKTOK, ensayo.COMPARTIR, TIPO_COMPARTIR, "", "", "100"),
        )
        for plataforma, tipo, interno, texto, monto, cantidad in casos:
            with self.subTest(tipo=tipo, plataforma=plataforma):
                registro = ensayo.registro(
                    "Ana", "hola", plataforma, tipo, cantidad, regalo="Rosa")
                self.assertEqual(registro.tipo, interno)
                self.assertEqual(registro.texto, texto)
                self.assertEqual(registro.monto, monto)
                self.assertEqual(registro.plataforma, plataforma)

    def test_los_campos_de_cada_tipo_son_solo_los_suyos(self):
        self.assertEqual(
            {tipo.clave: tipo.campos for tipo in ensayo.TIPOS},
            {ensayo.MENSAJE: ("mensaje",),
             ensayo.SUPER_CHAT: ("cantidad", "mensaje"),
             ensayo.MEMBRESIA: (),
             ensayo.REGALO: ("regalo", "cantidad"),
             ensayo.SEGUIDOR: (), ensayo.ME_GUSTA: (),
             ensayo.COMPARTIR: ()})


class TestRol(unittest.TestCase):

    def test_el_rol_llega_al_registro_como_en_la_captura(self):
        registro = ensayo.registro(
            "Ana", "hola", plataformas.YOUTUBE, ensayo.MENSAJE,
            rol=ROL_MODERADOR)
        self.assertEqual(registro.rol, ROL_MODERADOR)
        self.assertEqual(
            ensayo.registro("Ana", "hola", plataformas.YOUTUBE,
                            ensayo.MENSAJE).rol, "")

    def test_solo_youtube_tiene_rol(self):
        self.assertTrue(ensayo.con_rol(plataformas.YOUTUBE))
        self.assertFalse(ensayo.con_rol(plataformas.TIKTOK))
        self.assertEqual([_(rotulo) for rotulo, _valor in ensayo.ROLES],
                         ["Público", "Moderador", "Propietario del canal"])


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
