# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de la ventana de disparadores de evento, sin llamar a la app."""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import wx

from guyrapu.core import paths
from guyrapu.interaction import disparadores_guardados
from guyrapu.ui import disparador_cuadro, disparadores_ventana
from tests.rutas_temporales import redirigir_rutas
from tests.ventanas_prueba import app_de_prueba, destruir


def _datos(nombre="aplauso", **cambios):
    datos = {
        "nombre": nombre, "cuando": "evento", "evento": "superchat",
        "minimo": None, "medio": "aplauso.gif",
        "tarjeta": "", "estilo": "clasico", "segundos": 8,
        "permiso": "todos", "nombres": [], "espera_general": 5.0,
        "espera_persona": 30.0, "activo": True,
    }
    datos.update(cambios)
    return datos


def _de_evento(nombre="regalo", **cambios):
    return _datos(nombre, evento="superchat", minimo=5, **cambios)


class BaseVentana(unittest.TestCase):

    def setUp(self):
        self.app = app_de_prueba()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        parche = redirigir_rutas(self.tmp.name)
        parche.__enter__()
        self.addCleanup(parche.__exit__, None, None, None)

    def _panel(self, lista=None):
        if lista is not None:
            disparadores_guardados.guardar(paths.disparadores(), lista)
        marco = wx.Frame(None)
        self.addCleanup(destruir, marco)
        panel = disparadores_ventana.PanelDisparadores(marco)
        self.addCleanup(destruir, panel)
        return panel

    def _nombres_en_disco(self):
        return [disparador["nombre"]
                for disparador in disparadores_guardados.cargar(
                    paths.disparadores())]


class TestContratos(BaseVentana):

    def test_el_panel_lee_los_disparadores_al_abrir(self):
        panel = self._panel([
            _datos("aplauso"),
            _de_evento("regalo", tarjeta="Gracias")])
        self.assertEqual(panel.lista.GetCount(), 2)
        self.assertEqual(panel.lista.GetString(0),
                         "aplauso, cuando llega Super Chats y regalos")
        self.assertEqual(
            panel.lista.GetString(1),
            "regalo, cuando llega Super Chats y regalos desde 5")

    def test_la_lista_vacia_y_el_archivo_danado_dicen_que_hacer(self):
        panel = self._panel([])
        self.assertEqual(
            panel.lista.GetString(0),
            "No hay disparadores. Usa Agregar para crear uno.")
        paths.disparadores().write_text("{roto", encoding="utf-8")
        panel = self._panel()
        self.assertEqual(
            panel.lista.GetString(0),
            "No hay disparadores. Usa Agregar para crear uno.")

    def test_los_botones_del_panel_estan_encendidos(self):
        panel = self._panel([])
        botones = [hijo for hijo in panel.GetChildren()
                   if isinstance(hijo, wx.Button)]
        self.assertTrue(botones)
        self.assertTrue(all(boton.IsEnabled() for boton in botones))

    def test_sin_disparadores_las_acciones_dicen_por_que(self):
        panel = self._panel([])
        with mock.patch("guyrapu.ui.lista_acciones.anunciar") as decir:
            panel._lista.ejecutar("editar")
        decir.assert_called_once_with(
            "No hay disparadores. Usa Agregar para crear uno.")


