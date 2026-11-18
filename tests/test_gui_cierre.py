# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas del aviso y del lanzamiento al salir con un fin pendiente."""

import unittest
from unittest import mock

from guyrapu.ui import gui_cierre

TEXTO = ("El directo de YouTube sigue abierto porque no hay conexión. "
         "Guyrapu lo finalizará solo cuando vuelva la conexión, aunque "
         "la aplicación esté cerrada.")


class TestCierreConFinPendiente(unittest.TestCase):

    def _frame(self):
        frame = mock.Mock()
        frame._apagando = False
        frame._cerrar_sin_preguntar = False
        frame._config = {"confirmar_salida": False}
        frame._conectado = False
        frame._supervisor = None
        frame._obs_transmitiendo = False
        frame._obs_vigilante = None
        frame._diagnostico_parada = mock.Mock()
        frame.chat_vivo = mock.Mock()
        frame.on_desconectar_cb = None
        frame._parada = mock.Mock()
        frame._rep_panel = mock.Mock()
        frame._musica = mock.Mock()
        frame._recientes = mock.Mock()
        frame._worker = mock.Mock()
        frame._timer = mock.Mock()
        frame._diagnostico_timer = mock.Mock()
        return frame

    def _evento(self, vetable=True):
        evento = mock.Mock()
        evento.CanVeto.return_value = vetable
        return evento

    def _cerrar(self, frame, evento, pendientes):
        gestor = mock.Mock()
        gestor.lista.return_value = []
        with mock.patch.object(gui_cierre, "gestor", return_value=gestor), \
                mock.patch.object(gui_cierre.confirmar, "avisar") as avisar, \
                mock.patch.object(gui_cierre.finalizar_aparte,
                                  "lanzar") as lanzar, \
                mock.patch.object(gui_cierre.fin_pendiente, "leer",
                                  return_value=pendientes), \
                mock.patch.object(gui_cierre, "comprobar_cierre"), \
                mock.patch.object(gui_cierre.overlay_servidor, "apagar"), \
                mock.patch.object(gui_cierre._snd, "cerrar"), \
                mock.patch.object(
                    gui_cierre.diagnostico, "hilos_vivos_de_la_aplicacion",
                    return_value=()):
            gui_cierre.on_close(frame, evento)
        return avisar, lanzar

    def test_con_un_pendiente_avisa_y_lanza(self):
        frame = self._frame()

        avisar, lanzar = self._cerrar(
            frame, self._evento(), [{"id": "GNu-oOA-6Tc"}])

        avisar.assert_called_once_with(
            frame, TEXTO, "Directo sin finalizar", "Aceptar")
        lanzar.assert_called_once_with()
        self.assertTrue(frame._apagando)

    def test_sin_pendientes_no_avisa_ni_lanza(self):
        frame = self._frame()

        avisar, lanzar = self._cerrar(frame, self._evento(), [])

        avisar.assert_not_called()
        lanzar.assert_not_called()
        self.assertTrue(frame._apagando)

    def test_sin_veto_lanza_sin_aviso(self):
        frame = self._frame()

        avisar, lanzar = self._cerrar(
            frame, self._evento(vetable=False), [{"id": "GNu-oOA-6Tc"}])

        avisar.assert_not_called()
        lanzar.assert_called_once_with()
        self.assertTrue(frame._apagando)


if __name__ == "__main__":
    unittest.main()
