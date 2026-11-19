# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas wx del editor de listas: casillas, teclas, foco y orden de Tab.

Abre una ventana.
"""

import unittest
from unittest import mock

from guyrapu.core import idioma
from guyrapu.music.modelo import Tema
from guyrapu.ui import lista_acciones, musica_menus
from tests.ventanas_prueba import app_de_prueba, destruir

try:
    import wx
    from guyrapu.ui import musica_editor_lista
    _HAY_WX = True
except Exception:
    wx = None
    musica_editor_lista = None
    _HAY_WX = False


class Evento:
    """Doble mínimo de un evento de teclado de wx."""

    def __init__(self, keycode, mods=0):
        self._keycode = keycode
        self._mods = mods
        self.skipped = False

    def GetKeyCode(self):
        return self._keycode

    def GetModifiers(self):
        return self._mods

    def Skip(self):
        self.skipped = True


A = Tema("C:/Musica/a.mp3", "A")
B = Tema("C:/Musica/b.mp3", "B")
C = Tema("C:/Musica/c.mp3", "C")
VACIA = ("La lista no tiene canciones. Marca las casillas de Todas las "
         "canciones para agregarlas.")


@unittest.skipUnless(_HAY_WX, "wxPython no está instalado")
class TestEditorTeclas(unittest.TestCase):

    def setUp(self):
        self.app = app_de_prueba()
        self.dialogo = None
        self.anuncios = []
        self._parche = mock.patch.object(
            musica_editor_lista, "anunciar",
            lambda texto: self.anuncios.append(texto))
        self._parche.start()

    def tearDown(self):
        self._parche.stop()
        if self.dialogo is not None:
            destruir(self.dialogo)

    def _abrir(self, nombre="Lista", carpeta=(), lista=(), reproducir=None):
        self.dialogo = musica_editor_lista.DialogoEditorLista(
            None, nombre, tuple(carpeta), tuple(lista), reproducir=reproducir)
        wx.Yield()
        return self.dialogo

    def _marcar(self, indice, marcada):
        lista = self.dialogo.lb_todas
        lista.CheckItem(indice, marcada)
        tipo = (wx.wxEVT_LIST_ITEM_CHECKED if marcada
                else wx.wxEVT_LIST_ITEM_UNCHECKED)
        evento = wx.ListEvent(tipo, lista.GetId())
        evento.SetIndex(indice)
        evento.SetEventObject(lista)
        lista.GetEventHandler().ProcessEvent(evento)

    def _filas(self, lista):
        return [lista.GetItemText(indice)
                for indice in range(lista.GetItemCount())]

    def _enfocar(self, lista, indice):
        lista.SetFocus()
        lista.Focus(indice)
        lista.Select(indice)
        wx.Yield()

    def _pulsar(self, codigo, alt=False, shift=False, tipo=None):
        evento = wx.KeyEvent(tipo or wx.wxEVT_KEY_DOWN)
        evento.KeyCode = codigo
        if alt:
            evento.SetAltDown(True)
        if shift:
            evento.SetShiftDown(True)
        self.dialogo.lb_lista.GetEventHandler().ProcessEvent(evento)

    def _pulsar_en_todas(self, codigo, shift=False):
        evento = wx.KeyEvent(wx.wxEVT_KEY_DOWN)
        evento.KeyCode = codigo
        if shift:
            evento.SetShiftDown(True)
        self.dialogo.lb_todas.GetEventHandler().ProcessEvent(evento)

    def _menu_todas(self):
        menu = self.dialogo._todas_acciones._construir_menu()
        self.addCleanup(menu.Destroy)
        return menu

    def _indice_todas(self, titulo):
        return self._filas(self.dialogo.lb_todas).index(titulo)

    def _ejecutar_todas(self, clave):
        self.dialogo._todas_acciones.ejecutar(clave)

    def test_marcar_en_todas_agrega_al_final_y_anuncia(self):
        dialogo = self._abrir(carpeta=(A, B), lista=(A,))
        self.assertEqual(self._filas(dialogo.lb_lista), ["A"])
        self._marcar(1, True)
        self.assertEqual(self._filas(dialogo.lb_lista), ["A", "B"])
        self.assertTrue(dialogo.lb_todas.IsItemChecked(1))
        self.assertEqual(
            self.anuncios,
            ["Agregada a la lista: B. 2 canciones en total"])

    def test_desmarcar_quita_y_anuncia(self):
        dialogo = self._abrir(carpeta=(A, B), lista=(A,))
        self.assertTrue(dialogo.lb_todas.IsItemChecked(0))
        self._marcar(0, False)
        self.assertEqual(self._filas(dialogo.lb_lista), [VACIA])
        self.assertFalse(dialogo.lb_todas.IsItemChecked(0))
        self.assertEqual(
            self.anuncios,
            ["Eliminada de la lista: A. Quedan 0 canciones"])

    def test_supr_quita_desmarca_y_deja_el_foco(self):
        dialogo = self._abrir(carpeta=(A, B, C), lista=(A, B, C))
        self._enfocar(dialogo.lb_lista, 1)
        self._pulsar(wx.WXK_DELETE)
        self.assertEqual(self._filas(dialogo.lb_lista), ["A", "C"])
        self.assertFalse(dialogo.lb_todas.IsItemChecked(1))
        self.assertIs(wx.Window.FindFocus(), dialogo.lb_lista)
        self.assertEqual(dialogo.lb_lista.GetFocusedItem(), 1)
        self.assertEqual(
            self.anuncios,
            ["Eliminada de la lista: B. Quedan 2 canciones"])

    def test_supr_de_la_ultima_deja_el_foco_en_la_que_queda(self):
        dialogo = self._abrir(carpeta=(A, B), lista=(A, B))
        self._enfocar(dialogo.lb_lista, 1)
        self._pulsar(wx.WXK_DELETE)
        self.assertIs(wx.Window.FindFocus(), dialogo.lb_lista)
        self.assertEqual(dialogo.lb_lista.GetFocusedItem(), 0)

    def test_alt_abajo_mueve_enfoca_y_anuncia_la_posicion(self):
        dialogo = self._abrir(carpeta=(A, B, C), lista=(A, B, C))
        self._enfocar(dialogo.lb_lista, 0)
        self._pulsar(wx.WXK_DOWN, alt=True)
        self.assertEqual(self._filas(dialogo.lb_lista), ["B", "A", "C"])
        self.assertIs(wx.Window.FindFocus(), dialogo.lb_lista)
        self.assertEqual(dialogo.lb_lista.GetFocusedItem(), 1)
        self.assertEqual(
            self.anuncios,
            ["Canción movida a la posición 2 de 3"])
        self.assertEqual(
            [tema.titulo for tema in dialogo.datos()[1]], ["B", "A", "C"])

    def test_alt_arriba_en_el_borde_anuncia_la_posicion_que_tiene(self):
        dialogo = self._abrir(carpeta=(A, B), lista=(A, B))
        self._enfocar(dialogo.lb_lista, 0)
        self._pulsar(wx.WXK_UP, alt=True)
        self.assertEqual(self._filas(dialogo.lb_lista), ["A", "B"])
        self.assertEqual(
            self.anuncios,
            ["Canción movida a la posición 1 de 2"])

    def test_aplicaciones_abre_el_menu_una_vez(self):
        dialogo = self._abrir(carpeta=(A, B), lista=(A, B))
        self._enfocar(dialogo.lb_lista, 0)
        with mock.patch.object(dialogo.lb_lista, "PopupMenu") as popup:
            self._pulsar(wx.WXK_WINDOWS_MENU)
        self.assertEqual(popup.call_count, 1)

    def test_mayus_f10_abre_el_menu_una_vez(self):
        dialogo = self._abrir(carpeta=(A, B), lista=(A, B))
        self._enfocar(dialogo.lb_lista, 0)
        with mock.patch.object(dialogo.lb_lista, "PopupMenu") as popup:
            self._pulsar(wx.WXK_F10, shift=True)
        self.assertEqual(popup.call_count, 1)

    def test_intro_en_la_lista_reproduce_sin_cerrar_ni_marcar(self):
        reproducir = mock.Mock()
        dialogo = self._abrir(
            carpeta=(A, B), lista=(A, B), reproducir=reproducir)
        self._enfocar(dialogo.lb_lista, 1)
        with mock.patch.object(dialogo, "EndModal") as fin:
            self._pulsar(wx.WXK_RETURN, tipo=wx.wxEVT_CHAR_HOOK)
        reproducir.assert_called_once_with(B)
        fin.assert_not_called()
        self.assertEqual(self._filas(dialogo.lb_lista), ["A", "B"])
        self.assertTrue(dialogo.lb_todas.IsItemChecked(1))

    def test_intro_en_todas_reproduce_sin_marcar(self):
        reproducir = mock.Mock()
        dialogo = self._abrir(
            carpeta=(A, B), lista=(), reproducir=reproducir)
        self._enfocar(dialogo.lb_todas, 1)
        with mock.patch.object(dialogo, "EndModal") as fin:
            evento = wx.KeyEvent(wx.wxEVT_CHAR_HOOK)
            evento.KeyCode = wx.WXK_RETURN
            dialogo.lb_todas.GetEventHandler().ProcessEvent(evento)
        reproducir.assert_called_once_with(B)
        fin.assert_not_called()
        self.assertEqual(self._filas(dialogo.lb_lista), [VACIA])
        self.assertFalse(dialogo.lb_todas.IsItemChecked(1))

    def test_aplicaciones_en_todas_abre_el_menu_una_vez(self):
        dialogo = self._abrir(carpeta=(A, B))
        self._enfocar(dialogo.lb_todas, 0)
        with mock.patch.object(dialogo.lb_todas, "PopupMenu") as popup:
            self._pulsar_en_todas(wx.WXK_WINDOWS_MENU)
        self.assertEqual(popup.call_count, 1)

    def test_mayus_f10_en_todas_abre_el_menu_una_vez(self):
        dialogo = self._abrir(carpeta=(A, B))
        self._enfocar(dialogo.lb_todas, 0)
        with mock.patch.object(dialogo.lb_todas, "PopupMenu") as popup:
            self._pulsar_en_todas(wx.WXK_F10, shift=True)
        self.assertEqual(popup.call_count, 1)

    def test_clic_derecho_en_todas_abre_el_menu(self):
        dialogo = self._abrir(carpeta=(A, B))
        with mock.patch.object(dialogo.lb_todas, "PopupMenu") as popup:
            dialogo.lb_todas.ProcessEvent(
                wx.ContextMenuEvent(wx.wxEVT_CONTEXT_MENU))
        popup.assert_called_once()

    def test_escribir_en_todas_elige_la_que_empieza(self):
        dialogo = self._abrir(carpeta=(A, B))
        self._enfocar(dialogo.lb_todas, 0)
        with mock.patch.object(wx, "CallLater"), \
                mock.patch("guyrapu.ui.busqueda_teclado.anunciar"):
            evento = wx.KeyEvent(wx.wxEVT_CHAR)
            evento.SetUnicodeKey(ord("B"))
            dialogo.lb_todas.GetEventHandler().ProcessEvent(evento)
        self.assertEqual(dialogo.lb_todas.GetFirstSelected(), 1)

    def test_flecha_en_el_borde_de_todas_suena_la_orilla(self):
        dialogo = self._abrir(carpeta=(A, B))
        self._enfocar(dialogo.lb_todas, 0)
        with mock.patch.object(
                lista_acciones._snd, "reproducir") as sonar:
            self._pulsar_en_todas(wx.WXK_UP)
        sonar.assert_called_once_with("orilla")

    def test_el_menu_de_todas_tiene_sus_cuatro_acciones_en_orden(self):
        dialogo = self._abrir(carpeta=(A, B))
        dialogo.lb_todas.Select(0, False)
        items = self._menu_todas().GetMenuItems()
        self.assertEqual(
            [item.GetItemLabel() for item in items],
            ["&Reproducir\tEnter", "&Agregar a la lista",
             "&Eliminar de la lista\tDel", "Agregar &todas a la lista"])
        self.assertEqual(
            [item.IsEnabled() for item in items],
            [False, False, False, True])

    def test_agregar_a_la_lista_marca_y_anuncia_como_la_casilla(self):
        dialogo = self._abrir(carpeta=(A, B), lista=())
        indice = self._indice_todas("A")
        self._enfocar(dialogo.lb_todas, indice)
        self._ejecutar_todas(musica_menus.ACCION_AGREGAR_A_LISTA)
        self.assertEqual(
            [tema.titulo for tema in dialogo._lista.temas], ["A"])
        self.assertTrue(dialogo.lb_todas.IsItemChecked(indice))
        self.assertEqual(
            self.anuncios,
            ["Agregada a la lista: A. 1 canción en total"])

    def test_eliminar_de_la_lista_desmarca_y_anuncia_como_la_casilla(self):
        dialogo = self._abrir(carpeta=(A, B), lista=(A, B))
        indice = self._indice_todas("A")
        self._enfocar(dialogo.lb_todas, indice)
        self._ejecutar_todas(musica_menus.ACCION_QUITAR_DE_LISTA)
        self.assertEqual(
            [tema.titulo for tema in dialogo._lista.temas], ["B"])
        self.assertFalse(dialogo.lb_todas.IsItemChecked(indice))
        self.assertEqual(
            self.anuncios,
            ["Eliminada de la lista: A. Queda 1 canción"])

    def test_agregar_a_la_lista_dice_que_ya_esta(self):
        dialogo = self._abrir(carpeta=(A,), lista=(A,))
        self._enfocar(dialogo.lb_todas, self._indice_todas("A"))
        with mock.patch.object(lista_acciones, "anunciar") as anunciar:
            self._ejecutar_todas(musica_menus.ACCION_AGREGAR_A_LISTA)
        anunciar.assert_called_once_with("Ya está en la lista.")

    def test_eliminar_de_la_lista_dice_que_no_esta(self):
        dialogo = self._abrir(carpeta=(A,), lista=())
        self._enfocar(dialogo.lb_todas, self._indice_todas("A"))
        with mock.patch.object(lista_acciones, "anunciar") as anunciar:
            self._ejecutar_todas(musica_menus.ACCION_QUITAR_DE_LISTA)
        anunciar.assert_called_once_with("No está en la lista.")

    def test_agregar_todas_dice_que_ya_estan_todas(self):
        self._abrir(carpeta=(A,), lista=(A,))
        with mock.patch.object(lista_acciones, "anunciar") as anunciar:
            self._ejecutar_todas(musica_menus.ACCION_AGREGAR_TODAS_A_LISTA)
        anunciar.assert_called_once_with("Ya están todas en la lista.")

    def test_agregar_todas_suma_en_orden_marca_y_anuncia_una_vez(self):
        dialogo = self._abrir(carpeta=(C, A, B), lista=(B,))
        self._ejecutar_todas(musica_menus.ACCION_AGREGAR_TODAS_A_LISTA)
        self.assertEqual(
            [tema.titulo for tema in dialogo._lista.temas],
            ["B", "C", "A"])
        self.assertEqual(
            self._filas(dialogo.lb_lista), ["B", "C", "A"])
        for indice in range(3):
            self.assertTrue(dialogo.lb_todas.IsItemChecked(indice))
        self.assertEqual(
            self.anuncios,
            ["2 canciones agregadas a la lista. 3 canciones en total"])

    def test_agregar_todas_sin_filas_dice_el_texto_vacio(self):
        dialogo = self._abrir(carpeta=(A,), lista=())
        dialogo.txt_buscar.SetValue("zzz")
        dialogo._aplicar_filtro()
        with mock.patch.object(lista_acciones, "anunciar") as anunciar:
            self._ejecutar_todas(musica_menus.ACCION_AGREGAR_TODAS_A_LISTA)
        anunciar.assert_called_once_with(
            "Ninguna canción coincide con la búsqueda.")

    def test_marcar_con_fijar_no_agrega_ni_anuncia(self):
        dialogo = self._abrir(carpeta=(A, B), lista=(A,))
        self.assertTrue(dialogo.lb_todas.IsItemChecked(0))
        self.assertFalse(dialogo.lb_todas.IsItemChecked(1))
        self.assertEqual(
            [tema.titulo for tema in dialogo._lista.temas], ["A"])
        self.assertEqual(self.anuncios, [])

    def test_sin_canciones_la_linea_vacia_lo_dice(self):
        dialogo = self._abrir(carpeta=())
        self.assertEqual(
            self._filas(dialogo.lb_todas),
            ["No hay canciones en la carpeta de música."])

    def test_sin_coincidencias_la_linea_vacia_lo_dice(self):
        dialogo = self._abrir(carpeta=(A, B))
        dialogo.txt_buscar.SetValue("zzz")
        dialogo._aplicar_filtro()
        self.assertEqual(
            self._filas(dialogo.lb_todas),
            ["Ninguna canción coincide con la búsqueda."])

    def test_escape_cancela_el_cuadro(self):
        dialogo = self._abrir(carpeta=(A,), lista=(A,))
        with mock.patch.object(dialogo, "EndModal") as fin:
            dialogo._tecla(Evento(wx.WXK_ESCAPE))
        fin.assert_called_once_with(wx.ID_CANCEL)

    def test_intro_fuera_de_las_listas_sigue_su_camino(self):
        reproducir = mock.Mock()
        dialogo = self._abrir(carpeta=(A,), reproducir=reproducir)
        dialogo.txt_buscar.SetFocus()
        wx.Yield()
        evento = Evento(wx.WXK_RETURN)
        dialogo._tecla(evento)
        self.assertTrue(evento.skipped)
        reproducir.assert_not_called()

    def test_escribir_en_buscar_filtra_sin_cambiar_la_lista_ni_anunciar(self):
        dialogo = self._abrir(carpeta=(A, B), lista=(A,))
        dialogo.txt_buscar.SetValue("b")
        dialogo._aplicar_filtro()
        self.assertEqual(self._filas(dialogo.lb_todas), ["B"])
        self.assertEqual(self._filas(dialogo.lb_lista), ["A"])
        self.assertEqual(self.anuncios, [])

    def test_anuncios_en_ingles_usan_los_plurales(self):
        idioma.instalar("en")
        try:
            dialogo = self._abrir(carpeta=(A, B, C), lista=())
            for indice in range(3):
                self._marcar(indice, True)
            self.assertEqual(
                self.anuncios[0],
                "Added to the list: A. 1 song in total")
            self.assertEqual(
                self.anuncios[1],
                "Added to the list: B. 2 songs in total")
            self.assertEqual(
                self.anuncios[2],
                "Added to the list: C. 3 songs in total")
            self._marcar(1, False)
            self.assertEqual(
                self.anuncios[3],
                "Removed from the list: B. 2 songs left")
            self._marcar(2, False)
            self.assertEqual(
                self.anuncios[4],
                "Removed from the list: C. 1 song left")
        finally:
            idioma._reiniciar()
        self.assertEqual(dialogo.lb_lista.GetItemCount(), 1)

    def test_una_cancion_fuera_de_la_carpeta_solo_aparece_en_la_lista(self):
        externo = Tema("C:/Otra/externo.mp3", "Externo")
        dialogo = self._abrir(carpeta=(A,), lista=(A, externo))
        self.assertEqual(
            self._filas(dialogo.lb_lista), ["A", "Externo"])
        self.assertEqual(self._filas(dialogo.lb_todas), ["A"])
        self.assertEqual(dialogo.lb_todas.GetItemCount(), 1)

    def test_el_cuadro_entra_en_una_pantalla_de_768(self):
        carpeta = tuple(
            Tema(f"C:/Musica/t{indice}.mp3", f"T{indice}")
            for indice in range(14))
        dialogo = self._abrir(carpeta=carpeta, lista=carpeta[:3])
        self.assertLessEqual(dialogo.GetSize().height, 700)

    def test_orden_de_tab_nombres_accesibles_y_foco_al_editar(self):
        dialogo = self._abrir(nombre="Lista", carpeta=(A,))
        self._comprobar_orden_y_nombres(dialogo)
        self.assertIs(wx.Window.FindFocus(), dialogo.lb_lista)

    def test_orden_de_tab_nombres_accesibles_y_foco_al_crear(self):
        dialogo = self._abrir(nombre="", carpeta=(A,))
        self._comprobar_orden_y_nombres(dialogo)
        self.assertIs(wx.Window.FindFocus(), dialogo.txt_nombre)

    def _comprobar_orden_y_nombres(self, dialogo):
        panel = next(hijo for hijo in dialogo.GetChildren()
                     if isinstance(hijo, wx.Panel))
        interactivos = [
            control for control in panel.GetChildren()
            if isinstance(control, (wx.TextCtrl, wx.ListCtrl, wx.Button))]
        self.assertEqual([control.GetName() for control in interactivos], [
            "Nombre de la lista", "Canciones de la lista",
            "Buscar canciones", "Todas las canciones",
            "Guardar", "Cancelar"])


if __name__ == "__main__":
    unittest.main()
