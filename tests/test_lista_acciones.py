# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de la pieza común de listas con acciones."""

import unittest
from unittest import mock

import wx

from tests.ventanas_prueba import app_de_prueba, destruir
from guyrapu.ui import lista_acciones


def _accion(clave, tecla=None, necesita_elemento=True, manejador=None):
    return lista_acciones.Accion(
        clave=clave,
        etiqueta="&" + clave.capitalize(),
        manejador=manejador or (lambda: None),
        tecla=tecla,
        necesita_elemento=necesita_elemento)


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
                    lista_acciones.clave_de_tecla(
                        codigo, wx.MOD_NONE, ACCIONES),
                    esperado)

    def test_aplicaciones_y_mayus_f10_dan_menu(self):
        self.assertEqual(
            lista_acciones.clave_de_tecla(
                wx.WXK_WINDOWS_MENU, wx.MOD_NONE, ACCIONES),
            "menu")
        self.assertEqual(
            lista_acciones.clave_de_tecla(
                wx.WXK_F10, wx.MOD_SHIFT, ACCIONES),
            "menu")

    def test_una_tecla_sin_accion_da_none(self):
        self.assertIsNone(lista_acciones.clave_de_tecla(
            wx.WXK_F3, wx.MOD_NONE, ACCIONES))
        self.assertIsNone(lista_acciones.clave_de_tecla(
            wx.WXK_F10, wx.MOD_NONE, ACCIONES))

    def test_las_encendidas_dependen_de_que_haya_elemento(self):
        sin_elemento = lista_acciones.acciones_encendidas(ACCIONES, False)
        self.assertFalse(sin_elemento["editar"])
        self.assertFalse(sin_elemento["renombrar"])
        self.assertFalse(sin_elemento["eliminar"])
        self.assertTrue(sin_elemento["nuevo"])
        con_elemento = lista_acciones.acciones_encendidas(ACCIONES, True)
        self.assertTrue(all(con_elemento.values()))


class PruebaListaConVacio(unittest.TestCase):

    def setUp(self):
        self.app = app_de_prueba()
        self.marco = wx.Frame(None)
        self.addCleanup(destruir, self.marco)
        self.lista = wx.ListBox(self.marco)
        self.vacio = lista_acciones.ListaConVacio(
            self.lista, "Sin elementos.")

    def test_vacia_deja_la_linea_elegida_y_sin_indice(self):
        self.vacio.fijar([])
        self.assertTrue(self.vacio.vacia())
        self.assertEqual(self.lista.GetCount(), 1)
        self.assertEqual(self.lista.GetString(0), "Sin elementos.")
        self.assertEqual(self.lista.GetSelection(), 0)
        self.assertIsNone(self.vacio.indice())

    def test_sin_elemento_con_la_lista_vacia_anuncia_el_texto(self):
        self.vacio.fijar([])
        with mock.patch.object(lista_acciones, "anunciar") as anunciar:
            self.vacio.sin_elemento()
        anunciar.assert_called_once_with("Sin elementos.")

    def test_con_elementos_sin_elegir_anuncia_sin_seleccion(self):
        self.vacio.fijar(["a", "b"])
        self.assertFalse(self.vacio.vacia())
        self.lista.SetSelection(wx.NOT_FOUND)
        with mock.patch.object(lista_acciones, "anunciar") as anunciar:
            self.vacio.sin_elemento()
        anunciar.assert_called_once_with("Sin selección")


