# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas del envoltorio de `wx.ListCtrl` de la pieza de listas."""

import unittest

import wx

from tests.test_musica_ventana import ControlFalso, _biblioteca_de
from tests.ventanas_prueba import app_de_prueba, destruir
from guyrapu.ui.lista_ctrl import ListaCtrlComoListBox, ListaCtrlEnvuelta
from guyrapu.ui.musica_ventana import VentanaMusica


class PruebaSelecciones(unittest.TestCase):

    def setUp(self):
        self.app = app_de_prueba()
        self.marco = wx.Frame(None)
        self.addCleanup(destruir, self.marco)
        self.control = wx.ListCtrl(self.marco, style=wx.LC_REPORT)
        self.control.InsertColumn(0, "Nombre", width=150)
        self.lista = ListaCtrlEnvuelta(self.control)
        for texto in ("a", "b", "c", "d", "e"):
            self.lista.Append(texto)

    def test_p4_get_selections_da_todas_las_elegidas_en_orden(self):
        self.assertEqual(self.lista.GetSelections(), [])
        for indice in (4, 0, 2):
            self.control.Select(indice)
        self.assertEqual(self.lista.GetSelections(), [0, 2, 4])
        self.control.Select(2, False)
        self.assertEqual(self.lista.GetSelections(), [0, 4])

    def test_p4_una_sola_elegida_y_ninguna(self):
        self.control.Select(3)
        self.assertEqual(self.lista.GetSelections(), [3])
        self.control.Select(3, False)
        self.assertEqual(self.lista.GetSelections(), [])


class PruebaListaComoListBox(unittest.TestCase):

    def setUp(self):
        self.app = app_de_prueba()
        self.marco = wx.Frame(None, size=(320, 240))
        self.addCleanup(destruir, self.marco)
        self.lista = ListaCtrlComoListBox(self.marco, name="Canciones")
        self.caja = wx.ListBox(self.marco)

    def test_p1_es_un_listctrl_de_informe_de_una_columna_sin_encabezado(self):
        estilo = self.lista.GetWindowStyleFlag()
        self.assertIsInstance(self.lista, wx.ListCtrl)
        self.assertEqual(estilo & wx.LC_REPORT, wx.LC_REPORT)
        self.assertEqual(estilo & wx.LC_NO_HEADER, wx.LC_NO_HEADER)
        self.assertEqual(self.lista.GetColumnCount(), 1)

    def test_p1_agregar_insertar_borrar_y_limpiar_dan_lo_mismo_que_la_caja(
            self):
        for lista in (self.lista, self.caja):
            lista.Append("a")
            lista.Append("c")
            lista.Insert("b", 1)
        self.assertEqual(self.lista.GetCount(), self.caja.GetCount())
        self.assertEqual(self.lista.GetStrings(), self.caja.GetStrings())
        for indice in range(self.caja.GetCount()):
            self.assertEqual(self.lista.GetString(indice),
                             self.caja.GetString(indice))
        self.lista.Delete(0)
        self.caja.Delete(0)
        self.assertEqual(self.lista.GetStrings(), self.caja.GetStrings())
        self.lista.Clear()
        self.caja.Clear()
        self.assertEqual(self.lista.GetCount(), self.caja.GetCount())
        self.assertEqual(self.lista.GetStrings(), self.caja.GetStrings())

    def test_p1_set_reemplaza_los_textos_y_no_elige_ninguna(self):
        for lista in (self.lista, self.caja):
            lista.Append("vieja")
            lista.Append("otra")
            lista.Set(["a", "b", "c"])
        self.assertEqual(self.lista.GetStrings(), self.caja.GetStrings())
        self.assertEqual(self.lista.GetSelection(), self.caja.GetSelection())
        self.assertEqual(self.lista.GetSelections(), [])

    def test_p1_set_string_cambia_ese_texto_como_la_caja(self):
        for lista in (self.lista, self.caja):
            lista.Append("a")
            lista.Append("b")
        self.lista.SetString(1, "B")
        self.caja.SetString(1, "B")
        self.assertEqual(self.lista.GetStrings(), self.caja.GetStrings())

    def test_p1_seleccionar_deja_esa_fila_y_sin_indice_ninguna(self):
        for lista in (self.lista, self.caja):
            lista.Append("a")
            lista.Append("b")
            lista.SetSelection(1)
        self.assertEqual(self.lista.GetSelection(), self.caja.GetSelection())
        self.assertEqual(self.lista.GetSelections(), [1])
        self.lista.SetSelection(wx.NOT_FOUND)
        self.caja.SetSelection(wx.NOT_FOUND)
        self.assertEqual(self.lista.GetSelection(), self.caja.GetSelection())
        self.assertEqual(self.lista.GetSelections(), [])

    def test_p2_de_fabrica_deja_una_sola_fila(self):
        self.assertTrue(self.lista.GetWindowStyleFlag() & wx.LC_SINGLE_SEL)

    def test_p2_con_varias_deja_elegir_filas_sueltas(self):
        lista = ListaCtrlComoListBox(self.marco, varias=True)
        self.assertFalse(lista.GetWindowStyleFlag() & wx.LC_SINGLE_SEL)
        for texto in ("a", "b", "c"):
            lista.Append(texto)
        lista.Select(0)
        lista.Select(2)
        self.assertEqual(lista.GetSelections(), [0, 2])
        self.assertEqual(lista.GetSelection(), 0)

    def test_p1_set_selection_en_varias_deja_solo_esa_fila(self):
        lista = ListaCtrlComoListBox(self.marco, varias=True)
        for texto in ("a", "b", "c"):
            lista.Append(texto)
        lista.Select(0)
        lista.Select(2)
        lista.SetSelection(1)
        self.assertEqual(lista.GetSelections(), [1])
        self.assertEqual(lista.GetSelection(), 1)
        lista.SetSelection(wx.NOT_FOUND)
        self.assertEqual(lista.GetSelections(), [])

    def test_p1_la_columna_ocupa_el_ancho_al_cambiar_de_tamano(self):
        self.lista.SetSize((200, 120))
        self.lista.SendSizeEvent()
        self.assertEqual(self.lista.GetColumnWidth(0),
                         self.lista.GetClientSize().width)
        self.lista.SetSize((280, 120))
        self.lista.SendSizeEvent()
        self.assertEqual(self.lista.GetColumnWidth(0),
                         self.lista.GetClientSize().width)


class PruebaEnLaVentanaDeMusica(unittest.TestCase):

    def setUp(self):
        self.app = app_de_prueba()

    def test_p3_canciones_y_cola_usan_la_clase_y_colecciones_sigue_siendo_caja(
            self):
        ventana = VentanaMusica(
            None, ControlFalso(biblioteca=_biblioteca_de("Rock")))
        self.addCleanup(destruir, ventana)
        self.assertIsInstance(ventana.lb_temas, ListaCtrlComoListBox)
        self.assertIsInstance(ventana.lb_cola, ListaCtrlComoListBox)
        self.assertIsInstance(ventana.lb_colecciones, wx.ListBox)


if __name__ == "__main__":
    unittest.main()
