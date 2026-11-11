# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Sonido de cada estado de la conexión de un chat, según su historia."""

import unittest

from guyrapu.capture.sonido_reconexion import SonidoReconexion


class PruebasSonidoReconexion(unittest.TestCase):

    def test_la_primera_conexion_con_intentos_fallidos(self):
        sonido = SonidoReconexion()
        self.assertEqual(sonido.recibir("conectando"), "conectando")
        self.assertIsNone(sonido.recibir("error_conexion"))
        self.assertEqual(sonido.recibir("reintentando"), "conectando")
        self.assertEqual(sonido.recibir("conectando"), "conectando")
        self.assertEqual(sonido.recibir("conectado"), "conectado")

    def test_el_corte_y_la_vuelta_suenan_distinto_de_conectar(self):
        sonido = SonidoReconexion()
        self.assertEqual(sonido.recibir("conectado"), "conectado")
        self.assertEqual(sonido.recibir("reintentando"), "chat_cortado")
        self.assertEqual(sonido.recibir("reintentando"), "conectando")
        self.assertEqual(sonido.recibir("conectado"), "chat_reconectado")
        self.assertEqual(sonido.recibir("reintentando"), "chat_cortado")


if __name__ == "__main__":
    unittest.main()
