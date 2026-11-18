# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de la pieza común de listas con acciones."""

import ctypes
import unittest
from unittest import mock

import wx

from tests.ventanas_prueba import app_de_prueba, destruir
from guyrapu.ui import lista_acciones
from guyrapu.ui.lista_ctrl import ListaCtrlEnvuelta


def _accion(clave, tecla=None, necesita_elemento=True, manejador=None,
            motivo=None, opciones=None, varios=False, motivo_indices=None):
    return lista_acciones.Accion(
        clave=clave,
        etiqueta="&" + clave.capitalize(),
        manejador=manejador or (lambda: None),
        tecla=tecla,
        necesita_elemento=necesita_elemento,
        motivo=motivo,
        opciones=opciones,
        varios=varios,
        motivo_indices=motivo_indices)


ACCIONES = (
    _accion("editar", "intro"),
    _accion("renombrar", "f2"),
    _accion("eliminar", "suprimir"),
    _accion("nuevo", necesita_elemento=False),
)


class PruebaPartePura(unittest.TestCase):

    def test_alt_flecha_sin_accion_deja_pasar_el_evento(self):
        pieza = lista_acciones.ListaConAcciones(
            mock.Mock(), ACCIONES, "Sin elementos.")
        for codigo in (wx.WXK_UP, wx.WXK_DOWN):
            with self.subTest(codigo=codigo):
                evento = mock.Mock()
                evento.GetKeyCode.return_value = codigo
                evento.GetModifiers.return_value = wx.MOD_ALT
                pieza._al_tecla(evento)
                evento.Skip.assert_called_once_with()

    def test_una_accion_con_motivo_anuncia_el_motivo_y_no_corre(self):
        llamadas = []
        acciones = (_accion(
            "responder", necesita_elemento=False,
            manejador=lambda: llamadas.append("responder"),
            motivo=lambda: "Sin sesión de YouTube"),)
        pieza = lista_acciones.ListaConAcciones(
            mock.Mock(), acciones, "Sin elementos.")
        with mock.patch.object(lista_acciones, "anunciar") as anunciar:
            self.assertTrue(pieza.ejecutar("responder"))
        anunciar.assert_called_once_with("Sin sesión de YouTube.")
        self.assertEqual(llamadas, [])

    def test_una_accion_con_motivo_vacio_corre_como_siempre(self):
        llamadas = []
        acciones = (_accion(
            "responder", necesita_elemento=False,
            manejador=lambda: llamadas.append("responder"),
            motivo=lambda: ""),)
        pieza = lista_acciones.ListaConAcciones(
            mock.Mock(), acciones, "Sin elementos.")
        with mock.patch.object(lista_acciones, "anunciar") as anunciar:
            self.assertTrue(pieza.ejecutar("responder"))
        anunciar.assert_not_called()
        self.assertEqual(llamadas, ["responder"])