class TestAcciones(BaseVentana):

    def test_tiene_las_acciones_con_sus_teclas(self):
        panel = self._panel([])
        self.assertEqual([(a.clave, a.tecla) for a in panel._acciones], [
            ("agregar", None), ("editar", "intro"), ("renombrar", "f2"),
            ("duplicar", "ctrl+d"), ("pausar", None), ("escuchar", None),
            ("eliminar", "suprimir"), ("exportar", None), ("importar", None)])
        sin_elemento = {a.clave for a in panel._acciones
                        if not a.necesita_elemento}
        self.assertEqual(sin_elemento, {"agregar", "exportar", "importar"})

    def test_los_rotulos_son_los_pedidos(self):
        panel = self._panel([])
        self.assertEqual(
            [a.etiqueta.replace("&", "") for a in panel._acciones],
            ["Agregar", "Editar", "Cambiar nombre", "Duplicar",
             "Pausar o reanudar", "Escuchar", "Eliminar", "Exportar",
             "Importar"])

    def test_cada_tecla_llega_a_su_accion(self):
        from guyrapu.ui import lista_acciones
        acciones = self._panel([])._acciones
        for codigo, modificadores, esperada in (
                (wx.WXK_RETURN, wx.MOD_NONE, "editar"),
                (wx.WXK_F2, wx.MOD_NONE, "renombrar"),
                (ord("D"), wx.MOD_CONTROL, "duplicar"),
                (wx.WXK_DELETE, wx.MOD_NONE, "eliminar")):
            with self.subTest(esperada=esperada):
                self.assertEqual(
                    lista_acciones.clave_de_tecla(
                        codigo, modificadores, acciones), esperada)

    def test_agregar_guarda_y_deja_el_foco_en_el_nuevo(self):
        panel = self._panel([_datos("A")])
        panel.GetTopLevelParent().Show()
        wx.Yield()
        datos = _datos("B", evento="cofre")
        with mock.patch.object(disparador_cuadro, "abrir",
                               return_value=datos), \
                mock.patch.object(disparadores_ventana, "anunciar") as decir:
            panel._agregar()
        self.assertEqual(self._nombres_en_disco(), ["A", "B"])
        self.assertEqual(panel.lista.GetSelection(), 1)
        self.assertIs(panel.lista, wx.Window.FindFocus())
        decir.assert_called_once_with("Disparador agregado")

    def test_editar_guarda_y_deja_el_foco_en_el_mismo(self):
        panel = self._panel([_datos("A"), _datos("B", evento="cofre")])
        panel.lista.SetSelection(1)
        datos = _datos("B", evento="cofre", tarjeta="Nueva")
        with mock.patch.object(disparador_cuadro, "abrir",
                               return_value=datos), \
                mock.patch.object(disparadores_ventana, "anunciar") as decir:
            panel._editar()
        self.assertEqual(
            disparadores_guardados.cargar(paths.disparadores())[1]["tarjeta"],
            "Nueva")
        self.assertEqual(panel.lista.GetSelection(), 1)
        decir.assert_called_once_with("Disparador guardado")

    def test_renombrar_repite_la_validacion(self):
        panel = self._panel([_datos("A"), _datos("B", evento="cofre")])
        panel.lista.SetSelection(0)
        with mock.patch.object(disparador_cuadro, "pedir_nombre",
                               side_effect=["B", "nuevo"]), \
                mock.patch.object(disparadores_ventana, "anunciar") as decir:
            panel._renombrar()
        self.assertEqual(self._nombres_en_disco(), ["nuevo", "B"])
        self.assertIn("B", decir.call_args_list[0].args[0])

    def test_duplicar_deja_la_copia_debajo(self):
        panel = self._panel([_datos("A"), _datos("B", evento="cofre")])
        panel.lista.SetSelection(0)
        with mock.patch.object(disparadores_ventana, "anunciar") as decir:
            panel._duplicar()
        self.assertEqual(self._nombres_en_disco(),
                         ["A", "A (copia)", "B"])
        self.assertEqual(panel.lista.GetSelection(), 1)
        decir.assert_called_once_with("Disparador duplicado")

    def test_pausar_cambia_el_estado_y_la_fila(self):
        panel = self._panel([_datos("A")])
        panel.lista.SetSelection(0)
        with mock.patch.object(disparadores_ventana, "anunciar") as decir:
            panel._pausar()
        self.assertFalse(
            disparadores_guardados.cargar(paths.disparadores())[0]["activo"])
        self.assertEqual(
            panel.lista.GetString(0),
            "A, cuando llega Super Chats y regalos, pausado")
        decir.assert_called_once_with("Pausado")

    def test_escuchar_anuncia_la_frase(self):
        panel = self._panel([_datos(
            "A", tarjeta="Gracias por el apoyo")])
        panel.lista.SetSelection(0)
        with mock.patch.object(disparadores_ventana, "anunciar") as decir:
            panel._escuchar()
        decir.assert_called_once_with(
            "A: cuando llega Super Chats y regalos, muestra el medio "
            "aplauso.gif y la tarjeta «Gracias por el apoyo».")

    def test_eliminar_pide_confirmacion_con_no_predeterminado(self):
        panel = self._panel([_datos("A"), _datos("B", evento="cofre")])
        panel.lista.SetSelection(0)
        with mock.patch.object(disparadores_ventana.confirmar, "preguntar",
                               return_value=True) as preguntar, \
                mock.patch.object(disparadores_ventana, "anunciar") as decir:
            panel._eliminar()
        self.assertFalse(preguntar.call_args.kwargs["predeterminado_si"])
        self.assertEqual(self._nombres_en_disco(), ["B"])
        self.assertEqual(panel.lista.GetSelection(), 0)
        decir.assert_called_once_with("Disparador eliminado")

    def test_eliminar_el_ultimo_deja_el_foco_en_el_anterior(self):
        panel = self._panel([_datos("A"), _datos("B", evento="cofre")])
        panel.lista.SetSelection(1)
        with mock.patch.object(disparadores_ventana.confirmar, "preguntar",
                               return_value=True), \
                mock.patch.object(disparadores_ventana, "anunciar"):
            panel._eliminar()
        self.assertEqual(panel.lista.GetSelection(), 0)

    def test_exportar_con_la_lista_vacia_no_abre_nada(self):
        panel = self._panel([])
        with mock.patch.object(panel, "_pedir_ruta") as pedir, \
                mock.patch.object(disparadores_ventana, "anunciar") as decir:
            panel._exportar()
        pedir.assert_not_called()
        decir.assert_called_once_with(
            "No hay disparadores para exportar.")

    def test_exportar_e_importar_pausan_lo_importado(self):
        panel = self._panel([_datos("A")])
        ruta = Path(self.tmp.name) / "salida.zip"
        with mock.patch.object(panel, "_pedir_ruta", return_value=ruta):
            panel._exportar()
        panel = self._panel([_datos("A")])
        with mock.patch.object(panel, "_pedir_ruta", return_value=ruta), \
                mock.patch.object(panel, "_preguntar_reemplazo",
                                  return_value=False), \
                mock.patch.object(disparadores_ventana, "anunciar"):
            panel._importar()
        importados = [
            disparador for disparador
            in disparadores_guardados.cargar(paths.disparadores())
            if disparador["nombre"] != "A"]
        self.assertEqual([disparador["activo"] for disparador in importados],
                         [False])


if __name__ == "__main__":
    unittest.main()
