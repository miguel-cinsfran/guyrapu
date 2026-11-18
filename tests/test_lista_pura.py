# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de la parte pura de la pieza común de listas con acciones."""

import unittest

import wx

from guyrapu.ui import lista_pura, menu_lista


def _accion(clave, tecla=None, necesita_elemento=True, manejador=None,
            motivo=None, opciones=None):
    return lista_pura.Accion(
        clave=clave,
        etiqueta="&" + clave.capitalize(),
        manejador=manejador or (lambda: None),
        tecla=tecla,
        necesita_elemento=necesita_elemento,
        motivo=motivo,
        opciones=opciones)


ACCIONES = (
    _accion("editar", "intro"),
    _accion("renombrar", "f2"),
    _accion("eliminar", "suprimir"),
    _accion("nuevo", necesita_elemento=False),
)


class PruebaPartePura(unittest.TestCase):

    def test_cada_tecla_da_su_accion(self):
        casos = (
            (wx.WXK_RETURN, "editar"),
            (wx.WXK_NUMPAD_ENTER, "editar"),
            (wx.WXK_F2, "renombrar"),
            (wx.WXK_DELETE, "eliminar"),
            (wx.WXK_NUMPAD_DELETE, "eliminar"),
        )
        for codigo, esperado in casos:
            with self.subTest(codigo=codigo):
                self.assertEqual(
                    lista_pura.clave_de_tecla(
                        codigo, wx.MOD_NONE, ACCIONES),
                    esperado)

    def test_mayus_intro_y_ctrl_intro_llegan_a_su_accion(self):
        acciones = (
            _accion("continuar", "mayus+intro"),
            _accion("agregar", "ctrl+intro"),
        )
        for codigo in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            with self.subTest(codigo=codigo):
                self.assertEqual(
                    lista_pura.clave_de_tecla(
                        codigo, wx.MOD_SHIFT, acciones),
                    "continuar")
                self.assertEqual(
                    lista_pura.clave_de_tecla(
                        codigo, wx.MOD_CONTROL, acciones),
                    "agregar")
                self.assertIsNone(lista_pura.clave_de_tecla(
                    codigo, wx.MOD_NONE, acciones))
                self.assertIsNone(lista_pura.clave_de_tecla(
                    codigo, wx.MOD_ALT, acciones))
                self.assertIsNone(lista_pura.clave_de_tecla(
                    codigo, wx.MOD_SHIFT | wx.MOD_CONTROL, acciones))

    def test_alt_flecha_arriba_y_abajo_llegan_a_su_accion(self):
        acciones = (
            _accion("subir", "alt+flecha_arriba"),
            _accion("bajar", "alt+flecha_abajo"),
        )
        self.assertEqual(
            lista_pura.clave_de_tecla(wx.WXK_UP, wx.MOD_ALT, acciones),
            "subir")
        self.assertEqual(
            lista_pura.clave_de_tecla(wx.WXK_DOWN, wx.MOD_ALT, acciones),
            "bajar")
        self.assertIsNone(lista_pura.clave_de_tecla(
            wx.WXK_UP, wx.MOD_NONE, acciones))
        self.assertIsNone(lista_pura.clave_de_tecla(
            wx.WXK_DOWN, wx.MOD_ALT | wx.MOD_SHIFT, acciones))

    def test_ctrl_intro_sin_accion_que_lo_declare_da_none(self):
        for codigo in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            with self.subTest(codigo=codigo):
                self.assertIsNone(lista_pura.clave_de_tecla(
                    codigo, wx.MOD_CONTROL, ACCIONES))
                self.assertEqual(
                    lista_pura.clave_de_tecla(
                        codigo, wx.MOD_NONE, ACCIONES),
                    "editar")

    def test_f2_y_suprimir_siguen_respondiendo_con_modificadores(self):
        casos = (
            (wx.WXK_F2, wx.MOD_CONTROL | wx.MOD_SHIFT, "renombrar"),
            (wx.WXK_DELETE, wx.MOD_ALT, "eliminar"),
            (wx.WXK_NUMPAD_DELETE, wx.MOD_CONTROL, "eliminar"),
        )
        for codigo, modificadores, esperado in casos:
            with self.subTest(codigo=codigo):
                self.assertEqual(
                    lista_pura.clave_de_tecla(
                        codigo, modificadores, ACCIONES),
                    esperado)

    def test_aplicaciones_y_mayus_f10_dan_menu(self):
        self.assertEqual(
            lista_pura.clave_de_tecla(
                wx.WXK_WINDOWS_MENU, wx.MOD_NONE, ACCIONES),
            "menu")
        self.assertEqual(
            lista_pura.clave_de_tecla(
                wx.WXK_F10, wx.MOD_SHIFT, ACCIONES),
            "menu")

    def test_una_tecla_sin_accion_da_none(self):
        self.assertIsNone(lista_pura.clave_de_tecla(
            wx.WXK_F3, wx.MOD_NONE, ACCIONES))
        self.assertIsNone(lista_pura.clave_de_tecla(
            wx.WXK_F10, wx.MOD_NONE, ACCIONES))

    def test_las_encendidas_dependen_de_que_haya_elemento(self):
        sin_elemento = lista_pura.acciones_encendidas(ACCIONES, False)
        self.assertFalse(sin_elemento["editar"])
        self.assertFalse(sin_elemento["renombrar"])
        self.assertFalse(sin_elemento["eliminar"])
        self.assertTrue(sin_elemento["nuevo"])
        con_elemento = lista_pura.acciones_encendidas(ACCIONES, True)
        self.assertTrue(all(con_elemento.values()))

    def test_ctrl_d_da_su_accion_y_el_menu_dice_la_tecla(self):
        acciones = (_accion("duplicar", "ctrl+d"),)
        self.assertEqual(
            lista_pura.clave_de_tecla(
                ord("D"), wx.MOD_CONTROL, acciones),
            "duplicar")
        self.assertIsNone(lista_pura.clave_de_tecla(
            ord("D"), wx.MOD_CONTROL | wx.MOD_ALT, acciones))
        self.assertIsNone(lista_pura.clave_de_tecla(
            ord("D"), wx.MOD_CONTROL | wx.MOD_SHIFT, acciones))
        self.assertEqual(
            menu_lista.etiqueta_de_menu(acciones[0]),
            "&Duplicar\tCtrl+D")

    def test_ctrl_c_da_su_accion_solo_si_una_la_declara(self):
        acciones = (_accion("copiar", "ctrl+c"),)
        self.assertEqual(
            lista_pura.clave_de_tecla(
                ord("C"), wx.MOD_CONTROL, acciones),
            "copiar")
        self.assertEqual(
            lista_pura.clave_de_tecla(
                ord("c"), wx.MOD_CONTROL, acciones),
            "copiar")
        self.assertIsNone(lista_pura.clave_de_tecla(
            ord("C"), wx.MOD_CONTROL | wx.MOD_ALT, acciones))
        self.assertIsNone(lista_pura.clave_de_tecla(
            ord("C"), wx.MOD_NONE, ACCIONES))
        self.assertEqual(
            menu_lista.etiqueta_de_menu(acciones[0]),
            "&Copiar\tCtrl+C")


if __name__ == "__main__":
    unittest.main()