class PruebaListaConVacio(unittest.TestCase):

    def setUp(self):
        self.app = app_de_prueba()
        self.marco = wx.Frame(None)
        self.addCleanup(destruir, self.marco)
        self.lista = wx.ListBox(self.marco)
        self.vacio = lista_acciones.ListaConVacio(
            self.lista, "Sin elementos.")

    def _tecla(self, tipo, codigo):
        evento = wx.KeyEvent(tipo)
        evento.KeyCode = codigo
        self.lista.GetEventHandler().ProcessEvent(evento)

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

    def test_flecha_arriba_en_el_primero_reproduce_orilla(self):
        with mock.patch.object(lista_acciones._snd, "reproducir") as sonar:
            self.vacio.fijar(["a", "b"])
            self.lista.SetSelection(0)
            self._tecla(wx.wxEVT_KEY_DOWN, wx.WXK_UP)
            sonar.assert_called_once_with("orilla")

    def test_flecha_en_la_lista_vacia_tambien_reproduce_orilla(self):
        with mock.patch.object(lista_acciones._snd, "reproducir") as sonar:
            self.vacio.fijar([])
            self._tecla(wx.wxEVT_KEY_DOWN, wx.WXK_DOWN)
            sonar.assert_called_once_with("orilla")

    def test_escribir_una_letra_elige_el_primero_que_empieza(self):
        self.vacio.fijar(["Ana", "Beto", "Bruno"])
        self.lista.SetSelection(0)
        with mock.patch.object(wx, "CallLater"), \
                mock.patch("guyrapu.ui.busqueda_teclado.anunciar"):
            evento = wx.KeyEvent(wx.wxEVT_CHAR)
            evento.SetUnicodeKey(ord("B"))
            self.lista.GetEventHandler().ProcessEvent(evento)
        self.assertEqual(self.lista.GetSelection(), 1)

    def test_fijar_con_vacio_cambia_el_texto_de_esa_carga(self):
        self.vacio.fijar([], vacio="x")
        self.assertEqual(self.lista.GetString(0), "x")
        self.vacio.fijar([])
        self.assertEqual(self.lista.GetString(0), "Sin elementos.")


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

    def test_intro_con_modificador_no_ejecuta_la_accion_intro(self):
        self.pieza.fijar(["a"])
        for modificar in ("SetControlDown", "SetShiftDown", "SetAltDown"):
            with self.subTest(modificador=modificar):
                self.llamadas.clear()
                evento = wx.KeyEvent(wx.wxEVT_KEY_DOWN)
                evento.KeyCode = wx.WXK_RETURN
                getattr(evento, modificar)(True)
                self.lista.GetEventHandler().ProcessEvent(evento)
                self.assertEqual(self.llamadas, [])

    def test_ctrl_d_ejecuta_la_accion_de_tecla_ctrl_d(self):
        llamadas = []
        acciones = (lista_acciones.Accion(
            "duplicar", "&Duplicar", lambda: llamadas.append("duplicar"),
            tecla="ctrl+d"),)
        pieza = lista_acciones.ListaConAcciones(
            self.lista, acciones, "Sin elementos.")
        pieza.fijar(["a"])
        evento = mock.Mock()
        evento.GetKeyCode.return_value = ord("D")
        evento.GetModifiers.return_value = wx.MOD_CONTROL
        pieza._al_tecla(evento)
        self.assertEqual(llamadas, ["duplicar"])

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


class PruebaAccionesConOpciones(unittest.TestCase):

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

    def _menu(self, pieza):
        menu = pieza._construir_menu()
        self.addCleanup(menu.Destroy)
        return menu

    def _item(self, menu, etiqueta):
        return next(item for item in menu.GetMenuItems()
                    if item.GetItemLabelText() == etiqueta)

    def _opciones(self, menu, etiqueta):
        return self._item(menu, etiqueta).GetSubMenu()

    def test_p2_las_opciones_se_piden_en_cada_apertura(self):
        veces = []

        def opciones():
            veces.append(len(veces) + 1)
            return [(f"&Lista {len(veces)}", lambda: None)]

        pieza = self._pieza((_accion("agregar", opciones=opciones),))
        self.assertEqual(veces, [])
        primero = self._opciones(self._menu(pieza), "Agregar")
        self.assertEqual(
            [item.GetItemLabel() for item in primero.GetMenuItems()],
            ["&Lista 1"])
        segundo = self._opciones(self._menu(pieza), "Agregar")
        self.assertEqual(
            [item.GetItemLabel() for item in segundo.GetMenuItems()],
            ["&Lista 2"])
        self.assertEqual(veces, [1, 2])


