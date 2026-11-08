"""Pruebas wx del editor de listas: casillas, teclas, foco y orden de Tab.

Abre una ventana.
"""

import unittest
from unittest import mock

from guyrapu.core import idioma
from guyrapu.music.modelo import Tema
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
        self.assertEqual(self._filas(dialogo.lb_lista), [])
        self.assertFalse(dialogo.lb_todas.IsItemChecked(0))
        self.assertEqual(
            self.anuncios,
            ["Eliminada de la lista: A. Quedan 0 canciones"])

    def test_supr_quita_desmarca_y_deja_el_foco(self):
        dialogo = self._abrir(carpeta=(A, B, C), lista=(A, B, C))
        self._enfocar(dialogo.lb_lista, 1)
        dialogo._tecla(Evento(wx.WXK_DELETE))
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
        dialogo._tecla(Evento(wx.WXK_DELETE))
        self.assertIs(wx.Window.FindFocus(), dialogo.lb_lista)
        self.assertEqual(dialogo.lb_lista.GetFocusedItem(), 0)

    def test_alt_abajo_mueve_enfoca_y_anuncia_la_posicion(self):
        dialogo = self._abrir(carpeta=(A, B, C), lista=(A, B, C))
        self._enfocar(dialogo.lb_lista, 0)
        dialogo._tecla(Evento(wx.WXK_DOWN, wx.MOD_ALT))
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
        dialogo._tecla(Evento(wx.WXK_UP, wx.MOD_ALT))
        self.assertEqual(self._filas(dialogo.lb_lista), ["A", "B"])
        self.assertEqual(
            self.anuncios,
            ["Canción movida a la posición 1 de 2"])

    def test_intro_en_la_lista_reproduce_sin_cerrar_ni_marcar(self):
        reproducir = mock.Mock()
        dialogo = self._abrir(
            carpeta=(A, B), lista=(A, B), reproducir=reproducir)
        self._enfocar(dialogo.lb_lista, 1)
        with mock.patch.object(dialogo, "EndModal") as fin:
            dialogo._tecla(Evento(wx.WXK_RETURN))
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
            dialogo._tecla(Evento(wx.WXK_NUMPAD_ENTER))
        reproducir.assert_called_once_with(B)
        fin.assert_not_called()
        self.assertEqual(self._filas(dialogo.lb_lista), [])
        self.assertFalse(dialogo.lb_todas.IsItemChecked(1))

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