class PruebaConLista(unittest.TestCase):

    def setUp(self):
        self.app = app_de_prueba()
        self.marco = wx.Frame(None)
        self.addCleanup(destruir, self.marco)
        self.lista = wx.ListBox(self.marco)
        self.llamadas = []
        self.acciones = (
            _accion("editar", "intro",
                    manejador=lambda: self.llamadas.append("editar")),
            _accion("renombrar", "f2",
                    manejador=lambda: self.llamadas.append("renombrar")),
            _accion("eliminar", "suprimir",
                    manejador=lambda: self.llamadas.append("eliminar")),
            _accion("nuevo", necesita_elemento=False,
                    manejador=lambda: self.llamadas.append("nuevo")),
        )
        self.pieza = lista_acciones.ListaConAcciones(
            self.lista, self.acciones, "Sin elementos.")

    def _menu(self):
        menu = self.pieza._construir_menu()
        self.addCleanup(menu.Destroy)
        return menu

    def _tecla(self, tipo, codigo):
        evento = wx.KeyEvent(tipo)
        evento.KeyCode = codigo
        self.lista.GetEventHandler().ProcessEvent(evento)

    def test_fijar_vacio_deja_la_linea_elegida_y_sin_indice(self):
        self.pieza.fijar([])
        self.assertEqual(self.lista.GetCount(), 1)
        self.assertEqual(self.lista.GetString(0), "Sin elementos.")
        self.assertEqual(self.lista.GetSelection(), 0)
        self.assertIsNone(self.pieza.indice())

    def test_ejecutar_con_la_lista_vacia_anuncia_el_vacio_y_no_llama(self):
        self.pieza.fijar([])
        with mock.patch.object(lista_acciones, "anunciar") as anunciar:
            self.pieza.ejecutar("editar")
        anunciar.assert_called_once_with("Sin elementos.")
        self.assertEqual(self.llamadas, [])

    def test_ejecutar_sin_seleccion_anuncia_y_no_llama(self):
        self.pieza.fijar(["a", "b"])
        self.lista.SetSelection(wx.NOT_FOUND)
        with mock.patch.object(lista_acciones, "anunciar") as anunciar:
            self.pieza.ejecutar("editar")
        anunciar.assert_called_once_with("Sin selección")
        self.assertEqual(self.llamadas, [])

    def test_el_menu_tiene_las_etiquetas_en_orden_y_con_su_tecla(self):
        self.pieza.fijar([])
        items = self._menu().GetMenuItems()
        self.assertEqual(
            [item.GetItemLabel() for item in items],
            ["&Editar\tEnter", "&Renombrar\tF2", "&Eliminar\tDel", "&Nuevo"])
        self.assertEqual(
            [item.IsEnabled() for item in items],
            [False, False, False, True])
        self.pieza.fijar(["a"])
        items = self._menu().GetMenuItems()
        self.assertTrue(all(item.IsEnabled() for item in items))

    def test_suprimir_f2_e_intro_hacen_la_accion_de_su_tecla(self):
        casos = (
            (wx.wxEVT_KEY_DOWN, wx.WXK_DELETE, "eliminar"),
            (wx.wxEVT_KEY_DOWN, wx.WXK_F2, "renombrar"),
            (wx.wxEVT_CHAR_HOOK, wx.WXK_RETURN, "editar"),
        )
        for tipo, codigo, esperado in casos:
            with self.subTest(codigo=codigo):
                self.llamadas.clear()
                self.pieza.fijar(["a"])
                self._tecla(tipo, codigo)
                self.assertEqual(self.llamadas, [esperado])

    def test_el_clic_derecho_abre_el_menu(self):
        self.pieza.fijar(["a"])
        with mock.patch.object(self.lista, "PopupMenu") as popup:
            self.lista.ProcessEvent(
                wx.ContextMenuEvent(wx.wxEVT_CONTEXT_MENU))
        popup.assert_called_once()

    def test_la_tecla_y_el_contexto_abren_el_menu_una_sola_vez(self):
        self.pieza.fijar(["a"])
        with mock.patch.object(self.lista, "PopupMenu") as popup:
            self._tecla(wx.wxEVT_KEY_DOWN, wx.WXK_WINDOWS_MENU)
            self.lista.ProcessEvent(
                wx.ContextMenuEvent(wx.wxEVT_CONTEXT_MENU))
        self.assertEqual(popup.call_count, 1)

    def test_con_la_lista_vacia_suprimir_f2_e_intro_anuncian_el_vacio(self):
        self.pieza.fijar([])
        casos = (
            (wx.wxEVT_KEY_DOWN, wx.WXK_DELETE),
            (wx.wxEVT_KEY_DOWN, wx.WXK_F2),
            (wx.wxEVT_CHAR_HOOK, wx.WXK_RETURN),
        )
        for tipo, codigo in casos:
            with self.subTest(codigo=codigo):
                with mock.patch.object(lista_acciones, "anunciar") as anunciar:
                    self._tecla(tipo, codigo)
                anunciar.assert_called_once_with("Sin elementos.")


if __name__ == "__main__":
    unittest.main()
