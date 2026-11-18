# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas del armado del menú contextual de una lista con acciones."""

import unittest
from unittest import mock

import wx

from tests.ventanas_prueba import app_de_prueba, destruir
from guyrapu.ui import lista_acciones, menu_lista


def _accion(clave, tecla=None, necesita_elemento=True, manejador=None,
            motivo=None, opciones=None):
    return lista_acciones.Accion(
        clave=clave,
        etiqueta="&" + clave.capitalize(),
        manejador=manejador or (lambda: None),
        tecla=tecla,
        necesita_elemento=necesita_elemento,
        motivo=motivo,
        opciones=opciones)


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


class PruebaConstruirMenu(unittest.TestCase):

    def setUp(self):
        self.app = app_de_prueba()

    def _menu(self, acciones, estados):
        menu = menu_lista.construir_menu(acciones, estados, lambda clave: None)
        self.addCleanup(menu.Destroy)
        return menu

    def test_p1_las_opciones_salen_en_submenu_y_ejecutan_su_funcion(self):
        llamadas = []
        acciones = (_accion(
            "agregar",
            opciones=lambda: [
                ("&Una", lambda: llamadas.append("una")),
                ("&Otra", lambda: llamadas.append("otra"))]),)
        submenu = self._menu(
            acciones, {"agregar": True}).GetMenuItems()[0].GetSubMenu()
        self.assertIsNotNone(submenu)
        items = submenu.GetMenuItems()
        self.assertEqual(
            [item.GetItemLabel() for item in items], ["&Una", "&Otra"])
        for item in items:
            submenu.ProcessEvent(wx.CommandEvent(
                wx.EVT_MENU.typeId, item.GetId()))
        self.assertEqual(llamadas, ["una", "otra"])

    def test_p3_sin_elemento_la_accion_con_opciones_queda_apagada(self):
        item = self._menu(
            (_accion("agregar", opciones=lambda: []),),
            {"agregar": False}).GetMenuItems()[0]
        self.assertIsNone(item.GetSubMenu())
        self.assertFalse(item.IsEnabled())

    def test_p3_con_motivo_lleva_el_motivo_y_no_hay_submenu(self):
        acciones = (_accion(
            "agregar", opciones=lambda: [],
            motivo=lambda: "Sin sesión de YouTube"),)
        item = self._menu(acciones, {"agregar": True}).GetMenuItems()[0]
        self.assertIsNone(item.GetSubMenu())
        self.assertEqual(
            item.GetItemLabel(), "&Agregar (sin sesión de YouTube)")


class PruebaEjecutarConOpciones(unittest.TestCase):

    def setUp(self):
        self.app = app_de_prueba()
        self.marco = wx.Frame(None)
        self.addCleanup(destruir, self.marco)
        self.lista = wx.ListBox(self.marco)

    def _pieza(self, acciones):
        pieza = lista_acciones.ListaConAcciones(
            self.lista, acciones, "Sin elementos.")
        pieza.fijar(["a"])
        return pieza

    def test_p4_ejecutar_abre_un_menu_de_un_nivel_con_las_opciones(self):
        llamadas = []
        acciones = (_accion(
            "agregar",
            opciones=lambda: [("&Nueva lista…",
                               lambda: llamadas.append("nueva"))]),)
        pieza = self._pieza(acciones)
        etiquetas = []

        def popup(menu):
            items = menu.GetMenuItems()
            etiquetas.extend(item.GetItemLabel() for item in items)
            menu.ProcessEvent(wx.CommandEvent(
                wx.EVT_MENU.typeId, items[0].GetId()))

        with mock.patch.object(
                self.lista, "PopupMenu", side_effect=popup) as mostrar:
            self.assertTrue(pieza.ejecutar("agregar"))
        mostrar.assert_called_once()
        self.assertEqual(etiquetas, ["&Nueva lista…"])
        self.assertEqual(llamadas, ["nueva"])

    def test_p4_sin_fila_anuncia_el_vacio_y_no_abre_el_menu(self):
        acciones = (_accion("agregar", opciones=lambda: []),)
        pieza = lista_acciones.ListaConAcciones(
            self.lista, acciones, "Sin elementos.")
        pieza.fijar([])
        with mock.patch.object(self.lista, "PopupMenu") as mostrar, \
                mock.patch.object(lista_acciones, "anunciar") as anunciar:
            self.assertTrue(pieza.ejecutar("agregar"))
        anunciar.assert_called_once_with("Sin elementos.")
        mostrar.assert_not_called()

    def test_p4_con_motivo_lo_anuncia_y_no_abre_el_menu(self):
        acciones = (_accion(
            "agregar", opciones=lambda: [],
            motivo=lambda: "Sin sesión de YouTube"),)
        pieza = self._pieza(acciones)
        with mock.patch.object(self.lista, "PopupMenu") as mostrar, \
                mock.patch.object(lista_acciones, "anunciar") as anunciar:
            self.assertTrue(pieza.ejecutar("agregar"))
        anunciar.assert_called_once_with("Sin sesión de YouTube.")
        mostrar.assert_not_called()


if __name__ == "__main__":
    unittest.main()
