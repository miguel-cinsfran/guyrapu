# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas puras del editor de listas y `guardar_lista`.

No abren ventanas: comprueban la validación del nombre, qué hace cada tecla
y el guardado en un directorio temporal.
"""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from guyrapu.music import listas
from guyrapu.music.listas import ErrorListas
from guyrapu.music.modelo import Tema
from guyrapu.ui.musica_listas_propias import ListasPropiasMusica
from tests.ventanas_prueba import app_de_prueba

try:
    import wx
    from guyrapu.ui import musica_editor_lista
    from tests.pseudo_prueba import con_pseudo, textos_sin_marcar
    from tests.ventanas_prueba import destruir
    _HAY_WX = True
except Exception:
    wx = None
    musica_editor_lista = None
    _HAY_WX = False


@unittest.skipUnless(_HAY_WX, "wxPython no está instalado")
class TestValidarNombre(unittest.TestCase):

    def test_recorta_y_devuelve(self):
        self.assertEqual(
            musica_editor_lista.validar_nombre("  Favoritas "), "Favoritas")

    def test_vacio_lanza(self):
        with self.assertRaises(ErrorListas):
            musica_editor_lista.validar_nombre("   ")

    def test_prohibido_lanza(self):
        with self.assertRaises(ErrorListas):
            musica_editor_lista.validar_nombre("a/b")

    def test_mas_largo_que_sesenta_lanza(self):
        with self.assertRaises(ErrorListas) as exc:
            musica_editor_lista.validar_nombre("x" * 61)
        self.assertIn("más de 60", str(exc.exception))

    def test_sesenta_exactos_sirven(self):
        self.assertEqual(
            musica_editor_lista.validar_nombre("x" * 60), "x" * 60)


@unittest.skipUnless(_HAY_WX, "wxPython no está instalado")
class TestAccionTecla(unittest.TestCase):

    def test_enter_en_todas_lo_resuelve_la_pieza(self):
        for codigo in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            with self.subTest(codigo=codigo):
                self.assertIsNone(
                    musica_editor_lista.accion_tecla(codigo, "todas"))

    def test_enter_fuera_de_las_listas_sigue_su_camino(self):
        for codigo in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            with self.subTest(codigo=codigo):
                self.assertIsNone(
                    musica_editor_lista.accion_tecla(codigo, None))

    def test_espacio_en_todas_lo_maneja_el_control(self):
        self.assertIsNone(
            musica_editor_lista.accion_tecla(wx.WXK_SPACE, "todas"))

    def test_escape_cancela_aunque_no_este_en_una_lista(self):
        self.assertEqual(
            musica_editor_lista.accion_tecla(wx.WXK_ESCAPE, None),
            musica_editor_lista.ACCION_CANCELAR)

    def test_otra_tecla_sigue_su_camino(self):
        self.assertIsNone(
            musica_editor_lista.accion_tecla(wx.WXK_DOWN, "lista"))


class _ControlGuardar(ListasPropiasMusica):
    """Doble mínimo: carpeta temporal y avisos en memoria."""

    def __init__(self, carpeta):
        self._carpeta = carpeta
        self.avisos = []

    def carpeta_listas(self):
        return self._carpeta

    def _avisar(self, texto):
        self.avisos.append(texto)


class TestGuardarLista(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.raiz = Path(self.tmp.name)
        self.carpeta = self.raiz / "listas"
        self.a = self._mp3("a")
        self.tema_a = Tema(self.a, "A")

    def tearDown(self):
        self.tmp.cleanup()

    def _mp3(self, nombre):
        ruta = self.raiz / f"{nombre}.mp3"
        ruta.write_bytes(b"x")
        return str(ruta.resolve())

    def test_crea_la_lista_y_escribe_los_temas(self):
        control = _ControlGuardar(self.carpeta)
        control.guardar_lista("Nueva", [self.tema_a])
        temas, _ = listas.cargar(self.carpeta, "Nueva")
        self.assertEqual([t.titulo for t in temas], ["A"])

    def test_crear_con_nombre_existente_no_pisa(self):
        listas.crear(self.carpeta, "Nueva")
        control = _ControlGuardar(self.carpeta)
        control.guardar_lista("nueva", [self.tema_a])
        temas, _ = listas.cargar(self.carpeta, "Nueva")
        self.assertEqual(temas, ())
        self.assertTrue(any("Ya hay una lista con ese nombre" in a.texto
                            for a in control.avisos))

    def test_edita_y_renombra(self):
        listas.crear(self.carpeta, "Vieja")
        control = _ControlGuardar(self.carpeta)
        control.guardar_lista("Nueva", [self.tema_a], "Vieja")
        self.assertEqual(listas.nombres(self.carpeta), ["Nueva"])
        temas, _ = listas.cargar(self.carpeta, "Nueva")
        self.assertEqual([t.titulo for t in temas], ["A"])

    def test_edita_sin_cambiar_el_nombre(self):
        listas.crear(self.carpeta, "Vieja")
        control = _ControlGuardar(self.carpeta)
        control.guardar_lista("Vieja", [self.tema_a], "Vieja")
        temas, _ = listas.cargar(self.carpeta, "Vieja")
        self.assertEqual([t.titulo for t in temas], ["A"])


@unittest.skipUnless(_HAY_WX, "wxPython no está instalado")
class TestEditorPseudo(unittest.TestCase):
    """Ningún texto visible del editor sin pasar por gettext."""

    def setUp(self):
        self.app = app_de_prueba()
        self.dialogo = None

    def tearDown(self):
        if self.dialogo is not None:
            destruir(self.dialogo)

    def test_no_queda_ningun_texto_visible_sin_envolver(self):
        with con_pseudo():
            self.dialogo = musica_editor_lista.DialogoEditorLista(
                None, "Mía",
                (Tema("C:/Musica/rock.mp3", "Rock", artista="Ana"),), ())
            sin_marcar = textos_sin_marcar(
                self.dialogo, propios=("Mía", "Rock", "Ana"))
        self.assertEqual([], sin_marcar)

    def test_el_nombre_largo_se_anuncia_marcado(self):
        with con_pseudo():
            self.dialogo = musica_editor_lista.DialogoEditorLista(None)
            self.dialogo.txt_nombre.SetValue("x" * 61)
            with mock.patch.object(
                    musica_editor_lista, "anunciar") as anunciar:
                self.dialogo._guardar()
        anunciar.assert_called_once_with(
            "[¡El nombre no puede tener más de 60 caracteres!]")


TEXTO_LISTA_VACIA = (
    "La lista no tiene canciones. "
    "Marca las casillas de Todas las canciones para agregarlas.")
A = Tema("C:/Musica/a.mp3", "A")
B = Tema("C:/Musica/b.mp3", "B")


@unittest.skipUnless(_HAY_WX, "wxPython no está instalado")
class TestListaConLaPieza(unittest.TestCase):
    """«Canciones de la lista» con la pieza común: vacío, menú y teclas."""

    def setUp(self):
        self.app = app_de_prueba()
        self.dialogo = None

    def tearDown(self):
        if self.dialogo is not None:
            destruir(self.dialogo)

    def _abrir(self, lista=(), reproducir=None):
        self.dialogo = musica_editor_lista.DialogoEditorLista(
            None, "Lista", (A, B), tuple(lista), reproducir=reproducir)
        wx.Yield()
        return self.dialogo

    def _menu(self):
        menu = self.dialogo._lista_acciones._construir_menu()
        self.addCleanup(menu.Destroy)
        return menu

    def _pulsar(self, codigo, tipo=None):
        evento = wx.KeyEvent(tipo or wx.wxEVT_KEY_DOWN)
        evento.KeyCode = codigo
        self.dialogo.lb_lista.GetEventHandler().ProcessEvent(evento)

    def test_vacia_dice_que_marcar_las_casillas(self):
        dialogo = self._abrir(lista=())
        self.assertEqual(dialogo.lb_lista.GetItemCount(), 1)
        self.assertEqual(dialogo.lb_lista.GetItemText(0), TEXTO_LISTA_VACIA)
        self.assertIsNone(dialogo._lista_acciones.indice())

    def test_el_menu_tiene_las_cuatro_acciones_en_orden_y_encendidas(self):
        self._abrir(lista=(A,))
        items = self._menu().GetMenuItems()
        self.assertEqual(
            [item.GetItemLabel() for item in items],
            ["&Reproducir\tEnter", "&Eliminar\tDel",
             "&Subir\tAlt+Up", "&Bajar\tAlt+Down"])
        self.assertTrue(all(item.IsEnabled() for item in items))

    def test_el_menu_sin_fila_se_abre_con_las_acciones_apagadas(self):
        self._abrir(lista=())
        items = self._menu().GetMenuItems()
        self.assertEqual(len(items), 4)
        self.assertFalse(any(item.IsEnabled() for item in items))

    def test_intro_con_la_lista_vacia_no_reproduce(self):
        reproducir = mock.Mock()
        dialogo = self._abrir(lista=(), reproducir=reproducir)
        self.assertEqual(dialogo.lb_lista.GetItemText(0), TEXTO_LISTA_VACIA)
        dialogo.lb_lista.SetFocus()
        self._pulsar(wx.WXK_RETURN, wx.wxEVT_CHAR_HOOK)
        reproducir.assert_not_called()
        self.assertEqual(dialogo._lista.temas, ())


if __name__ == "__main__":
    unittest.main()
