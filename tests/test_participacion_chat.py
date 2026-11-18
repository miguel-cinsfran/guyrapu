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
from guyrapu.ui.participacion_chat import ORDEN_REGALOS, Participacion


def _registro(autor="Ana", identificador="C", plataforma="youtube",
              tipo=TIPO_TEXTO, monto=""):
    return MensajeChat(plataforma=plataforma, autor=autor,
                       identificador=identificador, texto="hola",
                       hora="12:00", tipo=tipo, monto=monto, rol="")


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

    def test_suma_los_diamantes_de_los_regalos(self):
        participacion = Participacion()
        participacion.sumar(_registro(tipo=TIPO_SUPERCHAT,
                                      monto="200 diamantes"))
        participacion.sumar(_registro(tipo=TIPO_SUPERCHAT,
                                      monto="40 diamantes"))
        self.assertEqual(participacion.lineas(),
                         ["Ana: 2 mensajes, 240 diamantes"])

    def test_los_superchats_se_suman_por_moneda(self):
        participacion = Participacion()
        for monto in ("US$10.00", "US$5.00", "€7.50"):
            participacion.sumar(_registro(tipo=TIPO_SUPERCHAT, monto=monto))
        self.assertEqual(participacion.lineas(),
                         ["Ana: 3 mensajes, 15,00 US$, 7,50 €"])

    def test_un_sticker_con_importe_cuenta_como_superchat(self):
        participacion = Participacion()
        participacion.sumar(_registro(tipo=TIPO_STICKER, monto="US$5.00"))
        self.assertEqual(participacion.lineas(),
                         ["Ana: 1 mensaje, 5,00 US$"])

    def test_un_monto_ilegible_cuenta_solo_el_mensaje(self):
        participacion = Participacion()
        participacion.sumar(_registro(tipo=TIPO_SUPERCHAT, monto="gracias"))
        self.assertEqual(participacion.lineas(), ["Ana: 1 mensaje"])

    def test_el_orden_por_regalos_deja_primero_los_diamantes_y_los_superchats(self):
        participacion = Participacion()
        participacion.sumar(_registro(autor="Ana", identificador="A"))
        participacion.sumar(_registro(autor="Beto", identificador="B",
                                      tipo=TIPO_SUPERCHAT,
                                      monto="US$50.00"))
        for _ in range(5):
            participacion.sumar(_registro(autor="Carla", identificador="C"))
        participacion.sumar(_registro(autor="Dani", identificador="D",
                                      tipo=TIPO_SUPERCHAT,
                                      monto="100 diamantes"))
        participacion.sumar(_registro(autor="Eva", identificador="E",
                                      tipo=TIPO_SUPERCHAT,
                                      monto="200 diamantes"))
        self.assertEqual(
            participacion.lineas(ORDEN_REGALOS),
            ["Eva: 1 mensaje, 200 diamantes",
             "Dani: 1 mensaje, 100 diamantes",
             "Beto: 1 mensaje, 50,00 US$",
             "Carla: 5 mensajes",
             "Ana: 1 mensaje"])
        self.assertEqual(
            participacion.lineas(),
            ["Carla: 5 mensajes",
             "Ana: 1 mensaje",
             "Beto: 1 mensaje, 50,00 US$",
             "Dani: 1 mensaje, 100 diamantes",
             "Eva: 1 mensaje, 200 diamantes"])

    def test_limpiar_deja_el_conteo_vacio(self):
        participacion = Participacion()
        participacion.sumar(_registro())
        participacion.limpiar()
        self.assertTrue(participacion.vacia())
        self.assertEqual(participacion.lineas(), [])


if __name__ == "__main__":
    unittest.main()
