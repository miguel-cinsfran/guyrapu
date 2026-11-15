# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas del conteo de participación por persona en el chat."""

import unittest

from guyrapu.core.avisos_tiktok import TIPOS_AVISO
from guyrapu.core.config import (
    TIPO_ENTRADA, TIPO_ME_GUSTA, TIPO_MIEMBRO, TIPO_STICKER, TIPO_SUPERCHAT,
    TIPO_TEXTO,
)
from guyrapu.ui.lista_chat import MensajeChat
from guyrapu.ui.participacion_chat import Participacion


def _registro(autor="Ana", identificador="C", plataforma="youtube",
              tipo=TIPO_TEXTO):
    return MensajeChat(plataforma=plataforma, autor=autor,
                       identificador=identificador, texto="hola",
                       hora="12:00", tipo=tipo, monto="", rol="")


class TestParticipacion(unittest.TestCase):

    def test_ordena_por_cantidad_y_desempata_por_nombre_sin_tildes_ni_mayusculas(self):
        participacion = Participacion()
        for autor in ("Beto", "Beto", "ángel", "Ana"):
            participacion.sumar(_registro(autor=autor, identificador=autor))
        self.assertEqual(participacion.lineas(),
                         ["Beto: 2 mensajes", "Ana: 1 mensaje",
                          "ángel: 1 mensaje"])

    def test_el_plural_va_con_uno_y_varios(self):
        participacion = Participacion()
        participacion.sumar(_registro(autor="Ana", identificador="A"))
        participacion.sumar(_registro(autor="Beto", identificador="B"))
        participacion.sumar(_registro(autor="Beto", identificador="B"))
        self.assertEqual(participacion.lineas(),
                         ["Beto: 2 mensajes", "Ana: 1 mensaje"])

    def test_la_plataforma_solo_se_muestra_con_mas_de_una(self):
        una = Participacion()
        una.sumar(_registro(plataforma="youtube"))
        una.sumar(_registro(plataforma="youtube"))
        self.assertEqual(una.lineas(), ["Ana: 2 mensajes"])

        varias = Participacion()
        varias.sumar(_registro(plataforma="youtube"))
        varias.sumar(_registro(plataforma="tiktok"))
        self.assertEqual(varias.lineas(),
                         ["Ana (YouTube): 1 mensaje",
                          "Ana (TikTok): 1 mensaje"])

    def test_solo_cuenta_texto_y_superchat(self):
        participacion = Participacion()
        participacion.sumar(_registro(tipo=TIPO_TEXTO))
        participacion.sumar(_registro(tipo=TIPO_SUPERCHAT))
        for tipo in (TIPO_ENTRADA, TIPO_ME_GUSTA, TIPO_MIEMBRO, TIPO_STICKER,
                     next(iter(TIPOS_AVISO))):
            participacion.sumar(_registro(tipo=tipo))
        self.assertEqual(participacion.lineas(), ["Ana: 2 mensajes"])

    def test_el_ultimo_nombre_visto_gana(self):
        participacion = Participacion()
        participacion.sumar(_registro(autor="Ana", identificador="C"))
        participacion.sumar(_registro(autor="Ana María", identificador="C"))
        self.assertEqual(participacion.lineas(), ["Ana María: 2 mensajes"])

    def test_sin_identificador_se_identifica_por_el_autor(self):
        participacion = Participacion()
        participacion.sumar(_registro(autor="Ana", identificador=""))
        participacion.sumar(_registro(autor="Ana", identificador=""))
        participacion.sumar(_registro(autor="Beto", identificador=""))
        self.assertEqual(participacion.lineas(),
                         ["Ana: 2 mensajes", "Beto: 1 mensaje"])

    def test_limpiar_deja_el_conteo_vacio(self):
        participacion = Participacion()
        participacion.sumar(_registro())
        participacion.limpiar()
        self.assertTrue(participacion.vacia())
        self.assertEqual(participacion.lineas(), [])


if __name__ == "__main__":
    unittest.main()
