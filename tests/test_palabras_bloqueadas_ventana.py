# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Página de palabras bloqueadas: lista, acciones, cuadro y archivo.

Abre ventanas.
"""

import tempfile
import unittest
from unittest import mock

import wx

from guyrapu.core import paths
from guyrapu.interaction import filtro_publico
from guyrapu.ui import palabras_bloqueadas_ventana
from guyrapu.ui.lista_acciones import clave_de_tecla
from tests.rutas_temporales import redirigir_rutas
from tests.ventanas_prueba import app_de_prueba, destruir


class BaseVentana(unittest.TestCase):
    def setUp(self):
        self.app = app_de_prueba()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        parche = redirigir_rutas(self.tmp.name)
        parche.__enter__()
        self.addCleanup(parche.__exit__, None, None, None)

    def _panel(self, palabras=None):
        if palabras is not None:
            filtro_publico.guardar(paths.palabras_bloqueadas(), palabras)
        marco = wx.Frame(None)
        self.addCleanup(destruir, marco)
        panel = palabras_bloqueadas_ventana.PanelPalabrasBloqueadas(marco)
        self.addCleanup(destruir, panel)
        return panel

    def _en_disco(self):
        return filtro_publico.cargar(paths.palabras_bloqueadas())

    def _pedir(self, *valores):
        return mock.patch.object(
            palabras_bloqueadas_ventana, "pedir_palabra",
            side_effect=valores)


class TestLista(BaseVentana):

    def test_p4_la_lista_tiene_su_nombre_accesible(self):
        panel = self._panel([])
        self.assertEqual(panel.lista.GetName(), "Palabras bloqueadas")

    def test_p4_vacia_dice_que_hacer(self):
        panel = self._panel([])
        self.assertEqual(panel.lista.GetCount(), 1)
        self.assertEqual(
            panel.lista.GetString(0),
            "No hay palabras bloqueadas. Aquí aparecen las palabras que se "
            "tapan en lo que el público escribe y se muestra en el vídeo. "
            "Usa Agregar para escribir una.")

    def test_p4_muestra_las_palabras_guardadas(self):
        panel = self._panel(["tonto", "mala palabra"])
        self.assertEqual(
            [panel.lista.GetString(indice)
             for indice in range(panel.lista.GetCount())],
            ["tonto", "mala palabra"])

    def test_p4_los_botones_nunca_se_deshabilitan(self):
        panel = self._panel([])
        botones = [hijo for hijo in panel.GetChildren()
                   if isinstance(hijo, wx.Button)]
        self.assertEqual([boton.GetLabel() for boton in botones],
                         ["A&gregar", "&Editar", "E&liminar"])
        self.assertTrue(all(boton.IsEnabled() for boton in botones))

    def test_p4_sin_elemento_las_acciones_dicen_por_que(self):
        panel = self._panel([])
        with mock.patch(
                "guyrapu.ui.lista_acciones.anunciar") as decir:
            panel._lista.ejecutar("editar")
        decir.assert_called_once_with(
            "No hay palabras bloqueadas. Aquí aparecen las palabras que se "
            "tapan en lo que el público escribe y se muestra en el vídeo. "
            "Usa Agregar para escribir una.")

    def test_p4_las_teclas_llegan_a_sus_acciones(self):
        panel = self._panel([])
        self.assertEqual(
            [(accion.clave, accion.tecla) for accion in panel._acciones],
            [("agregar", None), ("editar", "intro"),
             ("eliminar", "suprimir")])
        for codigo, esperada in ((wx.WXK_RETURN, "editar"),
                                 (wx.WXK_F2, None),
                                 (wx.WXK_DELETE, "eliminar")):
            with self.subTest(tecla=esperada):
                self.assertEqual(
                    clave_de_tecla(codigo, wx.MOD_NONE, panel._acciones),
                    esperada)


class TestCuadro(BaseVentana):

    def test_p5_pide_la_palabra_o_frase(self):
        class Dialogo:
            def __init__(self, padre, mensaje, titulo, value="") -> None:
                self.mensaje = mensaje
                self.titulo = titulo
                self.value = value

            def ShowModal(self):
                return wx.ID_OK

            def GetValue(self):
                return "tonto"

            def Destroy(self):
                pass

        creados = []

        def fabrica(*args, **kwargs):
            creados.append(Dialogo(*args, **kwargs))
            return creados[-1]

        with mock.patch.object(
                palabras_bloqueadas_ventana.wx, "TextEntryDialog",
                fabrica):
            self.assertEqual(
                palabras_bloqueadas_ventana.pedir_palabra(None), "tonto")
        self.assertEqual(creados[0].mensaje, "Palabra o frase:")


class TestAgregarYEditar(BaseVentana):

    def test_p5_agregar_guarda_y_deja_el_foco_en_la_entrada(self):
        panel = self._panel([])
        with self._pedir("tonto"), \
                mock.patch.object(palabras_bloqueadas_ventana,
                                  "anunciar") as decir, \
                mock.patch.object(panel.lista, "SetFocus") as foco:
            panel._agregar()
        self.assertEqual(self._en_disco(), ["tonto"])
        self.assertEqual(panel.lista.GetSelection(), 0)
        foco.assert_called_once_with()
        decir.assert_called_once_with("Palabra agregada")

    def test_p5_vacia_no_se_guarda_y_se_dice_por_que(self):
        panel = self._panel([])
        with self._pedir("   ", None), \
                mock.patch.object(palabras_bloqueadas_ventana,
                                  "anunciar") as decir:
            panel._agregar()
        self.assertEqual(self._en_disco(), [])
        decir.assert_called_once_with("Escribe una palabra o frase.")

    def test_p5_repetida_no_se_guarda_y_se_dice_por_que(self):
        panel = self._panel(["Tonto"])
        with self._pedir("tonto", None), \
                mock.patch.object(palabras_bloqueadas_ventana,
                                  "anunciar") as decir:
            panel._agregar()
        self.assertEqual(self._en_disco(), ["Tonto"])
        decir.assert_called_once_with("Esa palabra ya está en la lista.")

    def test_p5_editar_guarda_y_deja_el_foco_en_la_entrada(self):
        panel = self._panel(["tonto", "otro"])
        panel.lista.SetSelection(0)
        with self._pedir("nuevo"), \
                mock.patch.object(palabras_bloqueadas_ventana,
                                  "anunciar") as decir, \
                mock.patch.object(panel.lista, "SetFocus") as foco:
            panel._editar()
        self.assertEqual(self._en_disco(), ["nuevo", "otro"])
        self.assertEqual(panel.lista.GetSelection(), 0)
        foco.assert_called_once_with()
        decir.assert_called_once_with("Palabra guardada")

    def test_p5_editar_a_una_repetida_no_se_guarda(self):
        panel = self._panel(["tonto", "otro"])
        panel.lista.SetSelection(0)
        with self._pedir("OTRO", None), \
                mock.patch.object(palabras_bloqueadas_ventana,
                                  "anunciar") as decir:
            panel._editar()
        self.assertEqual(self._en_disco(), ["tonto", "otro"])
        decir.assert_called_once_with("Esa palabra ya está en la lista.")


class TestEliminar(BaseVentana):

    def test_p6_pide_confirmacion_con_no_de_fabrica(self):
        panel = self._panel(["tonto"])
        panel.lista.SetSelection(0)
        with mock.patch.object(
                palabras_bloqueadas_ventana.confirmar, "preguntar",
                return_value=True) as preguntar:
            panel._eliminar()
        self.assertFalse(preguntar.call_args.kwargs["predeterminado_si"])
        self.assertEqual(preguntar.call_args.args[1],
                         "¿Eliminar «tonto» de las palabras bloqueadas?")

    def test_p6_con_no_no_borra_nada(self):
        panel = self._panel(["tonto"])
        panel.lista.SetSelection(0)
        with mock.patch.object(
                palabras_bloqueadas_ventana.confirmar, "preguntar",
                return_value=False), \
                mock.patch.object(palabras_bloqueadas_ventana,
                                  "anunciar") as decir:
            panel._eliminar()
        self.assertEqual(self._en_disco(), ["tonto"])
        decir.assert_not_called()

    def test_p5_con_si_borra_y_deja_el_foco_en_la_siguiente(self):
        panel = self._panel(["uno", "dos", "tres"])
        panel.lista.SetSelection(1)
        with mock.patch.object(
                palabras_bloqueadas_ventana.confirmar, "preguntar",
                return_value=True), \
                mock.patch.object(palabras_bloqueadas_ventana,
                                  "anunciar") as decir, \
                mock.patch.object(panel.lista, "SetFocus") as foco:
            panel._eliminar()
        self.assertEqual(self._en_disco(), ["uno", "tres"])
        self.assertEqual(panel.lista.GetSelection(), 1)
        foco.assert_called_once_with()
        decir.assert_called_once_with("Palabra eliminada")

    def test_p5_al_borrar_la_ultima_deja_el_foco_en_la_anterior(self):
        panel = self._panel(["uno", "dos"])
        panel.lista.SetSelection(1)
        with mock.patch.object(
                palabras_bloqueadas_ventana.confirmar, "preguntar",
                return_value=True), \
                mock.patch.object(palabras_bloqueadas_ventana, "anunciar"):
            panel._eliminar()
        self.assertEqual(self._en_disco(), ["uno"])
        self.assertEqual(panel.lista.GetSelection(), 0)


if __name__ == "__main__":
    unittest.main()
