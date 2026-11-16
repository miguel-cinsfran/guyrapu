# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from guyrapu.capture import redaccion
from guyrapu.ui import gui_historial
from guyrapu.ui import lista_acciones
from guyrapu.core import historial
from tests.pseudo_prueba import con_pseudo, textos_sin_marcar
from tests.ventanas_prueba import app_de_prueba, destruir


def entrada(plataforma, clave, url):
    return {
        "plataforma": plataforma,
        "clave": clave,
        "url": url,
        "titulo": f"Título {clave}",
        "canal": f"Canal {clave}",
        "fecha": "2026-08-28T12:00:00",
        "directo": False,
    }


class PruebasHistorialDialog(unittest.TestCase):

    def setUp(self):
        self.app = app_de_prueba()
        self.temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)
        self.ruta = Path(self.temporal.name) / "historial.json"

    def _dialogo(self, entradas, on_conectar=None):
        self.ruta.write_text(json.dumps(entradas), encoding="utf-8")
        dialogo = gui_historial.HistorialDialog(None, self.ruta,
                                                on_conectar or mock.Mock())
        self.addCleanup(destruir, dialogo)
        return dialogo

    def _tecla(self, tipo, codigo, lista, shift=False):
        evento = gui_historial.wx.KeyEvent(tipo)
        evento.SetKeyCode(codigo)
        if shift:
            evento.SetShiftDown(True)
        lista.GetEventHandler().ProcessEvent(evento)

    def _elegir_en_menu(self, lista, textos):
        def popup(menu):
            for item in menu.GetMenuItems():
                if item.GetItemLabelText().split("\t")[0] in textos:
                    menu.ProcessEvent(gui_historial.wx.CommandEvent(
                        gui_historial.wx.EVT_MENU.typeId, item.GetId()))

        with mock.patch.object(lista, "PopupMenu", side_effect=popup):
            self._tecla(gui_historial.wx.wxEVT_KEY_DOWN,
                        gui_historial.wx.WXK_WINDOWS_MENU, lista)

    def test_poblar_separa_las_entradas_por_plataforma(self):
        youtube = entrada("youtube", "yt", "https://youtube.com/watch?v=yt")
        tiktok = entrada("tiktok", "tk", "https://tiktok.com/@tk/live")
        dialogo = self._dialogo([youtube, tiktok])

        self.assertEqual([historial.etiqueta(youtube)],
                         list(dialogo._listas["youtube"].GetStrings()))
        self.assertEqual([historial.etiqueta(tiktok)],
                         list(dialogo._listas["tiktok"].GetStrings()))

    def test_historial_vacio_mantiene_los_botones_habilitados_y_con_el_motivo(self):
        dialogo = self._dialogo([])

        self.assertTrue(dialogo.btn_conectar.IsEnabled())
        self.assertTrue(dialogo.btn_quitar.IsEnabled())
        motivo = "El historial está vacío"
        self.assertEqual(
            redaccion.etiqueta_con_motivo("&Conectar", motivo),
            dialogo.btn_conectar.GetLabel())
        self.assertEqual(
            redaccion.etiqueta_con_motivo("E&liminar", motivo),
            dialogo.btn_quitar.GetLabel())

    def test_con_entradas_las_etiquetas_son_la_base_sola(self):
        dialogo = self._dialogo([
            entrada("youtube", "yt", "https://youtube.com/watch?v=yt")])

        self.assertTrue(dialogo.btn_conectar.IsEnabled())
        self.assertTrue(dialogo.btn_quitar.IsEnabled())
        self.assertEqual("&Conectar", dialogo.btn_conectar.GetLabel())
        self.assertEqual("E&liminar", dialogo.btn_quitar.GetLabel())

    def test_la_tecla_de_aplicaciones_abre_el_menu_con_las_acciones(self):
        dialogo = self._dialogo([
            entrada("youtube", "yt", "https://youtube.com/watch?v=yt")])
        etiquetas = []

        def popup(menu):
            etiquetas.extend(item.GetItemLabel()
                             for item in menu.GetMenuItems())

        with mock.patch.object(dialogo._listas["youtube"], "PopupMenu",
                               side_effect=popup):
            self._tecla(gui_historial.wx.wxEVT_KEY_DOWN,
                        gui_historial.wx.WXK_WINDOWS_MENU,
                        dialogo._listas["youtube"])

        self.assertEqual(["&Conectar\tEnter", "E&liminar\tDel"], etiquetas)

    def test_mayus_f10_abre_el_menu(self):
        dialogo = self._dialogo([])
        with mock.patch.object(dialogo._listas["youtube"],
                               "PopupMenu") as mostrar:
            self._tecla(gui_historial.wx.wxEVT_KEY_DOWN,
                        gui_historial.wx.WXK_F10,
                        dialogo._listas["youtube"], shift=True)
        mostrar.assert_called_once()

    def test_el_clic_derecho_abre_el_menu(self):
        dialogo = self._dialogo([])
        lista = dialogo._listas["youtube"]
        evento = gui_historial.wx.ContextMenuEvent(
            gui_historial.wx.wxEVT_CONTEXT_MENU, lista.GetId())
        evento.SetEventObject(lista)
        with mock.patch.object(lista, "PopupMenu") as mostrar:
            lista.ProcessEvent(evento)
        mostrar.assert_called_once()

    def test_el_menu_ejecuta_conectar_y_eliminar(self):
        dialogo = self._dialogo([
            entrada("youtube", "yt", "https://youtube.com/watch?v=yt")])
        with mock.patch.object(dialogo, "_conectar") as conectar, \
                mock.patch.object(dialogo, "_quitar") as quitar:
            self._elegir_en_menu(
                dialogo._listas["youtube"], ("Conectar", "Eliminar"))
        conectar.assert_called_once_with()
        quitar.assert_called_once_with()

    def test_cada_pestana_vacia_dice_no_hay_entradas_de_su_plataforma(self):
        solo_youtube = self._dialogo([
            entrada("youtube", "yt", "https://youtube.com/watch?v=yt")])
        self.assertEqual(
            ["No hay entradas de TikTok."],
            list(solo_youtube._listas["tiktok"].GetStrings()))

        solo_tiktok = self._dialogo([
            entrada("tiktok", "tk", "https://tiktok.com/@tk/live")])
        self.assertEqual(
            ["No hay entradas de YouTube."],
            list(solo_tiktok._listas["youtube"].GetStrings()))

    def test_conectar_con_historial_vacio_anuncia_el_motivo(self):
        dialogo = self._dialogo([])

        with mock.patch.object(gui_historial, "anunciar") as anunciar:
            dialogo._conectar()

        dialogo._on_conectar.assert_not_called()
        anunciar.assert_called_once_with("El historial está vacío.")

    def test_quitar_con_historial_vacio_anuncia_el_motivo(self):
        dialogo = self._dialogo([])

        with mock.patch.object(gui_historial, "anunciar") as anunciar:
            dialogo._quitar()

        anunciar.assert_called_once_with("El historial está vacío.")

    def test_quitar_sin_seleccion_anuncia_sin_seleccion(self):
        datos = entrada("youtube", "yt", "https://youtube.com/watch?v=yt")
        dialogo = self._dialogo([datos])
        dialogo._listas["youtube"].SetSelection(gui_historial.wx.NOT_FOUND)

        with mock.patch.object(gui_historial, "anunciar") as anunciar:
            dialogo._quitar()

        anunciar.assert_called_once_with("Sin selección")
        self.assertEqual([datos], historial.cargar(self.ruta))

    def test_quitar_en_pestana_vacia_con_entradas_en_otra_anuncia_sin_seleccion(self):
        youtube = entrada("youtube", "yt", "https://youtube.com/watch?v=yt")
        dialogo = self._dialogo([youtube])
        with mock.patch.object(gui_historial, "anunciar"):
            dialogo.nb.SetSelection(1)

        with mock.patch.object(gui_historial, "anunciar") as anunciar:
            dialogo._quitar()

        anunciar.assert_called_once_with("Sin selección")
        self.assertEqual([youtube], historial.cargar(self.ruta))

    def test_intro_sobre_la_fila_vacia_no_cierra_el_cuadro(self):
        dialogo = self._dialogo([])
        lista = dialogo._listas["youtube"]
        with mock.patch.object(gui_historial, "anunciar"), \
                mock.patch.object(lista_acciones, "anunciar") as anunciar, \
                mock.patch.object(dialogo, "EndModal") as end_modal:
            self._tecla(gui_historial.wx.wxEVT_CHAR_HOOK,
                        gui_historial.wx.WXK_RETURN, lista)

        anunciar.assert_called_once_with("No hay entradas de YouTube.")
        end_modal.assert_not_called()

    def test_quitar_la_ultima_entrada_deja_el_motivo_en_las_etiquetas(self):
        dialogo = self._dialogo([
            entrada("youtube", "yt", "https://youtube.com/watch?v=yt")])

        with mock.patch.object(gui_historial, "anunciar"):
            dialogo._quitar()

        motivo = "El historial está vacío"
        self.assertEqual(
            redaccion.etiqueta_con_motivo("&Conectar", motivo),
            dialogo.btn_conectar.GetLabel())
        self.assertEqual(
            redaccion.etiqueta_con_motivo("E&liminar", motivo),
            dialogo.btn_quitar.GetLabel())

    def test_suprimir_deja_elegida_la_fila_que_ocupa_el_lugar(self):
        primera = entrada("youtube", "primera", "https://youtube.com/primera")
        segunda = entrada("youtube", "segunda", "https://youtube.com/segunda")
        tercera = entrada("youtube", "tercera", "https://youtube.com/tercera")
        dialogo = self._dialogo([primera, segunda, tercera])
        lista = dialogo._listas["youtube"]
        lista.SetSelection(1)

        with mock.patch.object(gui_historial, "anunciar"):
            self._tecla(gui_historial.wx.wxEVT_KEY_DOWN,
                        gui_historial.wx.WXK_DELETE, lista)

        self.assertEqual(1, lista.GetSelection())
        self.assertEqual(tercera, dialogo._seleccionada())

    def test_suprimir_la_ultima_deja_elegida_la_anterior(self):
        primera = entrada("youtube", "primera", "https://youtube.com/primera")
        segunda = entrada("youtube", "segunda", "https://youtube.com/segunda")
        tercera = entrada("youtube", "tercera", "https://youtube.com/tercera")
        dialogo = self._dialogo([primera, segunda, tercera])
        lista = dialogo._listas["youtube"]
        lista.SetSelection(2)

        with mock.patch.object(gui_historial, "anunciar"):
            self._tecla(gui_historial.wx.wxEVT_KEY_DOWN,
                        gui_historial.wx.WXK_DELETE, lista)

        self.assertEqual(1, lista.GetSelection())
        self.assertEqual(segunda, dialogo._seleccionada())

    def test_seleccionada_devuelve_la_entrada_elegida_o_none(self):
        primera = entrada("youtube", "primera", "https://youtube.com/watch?v=primera")
        segunda = entrada("youtube", "segunda", "https://youtube.com/watch?v=segunda")
        dialogo = self._dialogo([primera, segunda])

        dialogo._listas["youtube"].SetSelection(1)
        self.assertEqual(segunda, dialogo._seleccionada())
        dialogo._listas["youtube"].SetSelection(gui_historial.wx.NOT_FOUND)
        self.assertIsNone(dialogo._seleccionada())

    def test_pestana_tiktok_es_la_plataforma_actual(self):
        youtube = entrada("youtube", "solo-youtube", "https://youtube.com/solo-youtube")
        tiktok = entrada("tiktok", "solo-tiktok", "https://tiktok.com/solo-tiktok")
        dialogo = self._dialogo([youtube, tiktok])

        with mock.patch.object(gui_historial, "anunciar"):
            dialogo.nb.SetSelection(1)

        self.assertEqual("tiktok", dialogo._plat_actual())

    def test_pestana_tiktok_devuelve_su_entrada_seleccionada(self):
        youtube = entrada("youtube", "solo-youtube", "https://youtube.com/solo-youtube")
        tiktok = entrada("tiktok", "solo-tiktok", "https://tiktok.com/solo-tiktok")
        dialogo = self._dialogo([youtube, tiktok])

        with mock.patch.object(gui_historial, "anunciar"):
            dialogo.nb.SetSelection(1)

        self.assertEqual(tiktok, dialogo._seleccionada())

    def test_seleccionada_en_tiktok_con_filas_distintas_devuelve_tiktok(self):
        yt_primero = entrada("youtube", "yt-uno", "https://youtube.com/watch?v=yt-uno")
        yt_segundo = entrada("youtube", "yt-dos", "https://youtube.com/watch?v=yt-dos")
        tk_primero = entrada("tiktok", "tk-uno", "https://tiktok.com/@tk-uno/live")
        tk_segundo = entrada("tiktok", "tk-dos", "https://tiktok.com/@tk-dos/live")
        dialogo = self._dialogo([yt_primero, yt_segundo, tk_primero, tk_segundo])

        dialogo._listas["youtube"].SetSelection(1)
        dialogo._listas["tiktok"].SetSelection(0)
        with mock.patch.object(gui_historial, "anunciar"):
            dialogo.nb.SetSelection(1)

        self.assertEqual(tk_primero, dialogo._seleccionada())

    def test_conectar_en_youtube_con_filas_distintas_entrega_youtube(self):
        yt_primero = entrada("youtube", "yt-uno", "https://youtube.com/watch?v=yt-uno")
        url_youtube = "https://youtube.com/watch?v=yt-dos"
        yt_segundo = entrada("youtube", "yt-dos", url_youtube)
        tk_primero = entrada("tiktok", "tk-uno", "https://tiktok.com/@tk-uno/live")
        tk_segundo = entrada("tiktok", "tk-dos", "https://tiktok.com/@tk-dos/live")
        on_conectar = mock.Mock()
        dialogo = self._dialogo(
            [yt_primero, yt_segundo, tk_primero, tk_segundo], on_conectar)

        dialogo._listas["youtube"].SetSelection(1)
        dialogo._listas["tiktok"].SetSelection(0)
        with mock.patch.object(dialogo, "EndModal"):
            dialogo._conectar()

        on_conectar.assert_called_once_with(url_youtube)

    def test_conectar_desde_pestana_tiktok_entrega_su_url(self):
        youtube = entrada("youtube", "solo-youtube", "https://youtube.com/solo-youtube")
        url_tiktok = "https://tiktok.com/solo-tiktok"
        tiktok = entrada("tiktok", "solo-tiktok", url_tiktok)
        on_conectar = mock.Mock()
        dialogo = self._dialogo([youtube, tiktok], on_conectar)

        with mock.patch.object(gui_historial, "anunciar"):
            dialogo.nb.SetSelection(1)
        with mock.patch.object(dialogo, "EndModal"):
            dialogo._conectar()

        on_conectar.assert_called_once_with(url_tiktok)

    def test_conectar_entrega_la_url_de_la_entrada_elegida(self):
        on_conectar = mock.Mock()
        url = "https://youtube.com/watch?v=elegida"
        datos = entrada("youtube", "elegida", url)
        self.ruta.write_text(json.dumps([datos]), encoding="utf-8")
        dialogo = gui_historial.HistorialDialog(None, self.ruta, on_conectar)
        self.addCleanup(destruir, dialogo)

        with mock.patch.object(dialogo, "EndModal"):
            dialogo._conectar()

        on_conectar.assert_called_once_with(url)

    def test_conectar_sin_seleccion_anuncia_y_no_llama(self):
        dialogo = self._dialogo([entrada("youtube", "yt", "https://youtube.com/watch?v=yt")])
        dialogo._listas["youtube"].SetSelection(gui_historial.wx.NOT_FOUND)

        with mock.patch.object(gui_historial, "anunciar") as anunciar:
            dialogo._conectar()

        dialogo._on_conectar.assert_not_called()
        anunciar.assert_called_once_with("Sin selección")

    def test_conectar_entrada_sin_enlace_anuncia_y_no_cierra(self):
        dialogo = self._dialogo([entrada("youtube", "sin-enlace", "")])

        with mock.patch.object(gui_historial, "anunciar") as anunciar, \
                mock.patch.object(dialogo, "EndModal") as end_modal:
            dialogo._conectar()

        anunciar.assert_called_once_with("Esta entrada no tiene enlace.")
        end_modal.assert_not_called()
        dialogo._on_conectar.assert_not_called()

    def test_intro_por_char_hook_conecta(self):
        dialogo = self._dialogo([
            entrada("youtube", "yt", "https://youtube.com/watch?v=yt")])
        lista = dialogo._listas["youtube"]
        lista.SetSelection(0)
        evento = gui_historial.wx.KeyEvent(gui_historial.wx.wxEVT_CHAR_HOOK)
        evento.KeyCode = gui_historial.wx.WXK_RETURN
        with mock.patch.object(dialogo, "_conectar") as conectar:
            lista.GetEventHandler().ProcessEvent(evento)
        conectar.assert_called_once_with()

    def test_el_doble_clic_conecta(self):
        dialogo = self._dialogo([
            entrada("youtube", "yt", "https://youtube.com/watch?v=yt")])
        lista = dialogo._listas["youtube"]
        evento = gui_historial.wx.CommandEvent(
            gui_historial.wx.EVT_LISTBOX_DCLICK.typeId, lista.GetId())
        evento.SetEventObject(lista)
        with mock.patch.object(dialogo, "_conectar") as conectar:
            lista.GetEventHandler().ProcessEvent(evento)
        conectar.assert_called_once_with()

    def test_quitar_elimina_guarda_y_anuncia(self):
        youtube = entrada("youtube", "yt", "https://youtube.com/watch?v=yt")
        tiktok = entrada("tiktok", "tk", "https://tiktok.com/@tk/live")
        dialogo = self._dialogo([youtube, tiktok])

        with mock.patch.object(gui_historial, "anunciar") as anunciar:
            dialogo._quitar()

        self.assertEqual(["No hay entradas de YouTube."],
                         list(dialogo._listas["youtube"].GetStrings()))
        self.assertEqual([tiktok], historial.cargar(self.ruta))
        anunciar.assert_called_once_with("Entrada eliminada del historial")

    def test_mide_760_por_540_y_la_lista_respira_dentro_de_la_pestana(self):
        dialogo = self._dialogo([])
        self.assertEqual(tuple(dialogo.GetSize()), (760, 540))
        for plat in ("youtube", "tiktok"):
            with self.subTest(plataforma=plat):
                lista = dialogo._listas[plat]
                sizer = lista.GetContainingSizer()
                self.assertIsNotNone(sizer)
                partida = sizer.GetItem(lista)
                self.assertTrue(partida.GetFlag() & gui_historial.wx.ALL)
                self.assertEqual(partida.GetBorder(), 8)

    def test_controles_tienen_los_nombres_accesibles_esperados(self):
        dialogo = self._dialogo([])
        controles = {
            "lista de YouTube": (dialogo._listas["youtube"], "Historial de YouTube"),
            "lista de TikTok": (dialogo._listas["tiktok"], "Historial de TikTok"),
            "botón Conectar": (dialogo.btn_conectar, "ConectarHistorial"),
            "botón Quitar": (dialogo.btn_quitar, "QuitarHistorial"),
        }

        for descripcion, (control, nombre) in controles.items():
            with self.subTest(control=descripcion):
                self.assertEqual(nombre, control.GetName())

    def test_instala_busqueda_por_tecleo_en_cada_lista(self):
        youtube = entrada("youtube", "yt", "https://youtube.com/watch?v=yt")
        tiktok = entrada("tiktok", "tk", "https://tiktok.com/@tk/live")
        with mock.patch.object(lista_acciones, "instalar_busqueda_tipo") as instalar:
            dialogo = self._dialogo([youtube, tiktok])

        llamadas = {llamada.args[0]: llamada.args[1]
                    for llamada in instalar.call_args_list}
        self.assertEqual(
            set(llamadas),
            {dialogo._listas["youtube"], dialogo._listas["tiktok"]})
        for lista, obtener_textos in llamadas.items():
            with self.subTest(lista=lista.GetName()):
                self.assertEqual(obtener_textos(),
                                 list(lista.GetStrings()))

    def test_no_queda_ningun_texto_visible_sin_envolver(self):
        with con_pseudo():
            dialogo = self._dialogo([])
            sin_marcar = textos_sin_marcar(
                dialogo, propios=("YouTube", "TikTok"))

        self.assertEqual([], sin_marcar)


