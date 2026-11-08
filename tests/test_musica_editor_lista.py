# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas puras del editor de listas, el submenú y `guardar_lista`.

No abren ventanas: comprueban la validación del nombre, qué hace cada tecla,
la forma del submenú y el guardado en un directorio temporal.
"""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from guyrapu.music import listas
from guyrapu.music.listas import ErrorListas
from guyrapu.music.modelo import Tema
from guyrapu.ui import musica_menus
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

    def test_enter_en_cualquiera_de_las_dos_listas_reproduce(self):
        for en_lista in ("lista", "todas"):
            for codigo in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
                with self.subTest(en_lista=en_lista, codigo=codigo):
                    self.assertEqual(
                        musica_editor_lista.accion_tecla(codigo, 0, en_lista),
                        musica_menus.ACCION_REPRODUCIR)

    def test_enter_fuera_de_las_listas_sigue_su_camino(self):
        for codigo in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            with self.subTest(codigo=codigo):
                self.assertIsNone(
                    musica_editor_lista.accion_tecla(codigo, 0, None))

    def test_espacio_en_todas_lo_maneja_el_control(self):
        self.assertIsNone(
            musica_editor_lista.accion_tecla(wx.WXK_SPACE, 0, "todas"))

    def test_supr_quita_solo_en_la_lista(self):
        for codigo in (wx.WXK_DELETE, wx.WXK_NUMPAD_DELETE):
            with self.subTest(codigo=codigo):
                self.assertEqual(
                    musica_editor_lista.accion_tecla(codigo, 0, "lista"),
                    musica_menus.ACCION_QUITAR)
        self.assertIsNone(
            musica_editor_lista.accion_tecla(wx.WXK_DELETE, 0, "todas"))
        self.assertIsNone(
            musica_editor_lista.accion_tecla(wx.WXK_DELETE, 0, None))

    def test_alt_flechas_mueven_solo_en_la_lista(self):
        self.assertEqual(
            musica_editor_lista.accion_tecla(
                wx.WXK_UP, wx.MOD_ALT, "lista"),
            musica_menus.ACCION_SUBIR)
        self.assertEqual(
            musica_editor_lista.accion_tecla(
                wx.WXK_DOWN, wx.MOD_ALT, "lista"),
            musica_menus.ACCION_BAJAR)
        self.assertIsNone(
            musica_editor_lista.accion_tecla(
                wx.WXK_UP, wx.MOD_ALT, "todas"))
        self.assertIsNone(
            musica_editor_lista.accion_tecla(wx.WXK_DOWN, 0, "lista"))

    def test_aplicaciones_y_mayus_f10_abren_el_menu_solo_en_la_lista(self):
        self.assertEqual(
            musica_editor_lista.accion_tecla(
                wx.WXK_WINDOWS_MENU, 0, "lista"),
            musica_editor_lista.ACCION_MENU)
        self.assertEqual(
            musica_editor_lista.accion_tecla(
                wx.WXK_F10, wx.MOD_SHIFT, "lista"),
            musica_editor_lista.ACCION_MENU)
        self.assertIsNone(
            musica_editor_lista.accion_tecla(
                wx.WXK_WINDOWS_MENU, 0, "todas"))

    def test_escape_cancela_aunque_no_este_en_una_lista(self):
        self.assertEqual(
            musica_editor_lista.accion_tecla(wx.WXK_ESCAPE, 0, None),
            musica_editor_lista.ACCION_CANCELAR)

    def test_otra_tecla_sigue_su_camino(self):
        self.assertIsNone(
            musica_editor_lista.accion_tecla(wx.WXK_DOWN, 0, "lista"))


class TestSubmenu(unittest.TestCase):

    def test_una_entrada_por_lista_y_la_nueva_al_final(self):
        entradas = musica_menus.entradas_agregar_a_lista(("Mía", "Otra"))
        self.assertEqual([e for e, _a in entradas],
                         ["Mía", "Otra", "&Nueva lista…"])
        self.assertEqual(
            entradas[0][1],
            (musica_menus.ACCION_AGREGAR_A_LISTA, "Mía"))
        self.assertEqual(entradas[-1][1],
                         musica_menus.ACCION_NUEVA_LISTA_CON_TEMA)

    def test_sin_listas_solo_la_nueva(self):
        entradas = musica_menus.entradas_agregar_a_lista(())
        self.assertEqual([e for e, _a in entradas], ["&Nueva lista…"])


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


if __name__ == "__main__":
    unittest.main()
