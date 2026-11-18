# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas del armado del menú contextual de una lista."""

import unittest

from guyrapu.ui import lista_acciones, menu_lista


def _accion(clave, tecla=None, necesita_elemento=True, manejador=None,
            motivo=None):
    return lista_acciones.Accion(
        clave=clave,
        etiqueta="&" + clave.capitalize(),
        manejador=manejador or (lambda: None),
        tecla=tecla,
        necesita_elemento=necesita_elemento,
        motivo=motivo)


class PruebaEtiquetaDeMenu(unittest.TestCase):

    def test_el_menu_muestra_las_teclas_con_modificador(self):
        casos = (
            ("mayus+intro", "\tShift+Enter"),
            ("ctrl+intro", "\tCtrl+Enter"),
            ("alt+flecha_arriba", "\tAlt+Up"),
            ("alt+flecha_abajo", "\tAlt+Down"),
        )
        for tecla, sufijo in casos:
            with self.subTest(tecla=tecla):
                self.assertEqual(
                    menu_lista.etiqueta_de_menu(_accion("hacer", tecla)),
                    "&Hacer" + sufijo)

    def test_la_etiqueta_del_menu_lleva_el_motivo(self):
        con_motivo = _accion(
            "responder", tecla="intro",
            motivo=lambda: "Sin sesión de YouTube")
        self.assertEqual(
            menu_lista.etiqueta_de_menu(con_motivo),
            "&Responder (sin sesión de YouTube)\tEnter")
        sin_motivo = _accion("responder", motivo=lambda: "")
        self.assertEqual(
            menu_lista.etiqueta_de_menu(sin_motivo),
            "&Responder")


if __name__ == "__main__":
    unittest.main()