class PruebasOrillaHistorial(unittest.TestCase):

    def setUp(self):
        self.app = app_de_prueba()
        self.temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)
        self.ruta = Path(self.temporal.name) / "historial.json"

    def _dialogo_dos_filas(self):
        primera = entrada("youtube", "primera", "https://youtube.com/watch?v=primera")
        segunda = entrada("youtube", "segunda", "https://youtube.com/watch?v=segunda")
        self.ruta.write_text(json.dumps([primera, segunda]), encoding="utf-8")
        dialogo = gui_historial.HistorialDialog(None, self.ruta, mock.Mock())
        self.addCleanup(destruir, dialogo)
        return dialogo

    def _pulsar(self, codigo, lista):
        evento = gui_historial.wx.KeyEvent(gui_historial.wx.wxEVT_KEY_DOWN)
        evento.SetKeyCode(codigo)
        lista.GetEventHandler().ProcessEvent(evento)

    def test_arriba_en_primera_fila_suena(self):
        dialogo = self._dialogo_dos_filas()
        lista = dialogo._listas["youtube"]
        lista.SetSelection(0)
        with mock.patch.object(lista_acciones._snd, "reproducir") as reproducir:
            self._pulsar(gui_historial.wx.WXK_UP, lista)
        reproducir.assert_called_once_with("orilla")

    def test_abajo_en_ultima_fila_suena(self):
        dialogo = self._dialogo_dos_filas()
        lista = dialogo._listas["youtube"]
        lista.SetSelection(1)
        with mock.patch.object(lista_acciones._snd, "reproducir") as reproducir:
            self._pulsar(gui_historial.wx.WXK_DOWN, lista)
        reproducir.assert_called_once_with("orilla")

    def test_arriba_en_segunda_fila_no_suena(self):
        dialogo = self._dialogo_dos_filas()
        lista = dialogo._listas["youtube"]
        lista.SetSelection(1)
        with mock.patch.object(lista_acciones._snd, "reproducir") as reproducir:
            self._pulsar(gui_historial.wx.WXK_UP, lista)
        reproducir.assert_not_called()

    def test_orilla_aplica_a_la_lista_que_genero_el_evento(self):
        dialogo = self._dialogo_dos_filas()
        youtube = dialogo._listas["youtube"]
        tiktok = dialogo._listas["tiktok"]
        youtube.SetSelection(1)
        with mock.patch.object(lista_acciones._snd, "reproducir") as reproducir:
            self._pulsar(gui_historial.wx.WXK_UP, tiktok)
        # La lista de TikTok está vacía: suena aunque YouTube esté en la fila 1.
        reproducir.assert_called_once_with("orilla")


if __name__ == "__main__":
    unittest.main()
