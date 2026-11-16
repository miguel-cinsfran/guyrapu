# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de la lista de grabaciones como panel. Requieren entorno gráfico."""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import wx

from guyrapu.obs import grabaciones
from guyrapu.ui import gui_grabaciones, lista_acciones
from tests.ventanas_prueba import app_de_prueba, destruir


class TestPanelGrabaciones(unittest.TestCase):

    def setUp(self):
        self.app = app_de_prueba()
        self.temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)
        self.carpeta = Path(self.temporal.name)
        self.ruta = self.carpeta / "grabaciones.json"
        parche = mock.patch.object(grabaciones.paths, "grabaciones",
                                   return_value=self.ruta)
        parche.start()
        self.addCleanup(parche.stop)
        for parche in (
                mock.patch.object(gui_grabaciones, "anunciar"),
                mock.patch.object(lista_acciones, "anunciar"),
                mock.patch.object(gui_grabaciones.sound_player, "reproducir"),
                mock.patch.object(gui_grabaciones, "copiar_al_portapapeles")):
            parche.start()
            self.addCleanup(parche.stop)

    def _archivo(self, nombre, bytes_=16):
        ruta = self.carpeta / nombre
        ruta.write_bytes(b"x" * bytes_)
        return ruta

    def _panel(self):
        padre = wx.Frame(None)
        self.addCleanup(destruir, padre)
        panel = gui_grabaciones.PanelGrabaciones(padre)
        self.addCleanup(destruir, panel)
        return panel

    def _tecla(self, panel, tipo, codigo, shift=False):
        evento = wx.KeyEvent(tipo)
        evento.SetKeyCode(codigo)
        if shift:
            evento.SetShiftDown(True)
        panel._lista.GetEventHandler().ProcessEvent(evento)

    def _etiquetas_del_menu(self, panel):
        etiquetas = []

        def popup(menu):
            etiquetas.extend(item.GetItemLabel()
                             for item in menu.GetMenuItems())

        with mock.patch.object(panel._lista, "PopupMenu", side_effect=popup):
            self._tecla(panel, wx.wxEVT_KEY_DOWN, wx.WXK_WINDOWS_MENU)
        return etiquetas

    def _elegir_en_menu(self, panel, etiqueta):
        def popup(menu):
            for item in menu.GetMenuItems():
                if item.GetItemLabelText().split("\t")[0] == etiqueta:
                    menu.ProcessEvent(
                        wx.CommandEvent(wx.EVT_MENU.typeId, item.GetId()))

        with mock.patch.object(panel._lista, "PopupMenu", side_effect=popup):
            self._tecla(panel, wx.wxEVT_KEY_DOWN, wx.WXK_WINDOWS_MENU)

    def _anotar_varios(self, nombres):
        for nombre in nombres:
            grabaciones.anotar(self._archivo(nombre), ruta=self.ruta,
                               ahora=1000)

    def test_nombres_accesibles_exactos(self):
        panel = self._panel()
        self.assertEqual(panel._lista.GetName(), "Grabaciones y clips")

    def test_orden_de_tab(self):
        panel = self._panel()
        self.assertEqual([panel._lista.GetName()], ["Grabaciones y clips"])

    def test_poblar_deja_la_primera_fila_seleccionada(self):
        grabaciones.anotar(self._archivo("primera.mp4"), ruta=self.ruta,
                           ahora=1000)
        grabaciones.anotar(self._archivo("segunda.mp4"), ruta=self.ruta,
                           ahora=2000)
        panel = self._panel()
        self.assertEqual(panel._lista.GetSelection(), 0)
        self.assertIn("segunda.mp4", panel._lista.GetString(0))

    def test_una_fila_de_clip_dice_clip(self):
        archivo = self._archivo("clip.mp4", 2 * 1024 * 1024)
        grabaciones.anotar(archivo, ruta=self.ruta, ahora=1000, tipo="clip")
        panel = self._panel()
        fila = panel._lista.GetString(0)
        self.assertTrue(fila.startswith("Clip, clip.mp4, "))
        self.assertTrue(fila.endswith("2 MB"))

    def test_sin_grabaciones_la_fila_y_cualquier_accion_lo_dicen(self):
        panel = self._panel()
        self.assertEqual(panel._lista.GetCount(), 1)
        self.assertEqual(panel._lista.GetString(0),
                         "No hay grabaciones ni clips guardados.")
        for tipo, codigo in ((wx.wxEVT_CHAR_HOOK, wx.WXK_RETURN),
                             (wx.wxEVT_KEY_DOWN, wx.WXK_DELETE)):
            with self.subTest(codigo=codigo):
                lista_acciones.anunciar.reset_mock()
                self._tecla(panel, tipo, codigo)
                lista_acciones.anunciar.assert_called_once_with(
                    "No hay grabaciones ni clips guardados.")
        with mock.patch.object(panel, "_abrir_carpeta") as abrir_carpeta, \
                mock.patch.object(panel, "_copiar_ruta") as copiar:
            for clave in ("abrir_carpeta", "copiar_ruta"):
                lista_acciones.anunciar.reset_mock()
                panel._lista_acciones.ejecutar(clave)
                lista_acciones.anunciar.assert_called_once_with(
                    "No hay grabaciones ni clips guardados.")
            abrir_carpeta.assert_not_called()
            copiar.assert_not_called()

    def test_el_menu_tiene_las_cuatro_acciones_en_orden_y_con_su_tecla(self):
        panel = self._panel()
        self.assertEqual(
            self._etiquetas_del_menu(panel),
            ["&Abrir\tEnter", "Abrir ca&rpeta", "&Copiar ruta",
             "E&liminar de la lista\tDel"])

    def test_suprimir_saca_la_fila_y_deja_el_archivo_en_el_disco(self):
        primero = self._archivo("primero.mp4")
        segundo = self._archivo("segundo.mp4")
        grabaciones.anotar(primero, ruta=self.ruta, ahora=1000)
        grabaciones.anotar(segundo, ruta=self.ruta, ahora=2000)
        panel = self._panel()
        panel._lista.SetSelection(0)
        self._tecla(panel, wx.wxEVT_KEY_DOWN, wx.WXK_DELETE)
        self.assertTrue(segundo.is_file())
        self.assertEqual(panel._lista.GetCount(), 1)
        self.assertIn("primero.mp4", panel._lista.GetString(0))
        self.assertEqual([e["ruta"] for e in grabaciones.leer(self.ruta)],
                         [str(primero)])
        self.assertIs(panel.FindFocus(), panel._lista)
        gui_grabaciones.anunciar.assert_called_with(
            "Eliminada de la lista")

    def test_abrir_y_copiar_la_ruta(self):
        archivo = self._archivo("clip.mp4")
        grabaciones.anotar(archivo, ruta=self.ruta, ahora=1000)
        panel = self._panel()
        with mock.patch.object(gui_grabaciones.os, "startfile") as startfile:
            self._tecla(panel, wx.wxEVT_CHAR_HOOK, wx.WXK_RETURN)
        startfile.assert_called_once_with(str(archivo))
        self._elegir_en_menu(panel, "Copiar ruta")
        gui_grabaciones.copiar_al_portapapeles.assert_called_once_with(
            str(archivo))
        gui_grabaciones.anunciar.assert_called_with("Ruta copiada")
        gui_grabaciones.sound_player.reproducir.assert_called_with("copiar")

    def test_intro_por_char_hook_abre(self):
        grabaciones.anotar(self._archivo("clip.mp4"), ruta=self.ruta,
                           ahora=1000)
        panel = self._panel()
        evento = wx.KeyEvent(wx.wxEVT_CHAR_HOOK)
        evento.KeyCode = wx.WXK_RETURN
        with mock.patch.object(panel, "_abrir") as abrir:
            panel._lista.GetEventHandler().ProcessEvent(evento)
        abrir.assert_called_once_with()

    def test_doble_clic_abre_la_grabacion(self):
        grabaciones.anotar(self._archivo("clip.mp4"), ruta=self.ruta,
                           ahora=1000)
        panel = self._panel()
        evento = wx.CommandEvent(wx.EVT_LISTBOX_DCLICK.typeId,
                                 panel._lista.GetId())
        evento.SetEventObject(panel._lista)
        with mock.patch.object(panel, "_abrir") as abrir:
            panel._lista.GetEventHandler().ProcessEvent(evento)
        abrir.assert_called_once_with()

    def test_el_menu_ejecuta_las_cuatro_acciones(self):
        grabaciones.anotar(self._archivo("clip.mp4"), ruta=self.ruta,
                           ahora=1000)
        panel = self._panel()

        def popup(menu):
            for item in menu.GetMenuItems():
                menu.ProcessEvent(
                    wx.CommandEvent(wx.EVT_MENU.typeId, item.GetId()))

        with mock.patch.object(panel, "_abrir") as abrir, \
                mock.patch.object(panel, "_abrir_carpeta") as abrir_carpeta, \
                mock.patch.object(panel, "_copiar_ruta") as copiar, \
                mock.patch.object(panel, "_eliminar") as eliminar, \
                mock.patch.object(panel._lista, "PopupMenu",
                                  side_effect=popup):
            self._tecla(panel, wx.wxEVT_KEY_DOWN, wx.WXK_WINDOWS_MENU)
        abrir.assert_called_once_with()
        abrir_carpeta.assert_called_once_with()
        copiar.assert_called_once_with()
        eliminar.assert_called_once_with()

    def test_mayus_f10_abre_el_mismo_menu(self):
        panel = self._panel()
        with mock.patch.object(panel._lista, "PopupMenu") as mostrar:
            self._tecla(panel, wx.wxEVT_KEY_DOWN, wx.WXK_F10, shift=True)
        mostrar.assert_called_once()

    def test_el_clic_derecho_abre_el_menu(self):
        panel = self._panel()
        evento = wx.ContextMenuEvent(wx.wxEVT_CONTEXT_MENU,
                                     panel._lista.GetId())
        evento.SetEventObject(panel._lista)
        with mock.patch.object(panel._lista, "PopupMenu") as mostrar:
            panel._lista.ProcessEvent(evento)
        mostrar.assert_called_once()

    def test_abrir_carpeta_selecciona_el_archivo(self):
        archivo = self._archivo("clip.mp4")
        grabaciones.anotar(archivo, ruta=self.ruta, ahora=1000)
        panel = self._panel()
        with mock.patch.object(gui_grabaciones.subprocess, "Popen") as abrir:
            self._elegir_en_menu(panel, "Abrir carpeta")
        abrir.assert_called_once_with(["explorer", "/select,", str(archivo)])

    def test_abrir_carpeta_usa_el_mp4_convertido_con_barras_invertidas(self):
        mp4 = self._archivo("clip.mp4")
        anotada = str(self.carpeta / "clip.mkv").replace("\\", "/")
        grabaciones.anotar(anotada, ruta=self.ruta, ahora=1000)
        panel = self._panel()
        with mock.patch.object(gui_grabaciones.subprocess, "Popen") as abrir:
            self._elegir_en_menu(panel, "Abrir carpeta")
        abrir.assert_called_once_with(["explorer", "/select,", str(mp4)])
        self.assertIn("\\", abrir.call_args.args[0][2])

    def test_eliminar_saca_la_entrada_anotada_aunque_la_fila_muestre_el_mp4(self):
        self._archivo("clip.mp4")
        anotada = str(self.carpeta / "clip.mkv").replace("\\", "/")
        grabaciones.anotar(anotada, ruta=self.ruta, ahora=1000)
        panel = self._panel()
        self.assertIn("clip.mp4", panel._lista.GetString(0))
        panel._lista.SetSelection(0)
        self._tecla(panel, wx.wxEVT_KEY_DOWN, wx.WXK_DELETE)
        self.assertEqual(grabaciones.leer(self.ruta), [])

    def test_abrir_archivo_o_carpeta_que_ya_no_estan_avisa(self):
        subcarpeta = self.carpeta / "no-existe"
        subcarpeta.mkdir()
        archivo = subcarpeta / "clip.mp4"
        archivo.write_bytes(b"x" * 16)
        grabaciones.anotar(archivo, ruta=self.ruta, ahora=1000)
        panel = self._panel()
        archivo.unlink()
        subcarpeta.rmdir()
        panel._abrir()
        gui_grabaciones.anunciar.assert_called_with(
            "El archivo ya no está disponible.")
        gui_grabaciones.sound_player.reproducir.assert_called_with("error")
        panel._abrir_carpeta()
        gui_grabaciones.anunciar.assert_called_with(
            "La carpeta ya no está disponible.")

    def test_tras_eliminar_queda_en_la_misma_posicion_y_el_foco_vuelve(self):
        self._anotar_varios(("uno.mp4", "dos.mp4", "tres.mp4"))
        panel = self._panel()
        panel._lista.SetSelection(1)
        self._tecla(panel, wx.wxEVT_KEY_DOWN, wx.WXK_DELETE)
        self.assertEqual(panel._lista.GetSelection(), 1)
        self.assertIn("uno.mp4", panel._lista.GetString(1))
        self.assertEqual(panel._lista_acciones.indice(), 1)
        self.assertIs(panel.FindFocus(), panel._lista)

    def test_tras_eliminar_la_ultima_queda_en_la_ultima(self):
        self._anotar_varios(("uno.mp4", "dos.mp4"))
        panel = self._panel()
        panel._lista.SetSelection(1)
        self._tecla(panel, wx.wxEVT_KEY_DOWN, wx.WXK_DELETE)
        self.assertEqual(panel._lista.GetCount(), 1)
        self.assertEqual(panel._lista.GetSelection(), 0)
        self.assertEqual(panel._lista_acciones.indice(), 0)
        self.assertIs(panel.FindFocus(), panel._lista)

    def test_lo_borrado_del_disco_no_se_muestra(self):
        queda = self._archivo("queda.mp4")
        borrado = self._archivo("borrado.mp4")
        grabaciones.anotar(queda, ruta=self.ruta, ahora=1000)
        grabaciones.anotar(borrado, ruta=self.ruta, ahora=2000)
        borrado.unlink()
        panel = self._panel()
        self.assertEqual(panel._lista.GetCount(), 1)
        self.assertIn("queda.mp4", panel._lista.GetString(0))


if __name__ == "__main__":
    unittest.main()
