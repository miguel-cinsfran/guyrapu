# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Las piezas comunes para pedir y avisar de los paquetes de Interacción."""

import unittest
from unittest import mock

from guyrapu.ui import paquetes_ventana


class _CuadroCancelado:

    def __init__(self, *_args, **_kwargs):
        pass

    def ShowModal(self):
        return paquetes_ventana.wx.ID_CANCEL

    def Destroy(self):
        pass


class TestEscribir(unittest.TestCase):

    def test_un_fallo_avisa_y_devuelve_falso(self):
        with mock.patch.object(paquetes_ventana.paquetes, "exportar",
                               side_effect=OSError("disco lleno")), \
             mock.patch.object(paquetes_ventana.confirmar, "avisar") as avisar:
            resultado = paquetes_ventana.escribir(
                self, "salida.zip", "comandos", [], "Exportar comandos")
        self.assertFalse(resultado)
        avisar.assert_called_once()
        self.assertIn("disco lleno", avisar.call_args.args[1])
        self.assertEqual(avisar.call_args.args[2], "Exportar comandos")


class TestLeer(unittest.TestCase):

    def test_un_paquete_rechazado_avisa_y_devuelve_none(self):
        motivo = "El archivo no es un paquete de Guyrapu."
        with mock.patch.object(
                paquetes_ventana.paquetes, "leer",
                side_effect=paquetes_ventana.paquetes.PaqueteRechazado(
                    motivo)), \
             mock.patch.object(paquetes_ventana.confirmar, "avisar") as avisar:
            resultado = paquetes_ventana.leer(
                self, "entrada.zip", "comandos", "Importar comandos")
        self.assertIsNone(resultado)
        avisar.assert_called_once_with(
            self, motivo, "Importar comandos", "Aceptar",
            icono=paquetes_ventana.confirmar.ICON_ERROR)


class TestPedirRuta(unittest.TestCase):

    def test_un_cuadro_cancelado_no_devuelve_ruta(self):
        with mock.patch.object(paquetes_ventana.wx, "FileDialog",
                               _CuadroCancelado):
            self.assertIsNone(paquetes_ventana.pedir_ruta(
                self, "Exportar comandos", True))


if __name__ == "__main__":
    unittest.main()
