# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""El chat con la línea de vacío sigue contando y anunciando como antes."""

import unittest
from unittest import mock

from guyrapu.core.idioma import _
from guyrapu.ui import chat_acciones, chat_vivo


class _Lista:
    def __init__(self, filas):
        self.filas = list(filas)
        self.seleccion = 0 if filas else -1

    def GetCount(self):
        return len(self.filas)

    def GetString(self, indice):
        return self.filas[indice]

    def GetSelection(self):
        return self.seleccion


class TestLineaDeVacioEnLasAcciones(unittest.TestCase):

    def _acciones(self, lista):
        return chat_acciones.AccionesChat(
            lista, mock.Mock(), mock.Mock(), {}, mock.Mock(), mock.Mock())

    def test_el_filtro_con_el_chat_vacio_dice_cero_mensajes(self):
        acciones = self._acciones(_Lista([_(chat_vivo.VACIO_CHAT)]))
        with mock.patch.object(chat_acciones, "anunciar") as anunciar, \
                mock.patch.object(chat_acciones, "guardar_opcion"):
            acciones._aplicar_filtro(0)
        anunciar.assert_called_once_with("Filtro: Todos. 0 mensajes")

    def test_la_accion_sobre_la_linea_de_vacio_anuncia_la_ayuda(self):
        acciones = self._acciones(_Lista([_(chat_vivo.VACIO_CHAT)]))
        with mock.patch.object(chat_acciones, "anunciar") as anunciar:
            self.assertIsNone(acciones._get_selected_data())
        anunciar.assert_called_once_with(_(chat_vivo.VACIO_CHAT))


if __name__ == "__main__":
    unittest.main()
