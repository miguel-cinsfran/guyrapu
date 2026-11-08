# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de los ítems de moderación del menú de una fila del chat."""

import unittest
from types import SimpleNamespace
from unittest import mock

from guyrapu.ui import menu_moderacion
from guyrapu.ui.lista_chat import MensajeChat


class MenuFalso:

    def __init__(self):
        self.etiquetas = {}
        self.handlers = {}
        self.separadores = 0

    def Append(self, identificador, etiqueta):
        self.etiquetas[identificador] = etiqueta

    def AppendSeparator(self):
        self.separadores += 1

    def Bind(self, _evento, handler, id):
        self.handlers[id] = handler


class FrameFalso:

    def __init__(self, live_chat_id="live"):
        self.sesion = SimpleNamespace(live_chat_id=live_chat_id)
        self.moderar = mock.Mock()

    def _moderar(self, autor, canal_id, segundos):
        self.moderar(autor, canal_id, segundos)


def _registro(plataforma="youtube", autor="Ana", identificador="CANAL1"):
    return MensajeChat(plataforma=plataforma, autor=autor,
                       identificador=identificador, texto="hola",
                       hora="12:00:00", tipo="text", monto="")


class TestItemsDeModeracion(unittest.TestCase):

    def test_agrega_los_dos_items_y_modera_con_el_identificador(self):
        frame = FrameFalso()
        menu = MenuFalso()
        with mock.patch.object(menu_moderacion.youtube_api, "google_disponible",
                               return_value=True), \
                mock.patch.object(menu_moderacion.credenciales, "hay_sesion",
                                  return_value=True):
            menu_moderacion.agregar(menu, frame, _registro(), "Carlos")

        self.assertEqual(menu.separadores, 1)
        self.assertIn("Suspender temporalmente a Carlos (5 minutos)",
                      menu.etiquetas.values())
        self.assertIn("Ocultar a Carlos en el canal de YouTube",
                      menu.etiquetas.values())
        for handler in menu.handlers.values():
            handler(None)
        self.assertIn(mock.call("Ana", "CANAL1", 300), frame.moderar.call_args_list)
        self.assertIn(mock.call("Ana", "CANAL1", None), frame.moderar.call_args_list)

    def test_sin_moderacion_no_agrega_nada(self):
        casos = {
            "tiktok": (_registro(plataforma="tiktok"), "live", True, True),
            "sin identificador": (_registro(identificador=""), "live", True, True),
            "sin autor": (_registro(autor=""), "live", True, True),
            "sin sesion": (_registro(), "", True, True),
            "sin google": (_registro(), "live", False, True),
            "sin credenciales": (_registro(), "live", True, False),
            "sin seleccion": (None, "live", True, True),
        }
        for nombre, (registro, live_chat_id, google, hay_sesion) in casos.items():
            with self.subTest(nombre):
                menu = MenuFalso()
                frame = FrameFalso(live_chat_id)
                with mock.patch.object(menu_moderacion.youtube_api,
                                       "google_disponible", return_value=google), \
                        mock.patch.object(menu_moderacion.credenciales,
                                          "hay_sesion", return_value=hay_sesion):
                    menu_moderacion.agregar(menu, frame, registro, "Carlos")
                self.assertEqual(menu.etiquetas, {})
                self.assertEqual(menu.handlers, {})
                self.assertEqual(menu.separadores, 0)
                frame.moderar.assert_not_called()


if __name__ == "__main__":
    unittest.main()
