# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de la regla de los tres usos de un perfil de OBS."""

import unittest

from guyrapu.obs import usos_perfil


class TestEtiquetaFila(unittest.TestCase):

    def test_sin_usos_ni_en_uso_es_solo_el_nombre(self):
        self.assertEqual(
            usos_perfil.etiqueta_fila("YouTube", False, []), "YouTube")

    def test_sin_usos_y_en_uso_lo_dice(self):
        self.assertEqual(
            usos_perfil.etiqueta_fila("YouTube", True, []),
            "YouTube (en uso)")

    def test_un_uso(self):
        self.assertEqual(
            usos_perfil.etiqueta_fila(
                "YouTube", False, ["perfil_horizontal"]),
            "YouTube (para transmitir en horizontal)")

    def test_tres_usos_con_en_uso(self):
        self.assertEqual(
            usos_perfil.etiqueta_fila(
                "YouTube", True,
                ["perfil_horizontal", "perfil_vertical", "perfil_grabar"]),
            "YouTube (en uso, para transmitir en horizontal, "
            "para transmitir en vertical, para grabar)")


class TestUsosDe(unittest.TestCase):

    def test_devuelve_los_usos_asignados_en_el_orden_de_la_lista(self):
        config = {"perfil_vertical": "TikTok",
                  "perfil_horizontal": "YouTube",
                  "perfil_grabar": "YouTube"}
        self.assertEqual(
            usos_perfil.usos_de("YouTube", config),
            ["perfil_horizontal", "perfil_grabar"])

    def test_nombre_vacio_no_tiene_usos(self):
        self.assertEqual(usos_perfil.usos_de("", {}), [])


class TestCambios(unittest.TestCase):

    def test_asignar_un_uso_que_tenia_otro_perfil(self):
        config = {"perfil_horizontal": "YouTube",
                  "perfil_vertical": "TikTok",
                  "perfil_grabar": ""}
        self.assertEqual(
            usos_perfil.cambios("Nuevo", {"perfil_vertical": True}, config),
            [("perfil_vertical", "Nuevo")])

    def test_desmarcar_un_uso_lo_deja_vacio(self):
        config = {"perfil_grabar": "Nuevo"}
        self.assertEqual(
            usos_perfil.cambios("Nuevo", {"perfil_grabar": False}, config),
            [("perfil_grabar", "")])

    def test_no_toca_los_usos_no_mencionados(self):
        config = {"perfil_horizontal": "YouTube",
                  "perfil_vertical": "TikTok",
                  "perfil_grabar": "Nuevo"}
        self.assertEqual(
            usos_perfil.cambios("Nuevo", {"perfil_grabar": False}, config),
            [("perfil_grabar", "")])

    def test_sin_cambios_devuelve_vacio(self):
        config = {"perfil_grabar": "Nuevo"}
        self.assertEqual(
            usos_perfil.cambios("Nuevo", {"perfil_grabar": True}, config), [])

    def test_desmarcar_un_uso_de_otro_perfil_no_lo_toca(self):
        config = {"perfil_horizontal": "YouTube",
                  "perfil_vertical": "TikTok",
                  "perfil_grabar": ""}
        self.assertEqual(
            usos_perfil.cambios(
                "YouTube",
                {"perfil_horizontal": True, "perfil_vertical": False,
                 "perfil_grabar": True}, config),
            [("perfil_grabar", "YouTube")])


class TestCambiosAlEliminar(unittest.TestCase):

    def test_deja_vacios_los_usos_del_perfil_eliminado(self):
        config = {"perfil_horizontal": "Eliminado",
                  "perfil_vertical": "TikTok",
                  "perfil_grabar": "Eliminado"}
        self.assertEqual(
            usos_perfil.cambios_al_eliminar("Eliminado", config),
            [("perfil_horizontal", ""), ("perfil_grabar", "")])

    def test_un_perfil_sin_usos_no_cambia_nada(self):
        self.assertEqual(
            usos_perfil.cambios_al_eliminar(
                "Otro", {"perfil_horizontal": "YouTube"}), [])


class TestTextoPara(unittest.TestCase):

    def test_une_los_usos_con_y(self):
        self.assertEqual(
            usos_perfil.texto_para(["perfil_horizontal", "perfil_grabar"]),
            "para transmitir en horizontal y para grabar")


if __name__ == "__main__":
    unittest.main()