class PruebaEnvoltorioListaCtrl(unittest.TestCase):

    def setUp(self):
        self.app = app_de_prueba()
        self.marco = wx.Frame(None)
        self.addCleanup(destruir, self.marco)
        self.control = wx.ListCtrl(
            self.marco, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        self.control.InsertColumn(0, "Nombre", width=150)
        self.control.InsertColumn(1, "Familia", width=150)
        self.lista = ListaCtrlEnvuelta(self.control)

    def test_append_acepta_texto_y_tuplas_y_los_cuenta(self):
        self.lista.Append("Solo")
        self.lista.Append(("Con", "Dos"))
        self.assertEqual(self.lista.GetCount(), 2)
        self.assertEqual(self.control.GetItemText(0, 0), "Solo")
        self.assertEqual(self.control.GetItemText(0, 1), "")
        self.assertEqual(self.control.GetItemText(1, 0), "Con")
        self.assertEqual(self.control.GetItemText(1, 1), "Dos")

    def test_sin_fila_elegida_da_not_found_y_set_selection_enfoca(self):
        self.lista.Append("Solo")
        self.assertEqual(self.lista.GetSelection(), wx.NOT_FOUND)
        self.lista.SetSelection(0)
        self.assertEqual(self.lista.GetSelection(), 0)
        self.assertEqual(self.control.GetFocusedItem(), 0)
        self.lista.Clear()
        self.assertEqual(self.lista.GetCount(), 0)


class PruebaListaConVacioCtrl(unittest.TestCase):

    def setUp(self):
        self.app = app_de_prueba()
        self.marco = wx.Frame(None)
        self.addCleanup(destruir, self.marco)
        self.lista = self._lista_ctrl()
        self.vacio = lista_acciones.ListaConVacio(
            self.lista, "Sin elementos.")

    def _lista_ctrl(self):
        lista = wx.ListCtrl(
            self.marco, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        lista.InsertColumn(0, "Nombre", width=150)
        lista.InsertColumn(1, "Familia", width=150)
        return lista

    def _tecla(self, tipo, codigo):
        evento = wx.KeyEvent(tipo)
        evento.KeyCode = codigo
        self.lista.GetEventHandler().ProcessEvent(evento)

    def test_vacia_deja_la_linea_elegida_y_sin_indice(self):
        self.vacio.fijar([])
        self.assertTrue(self.vacio.vacia())
        self.assertEqual(self.lista.GetItemCount(), 1)
        self.assertEqual(self.lista.GetItemText(0, 0), "Sin elementos.")
        self.assertEqual(self.lista.GetItemText(0, 1), "")
        self.assertEqual(self.lista.GetFirstSelected(), 0)
        self.assertIsNone(self.vacio.indice())

    def test_sin_elemento_con_la_lista_vacia_anuncia_el_texto(self):
        self.vacio.fijar([])
        with mock.patch.object(lista_acciones, "anunciar") as anunciar:
            self.vacio.sin_elemento()
        anunciar.assert_called_once_with("Sin elementos.")

    def test_con_elementos_sin_elegir_anuncia_sin_seleccion(self):
        self.vacio.fijar(["a", "b"])
        self.assertFalse(self.vacio.vacia())
        self.lista.Select(0, False)
        with mock.patch.object(lista_acciones, "anunciar") as anunciar:
            self.vacio.sin_elemento()
        anunciar.assert_called_once_with("Sin selección")

    def test_flecha_arriba_en_el_primero_reproduce_orilla(self):
        with mock.patch.object(lista_acciones._snd, "reproducir") as sonar:
            self.vacio.fijar(["a", "b"])
            self.lista.Select(0)
            self._tecla(wx.wxEVT_KEY_DOWN, wx.WXK_UP)
            sonar.assert_called_once_with("orilla")

    def test_flecha_en_la_lista_vacia_tambien_reproduce_orilla(self):
        with mock.patch.object(lista_acciones._snd, "reproducir") as sonar:
            self.vacio.fijar([])
            self._tecla(wx.wxEVT_KEY_DOWN, wx.WXK_DOWN)
            sonar.assert_called_once_with("orilla")

    def test_escribir_una_letra_elige_el_primero_que_empieza(self):
        self.vacio.fijar([("Ana", "A"), ("Beto", "B"), ("Bruno", "C")])
        self.lista.Select(0)
        with mock.patch.object(wx, "CallLater"), \
                mock.patch("guyrapu.ui.busqueda_teclado.anunciar"):
            evento = wx.KeyEvent(wx.wxEVT_CHAR)
            evento.SetUnicodeKey(ord("B"))
            self.lista.GetEventHandler().ProcessEvent(evento)
        self.assertEqual(self.lista.GetFirstSelected(), 1)

    def test_busca_por_la_primera_columna(self):
        self.vacio.fijar([("Ana", "Zeta"), ("Beto", "Ana")])
        self.lista.Select(0)
        with mock.patch.object(wx, "CallLater"), \
                mock.patch("guyrapu.ui.busqueda_teclado.anunciar") as anunciar:
            evento = wx.KeyEvent(wx.wxEVT_CHAR)
            evento.SetUnicodeKey(ord("B"))
            self.lista.GetEventHandler().ProcessEvent(evento)
        anunciar.assert_any_call("Beto")
        self.assertEqual(self.lista.GetFirstSelected(), 1)

    def test_fijar_acepta_texto_y_tuplas(self):
        self.vacio.fijar(["Solo", ("Con", "Dos")])
        self.assertEqual(self.lista.GetItemText(0, 0), "Solo")
        self.assertEqual(self.lista.GetItemText(0, 1), "")
        self.assertEqual(self.lista.GetItemText(1, 0), "Con")
        self.assertEqual(self.lista.GetItemText(1, 1), "Dos")

    def test_fijar_con_vacio_cambia_el_texto_de_esa_carga(self):
        self.vacio.fijar([], vacio="x")
        self.assertEqual(self.lista.GetItemText(0, 0), "x")
        self.vacio.fijar([])
        self.assertEqual(self.lista.GetItemText(0, 0), "Sin elementos.")


class PruebaConListaCtrl(unittest.TestCase):

    def setUp(self):
        self.app = app_de_prueba()
        self.marco = wx.Frame(None)
        self.addCleanup(destruir, self.marco)
        self.lista = self._lista_ctrl()
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

    def _lista_ctrl(self):
        lista = wx.ListCtrl(
            self.marco, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        lista.InsertColumn(0, "Nombre", width=150)
        lista.InsertColumn(1, "Familia", width=150)
        return lista

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
        self.assertEqual(self.lista.GetItemCount(), 1)
        self.assertEqual(self.lista.GetItemText(0, 0), "Sin elementos.")
        self.assertEqual(self.lista.GetFirstSelected(), 0)
        self.assertIsNone(self.pieza.indice())

    def test_ejecutar_con_la_lista_vacia_anuncia_el_vacio_y_no_llama(self):
        self.pieza.fijar([])
        with mock.patch.object(lista_acciones, "anunciar") as anunciar:
            self.pieza.ejecutar("editar")
        anunciar.assert_called_once_with("Sin elementos.")
        self.assertEqual(self.llamadas, [])

    def test_ejecutar_sin_seleccion_anuncia_y_no_llama(self):
        self.pieza.fijar(["a", "b"])
        self.lista.Select(0, False)
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

    def test_intro_corre_la_accion_una_sola_vez(self):
        self.pieza.fijar(["a"])
        self._tecla(wx.wxEVT_CHAR_HOOK, wx.WXK_RETURN)
        self.assertEqual(self.llamadas, ["editar"])

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

    def test_el_doble_clic_corre_la_accion(self):
        self.pieza.fijar(["a"])
        evento = wx.ListEvent(
            wx.wxEVT_LIST_ITEM_ACTIVATED, self.lista.GetId())
        self.lista.ProcessEvent(evento)
        self.assertEqual(self.llamadas, ["editar"])

    def test_el_doble_clic_de_listbox_no_corre_la_accion(self):
        self.pieza.fijar(["a"])
        evento = wx.ListEvent(wx.wxEVT_LISTBOX_DCLICK, self.lista.GetId())
        self.lista.ProcessEvent(evento)
        self.assertEqual(self.llamadas, [])

    def test_fijar_deja_la_fila_elegida_y_enfocada(self):
        self.pieza.fijar(["a", "b"], elegido=1)
        self.assertEqual(self.lista.GetFirstSelected(), 1)
        self.assertEqual(self.lista.GetFocusedItem(), 1)


class PruebaSeleccionMultiple(unittest.TestCase):

    MOTIVO = "Elige un solo elemento para esta acción"

    def setUp(self):
        self.app = app_de_prueba()
        self.marco = wx.Frame(None)
        self.addCleanup(destruir, self.marco)
        self.lista = wx.ListCtrl(self.marco, style=wx.LC_REPORT)
        self.lista.InsertColumn(0, "Nombre", width=150)
        self.lista.InsertColumn(1, "Familia", width=150)

    def _pieza(self, acciones):
        pieza = lista_acciones.ListaConAcciones(
            self.lista, acciones, "Sin elementos.")
        pieza.fijar(["a", "b", "c", "d", "e"])
        return pieza

    def _tecla(self, tipo, codigo):
        evento = wx.KeyEvent(tipo)
        evento.KeyCode = codigo
        self.lista.GetEventHandler().ProcessEvent(evento)

    def test_p1_indices_da_todas_las_elegidas_en_orden(self):
        pieza = self._pieza((_accion("editar"),))
        for indice in (0, 2, 4):
            self.lista.Select(indice)
        self.assertEqual(pieza.indices(), [0, 2, 4])
        for indice in (0, 2, 4):
            self.lista.Select(indice, False)
        self.assertEqual(pieza.indices(), [])
        self.lista.Select(3)
        self.assertEqual(pieza.indices(), [3])
        pieza.fijar([])
        self.assertEqual(pieza.indices(), [])

    def test_p1_lista_con_vacio_da_los_indices_elegidos(self):
        vacio = lista_acciones.ListaConVacio(self.lista, "Sin elementos.")
        vacio.fijar(["a", "b", "c"])
        self.lista.Select(0, False)
        self.lista.Select(1)
        self.assertEqual(vacio.indices(), [1])
        vacio.fijar([])
        self.assertEqual(vacio.indices(), [])

    def test_p2_con_dos_elegidas_la_de_una_anuncia_y_no_corre(self):
        llamadas = []
        pieza = self._pieza((_accion(
            "editar", manejador=lambda: llamadas.append("editar")),))
        self.lista.Select(1)
        with mock.patch.object(lista_acciones, "anunciar") as anunciar:
            self.assertTrue(pieza.ejecutar("editar"))
        anunciar.assert_called_once_with(self.MOTIVO + ".")
        self.assertEqual(llamadas, [])

    def test_p2_con_varias_la_accion_de_varias_corre(self):
        llamadas = []
        pieza = self._pieza((_accion(
            "unir", varios=True,
            manejador=lambda: llamadas.append("unir")),))
        self.lista.Select(1)
        with mock.patch.object(lista_acciones, "anunciar") as anunciar:
            self.assertTrue(pieza.ejecutar("unir"))
        anunciar.assert_not_called()
        self.assertEqual(llamadas, ["unir"])

    def test_p2_en_el_menu_la_de_una_queda_apagada_con_el_motivo(self):
        pieza = self._pieza((_accion("editar"),))
        self.lista.Select(1)
        menu = pieza._construir_menu()
        self.addCleanup(menu.Destroy)
        item = menu.GetMenuItems()[0]
        self.assertFalse(item.IsEnabled())
        self.assertEqual(
            item.GetItemLabel(),
            "&Editar (elige un solo elemento para esta acción)")

    def test_p3_la_tecla_anuncia_el_motivo_propio_y_no_corre(self):
        llamadas = []
        self._pieza((_accion(
            "descargar", tecla="suprimir", varios=True,
            motivo_indices=lambda indices: "Algún elegido no se puede bajar",
            manejador=lambda: llamadas.append("descargar")),))
        self.lista.Select(1)
        self.lista.Select(2)
        with mock.patch.object(lista_acciones, "anunciar") as anunciar:
            self._tecla(wx.wxEVT_KEY_DOWN, wx.WXK_DELETE)
        anunciar.assert_called_once_with(
            "Algún elegido no se puede bajar.")
        self.assertEqual(llamadas, [])

    def test_p3_el_menu_apaga_con_el_motivo_propio(self):
        pieza = self._pieza((_accion(
            "descargar", varios=True,
            motivo_indices=lambda indices: "Algún elegido no se puede bajar"),))
        self.lista.Select(1)
        self.lista.Select(2)
        menu = pieza._construir_menu()
        self.addCleanup(menu.Destroy)
        item = menu.GetMenuItems()[0]
        self.assertFalse(item.IsEnabled())
        self.assertEqual(
            item.GetItemLabel(),
            "&Descargar (algún elegido no se puede bajar)")


class PruebaCasillasConPieza(unittest.TestCase):

    def setUp(self):
        self.app = app_de_prueba()
        self.marco = wx.Frame(None)
        self.addCleanup(destruir, self.marco)
        self.lista = wx.ListCtrl(
            self.marco, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        self.lista.InsertColumn(0, "Nombre", width=150)
        self.lista.InsertColumn(1, "Familia", width=150)
        self.lista.EnableCheckBoxes(True)
        self.pieza = lista_acciones.ListaConAcciones(
            self.lista, (_accion("oir"),), "Sin elementos.")

    def _espacio(self):
        enviar = ctypes.windll.user32.SendMessageW
        enviar.argtypes = (ctypes.c_void_p, ctypes.c_uint, ctypes.c_size_t,
                           ctypes.c_ssize_t)
        enviar.restype = ctypes.c_ssize_t
        for mensaje in (0x0100, 0x0101):   # WM_KEYDOWN, WM_KEYUP
            enviar(self.lista.GetHandle(), mensaje, 0x20, 0)   # VK_SPACE
        wx.Yield()

    def test_espacio_con_la_busqueda_vacia_alterna_la_casilla(self):
        self.pieza.fijar([("Uno", "A"), ("Dos", "B")])
        self.lista.CheckItem(0, True)
        self.assertTrue(self.lista.IsItemChecked(0))
        self._espacio()
        self.assertFalse(self.lista.IsItemChecked(0))
        self._espacio()
        self.assertTrue(self.lista.IsItemChecked(0))


class _ListBoxEspia(wx.ListBox):
    """ListBox real que cuenta lo que la pieza le hace."""

    def __init__(self, padre):
        super().__init__(padre)
        self.insertadas = []
        self.borradas = []
        self.reescritas = []
        self.selecciones = []

    def Insert(self, texto, indice):
        self.insertadas.append((indice, texto))
        return super().Insert(texto, indice)

    def Delete(self, indice):
        self.borradas.append(indice)
        return super().Delete(indice)

    def SetString(self, indice, texto):
        self.reescritas.append((indice, texto))
        return super().SetString(indice, texto)

    def SetSelection(self, indice):
        self.selecciones.append(indice)
        return super().SetSelection(indice)

    def limpiar_cuentas(self):
        self.insertadas.clear()
        self.borradas.clear()
        self.reescritas.clear()
        self.selecciones.clear()


class _ListCtrlEspia(wx.ListCtrl):
    """ListCtrl real que cuenta lo que la pieza le hace."""

    def __init__(self, padre):
        super().__init__(padre, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        self.insertadas = []
        self.borradas = []
        self.celdas = []
        self.selecciones = []

    def InsertItem(self, indice, texto):
        self.insertadas.append((indice, texto))
        return super().InsertItem(indice, texto)

    def DeleteItem(self, indice):
        self.borradas.append(indice)
        return super().DeleteItem(indice)

    def SetItem(self, indice, columna, texto):
        self.celdas.append((indice, columna, texto))
        return super().SetItem(indice, columna, texto)

    def Select(self, indice, *args):
        self.selecciones.append(indice)
        return super().Select(indice, *args)

    def limpiar_cuentas(self):
        self.insertadas.clear()
        self.borradas.clear()
        self.celdas.clear()
        self.selecciones.clear()


class PruebaPonerAlDiaListBox(unittest.TestCase):

    def setUp(self):
        self.app = app_de_prueba()
        self.marco = wx.Frame(None)
        self.addCleanup(destruir, self.marco)
        self.lista = _ListBoxEspia(self.marco)
        self.vacio = lista_acciones.ListaConVacio(self.lista, "Sin elementos.")
        self.vacio.poner_al_dia(["a", "b", "c"], ["a", "b", "c"])
        self.lista.limpiar_cuentas()

    def _textos(self):
        return [self.lista.GetString(i) for i in range(self.lista.GetCount())]

    def test_de_a_b_c_a_a_c_d_conserva_la_a(self):
        self.vacio.poner_al_dia(["a", "c", "d"], ["a", "c", "d"])
        self.assertEqual(self._textos(), ["a", "c", "d"])
        self.assertEqual(self.lista.borradas, [1])
        self.assertEqual(self.lista.insertadas, [(2, "d")])
        self.assertEqual(self.lista.reescritas, [])

    def test_b_elegida_queda_en_su_indice_nuevo(self):
        self.lista.SetSelection(1)
        self.lista.limpiar_cuentas()
        self.vacio.poner_al_dia(["x", "a", "b", "c"], ["x", "a", "b", "c"])
        self.assertEqual(self.lista.GetSelection(), 2)
        self.assertEqual(self.lista.selecciones, [2])

    def test_b_elegida_sin_movimiento_no_llama_a_set_selection(self):
        self.lista.SetSelection(1)
        self.lista.limpiar_cuentas()
        self.vacio.poner_al_dia(["a", "b", "c"], ["a", "b", "c"])
        self.assertEqual(self.lista.selecciones, [])
        self.assertEqual(self.lista.GetSelection(), 1)

    def test_si_la_elegida_desaparece_se_elege_el_mismo_indice_o_el_ultimo(self):
        self.lista.SetSelection(2)
        self.lista.limpiar_cuentas()
        self.vacio.poner_al_dia(["a", "b", "d"], ["a", "b", "d"])
        self.assertEqual(self.lista.GetSelection(), 2)
        self.vacio.poner_al_dia(["a"], ["a"])
        self.assertEqual(self.lista.GetSelection(), 0)

    def test_con_una_clave_elegida_se_elege_esa_fila(self):
        self.vacio.poner_al_dia(["a", "b", "c"], ["a", "b", "c"],
                                elegida="c")
        self.assertEqual(self.lista.GetSelection(), 2)

    def test_de_filas_a_ninguna_deja_la_linea_vacia(self):
        self.vacio.poner_al_dia([], [])
        self.assertEqual(self._textos(), ["Sin elementos."])
        self.assertIsNone(self.vacio.indice())
        self.assertTrue(self.vacio.vacia())

    def test_de_la_linea_vacia_a_filas_la_reemplaza(self):
        self.vacio.poner_al_dia([], [])
        self.lista.limpiar_cuentas()
        self.vacio.poner_al_dia(["a"], ["a"])
        self.assertEqual(self._textos(), ["a"])
        self.assertEqual(self.lista.insertadas, [(0, "a")])

    def test_claves_repetidas_se_muestran_todas(self):
        self.vacio.poner_al_dia(
            ["a", "b", "a", "c", "a"], ["a", "b", "a", "c", "a"])
        self.assertEqual(self._textos(), ["a", "b", "a", "c", "a"])

    def test_quitar_una_repetida_y_agregar_otra_en_medio(self):
        self.vacio.poner_al_dia(
            ["a", "b", "a", "c", "a"], ["a", "b", "a", "c", "a"])
        self.vacio.poner_al_dia(
            ["a", "b", "x", "c", "a"], ["a", "b", "x", "c", "a"])
        self.assertEqual(self._textos(), ["a", "b", "x", "c", "a"])

    def test_la_segunda_a_elegida_sigue_en_la_segunda_a(self):
        self.vacio.poner_al_dia(
            ["a", "b", "a", "c", "a"], ["a", "b", "a", "c", "a"])
        self.lista.SetSelection(2)
        self.vacio.poner_al_dia(
            ["a", "b", "a", "c", "a"], ["a", "b", "a", "c", "a"])
        self.assertEqual(self.lista.GetSelection(), 2)

    def test_elegida_con_la_misma_clave_conserva_la_aparicion(self):
        self.vacio.poner_al_dia(
            ["a", "b", "a", "c", "a"], ["a", "b", "a", "c", "a"])
        self.lista.SetSelection(2)
        self.vacio.poner_al_dia(
            ["a", "b", "a", "c", "a"], ["a", "b", "a", "c", "a"],
            elegida="a")
        self.assertEqual(self.lista.GetSelection(), 2)

    def test_elegida_con_otra_clave_va_a_la_primera_aparicion(self):
        self.vacio.poner_al_dia(
            ["a", "b", "a", "c", "a"], ["a", "b", "a", "c", "a"])
        self.lista.SetSelection(2)
        self.vacio.poner_al_dia(
            ["a", "b", "a", "c", "a"], ["a", "b", "a", "c", "a"],
            elegida="b")
        self.assertEqual(self.lista.GetSelection(), 1)


class PruebaPonerAlDiaListCtrl(unittest.TestCase):

    def setUp(self):
        self.app = app_de_prueba()
        self.marco = wx.Frame(None)
        self.addCleanup(destruir, self.marco)
        self.control = _ListCtrlEspia(self.marco)
        self.control.InsertColumn(0, "Clave", width=100)
        self.control.InsertColumn(1, "Valor", width=100)
        self.lista = ListaCtrlEnvuelta(self.control)
        self.vacio = lista_acciones.ListaConVacio(
            self.lista, "Sin elementos.")
        self.vacio.poner_al_dia(
            ["a", "b", "c"], [("a", "1"), ("b", "2"), ("c", "3")])
        self.control.limpiar_cuentas()

    def _textos(self):
        return [self.control.GetItemText(i, 0)
                for i in range(self.control.GetItemCount())]

    def test_de_a_b_c_a_a_c_d_conserva_la_a(self):
        self.vacio.poner_al_dia(
            ["a", "c", "d"], [("a", "1"), ("c", "3"), ("d", "4")])
        self.assertEqual(self._textos(), ["a", "c", "d"])
        self.assertEqual(self.control.borradas, [1])
        self.assertEqual(self.control.insertadas, [(2, "d")])
        self.assertEqual(self.control.celdas, [(2, 1, "4")])

    def test_cambiar_solo_la_segunda_celda_reescribe_solo_esa_celda(self):
        self.vacio.poner_al_dia(["a", "b"], [("a", "1"), ("b", "2")])
        self.control.limpiar_cuentas()
        self.vacio.poner_al_dia(["a", "b"], [("a", "1"), ("b", "X")])
        self.assertEqual(self.control.celdas, [(1, 1, "X")])

    def test_b_elegida_queda_en_su_indice_nuevo(self):
        self.lista.SetSelection(1)
        self.control.limpiar_cuentas()
        self.vacio.poner_al_dia(
            ["x", "a", "b", "c"],
            [("x", "0"), ("a", "1"), ("b", "2"), ("c", "3")])
        self.assertEqual(self.control.GetFirstSelected(), 2)
        self.assertEqual(self.control.selecciones, [2])

    def test_b_elegida_sin_movimiento_no_llama_a_set_selection(self):
        self.lista.SetSelection(1)
        self.control.limpiar_cuentas()
        self.vacio.poner_al_dia(
            ["a", "b", "c"], [("a", "1"), ("b", "2"), ("c", "3")])
        self.assertEqual(self.control.selecciones, [])
        self.assertEqual(self.control.GetFirstSelected(), 1)

    def test_de_filas_a_ninguna_deja_la_linea_vacia(self):
        self.vacio.poner_al_dia([], [])
        self.assertEqual(self._textos(), ["Sin elementos."])
        self.assertIsNone(self.vacio.indice())
        self.assertTrue(self.vacio.vacia())

    def test_de_la_linea_vacia_a_filas_la_reemplaza(self):
        self.vacio.poner_al_dia([], [])
        self.control.limpiar_cuentas()
        self.vacio.poner_al_dia(["a"], [("a", "1")])
        self.assertEqual(self._textos(), ["a"])
        self.assertEqual(self.control.insertadas, [(0, "a")])


if __name__ == "__main__":
    unittest.main()
