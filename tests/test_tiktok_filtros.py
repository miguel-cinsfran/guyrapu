# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Filtros de TikTok: nombres legibles y memoria de la sesión."""

import unittest

from guyrapu.capture.tiktok_filtros import MemoriaSesion, nombre_para_leer


class TestNombreParaLeer(unittest.TestCase):
    def test_normaliza_las_letras_decorativas(self):
        self.assertEqual(nombre_para_leer("𝓜𝓪𝓻𝓲𝓪"), "Maria")

    def test_sin_letra_ni_cifra_usa_el_usuario(self):
        self.assertEqual(nombre_para_leer("✦✦", "mariaj"), "mariaj")

    def test_sin_usuario_queda_usuario(self):
        self.assertEqual(nombre_para_leer("✦✦", ""), "Usuario")


class TestMemoriaSesion(unittest.TestCase):
    def test_una_persona_que_sigue_dos_veces_pasa_una(self):
        memoria = MemoriaSesion()
        self.assertTrue(memoria.registrar_seguidor("7"))
        self.assertFalse(memoria.registrar_seguidor("7"))

    def test_otra_persona_sigue_pasando(self):
        memoria = MemoriaSesion()
        self.assertTrue(memoria.registrar_seguidor("7"))
        self.assertTrue(memoria.registrar_seguidor("8"))

    def test_el_mismo_mensaje_pasa_una(self):
        memoria = MemoriaSesion()
        self.assertTrue(memoria.registrar_mensaje(42))
        self.assertFalse(memoria.registrar_mensaje(42))

    def test_con_el_tope_lleno_el_mas_viejo_se_olvida(self):
        memoria = MemoriaSesion()
        for ident in range(2000):
            memoria.registrar_mensaje(ident)
        memoria.registrar_mensaje(2000)
        self.assertFalse(memoria.registrar_mensaje(1999))
        self.assertTrue(memoria.registrar_mensaje(0))


if __name__ == "__main__":
    unittest.main()
