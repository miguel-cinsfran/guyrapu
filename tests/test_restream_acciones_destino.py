# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas del sonido de las acciones de la pestaña Destinos de Restream."""

import unittest
from types import SimpleNamespace
from unittest import mock

from guyrapu.restream.api import Canal
from guyrapu.ui import restream_acciones_destino as acciones


def _canal(activo=True):
    return Canal(1, 67, "TikTok", "uno", "", activo)


class TestEstadoCambiado(unittest.TestCase):

    def _cambiar(self, nuevo):
        destino = _canal(activo=not nuevo)
        ventana = SimpleNamespace(
            _destinos=[destino],
            _error_destinos="",
            _pagina_destinos=SimpleNamespace(mostrar=mock.Mock()),
            _actualizar_cuenta=mock.Mock())
        with mock.patch.object(acciones, "avisar") as avisar:
            acciones._estado_cambiado(ventana, destino, nuevo)
        return avisar

    def test_p2_activar_suena_reanudar(self):
        avisar = self._cambiar(True)

        avisar.assert_called_once_with("TikTok: uno activado", "reanudar")

    def test_p2_desactivar_suena_pausa(self):
        avisar = self._cambiar(False)

        avisar.assert_called_once_with("TikTok: uno desactivado", "pausa")


class TestTituloYAgregado(unittest.TestCase):

    def test_p3_titulo_cambiado_suena_listo(self):
        ventana = SimpleNamespace(
            _error_destinos="",
            _actualizar_cuenta=mock.Mock())
        with mock.patch.object(acciones, "avisar") as avisar:
            acciones._titulo_cambiado(ventana)

        avisar.assert_called_once_with("Título cambiado.", "listo")

    def test_p3_destino_agregado_suena_listo(self):
        canal = _canal()
        ventana = SimpleNamespace(
            _destinos=[],
            _error_destinos="",
            _pagina_destinos=SimpleNamespace(mostrar=mock.Mock()),
            _pagina_eventos=SimpleNamespace(actualizar_nombres=mock.Mock()),
            _actualizar_cuenta=mock.Mock())
        with mock.patch.object(acciones, "avisar") as avisar:
            acciones._destino_agregado(ventana, canal)

        avisar.assert_called_once_with("Destino agregado.", "listo")


if __name__ == "__main__":
    unittest.main()
