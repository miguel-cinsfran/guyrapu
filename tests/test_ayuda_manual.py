# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""F1 abre el manual en la sección de la ventana."""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

try:
    import wx
    _HAY_WX = True
except Exception:
    _HAY_WX = False

from guyrapu.core import paths
from guyrapu.ui import ayuda_manual, gui_menu
from guyrapu.ui import gui_elegir_destino as elegir
from tests.ventanas_prueba import app_de_prueba, destruir

RAIZ = Path(__file__).resolve().parent.parent


class TestAnclas(unittest.TestCase):

    def test_p2_las_anclas_van_escritas_en_los_dos_manuales(self):
        for idioma in ("es", "en"):
            manual = (RAIZ / "docs" / idioma / "MANUAL.md").read_text(
                encoding="utf-8")
            lineas = manual.splitlines()
            for ancla in ayuda_manual.ANCLAS.values():
                with self.subTest(idioma=idioma, ancla=ancla):
                    self.assertTrue(
                        any(linea.startswith("#")
                            and f'<a id="{ancla}"></a>' in linea
                            for linea in lineas), ancla)

    def test_p4_cada_ancla_del_registro_existe_en_los_dos_html(self):
        for idioma in ("es", "en"):
            manual = (RAIZ / "docs" / idioma / "MANUAL.html").read_text(
                encoding="utf-8")
            lineas = manual.splitlines()
            for clave, ancla in ayuda_manual.ANCLAS.items():
                with self.subTest(ventana=clave, idioma=idioma):
                    self.assertTrue(
                        any(linea.startswith(("<h2", "<h3"))
                            and f'<a id="{ancla}"></a>' in linea
                            for linea in lineas), ancla)

    def test_p5_las_ventanas_fuera_de_la_lista_no_tienen_ancla(self):
        for clave in ("encuadre", "mensajes_automaticos"):
            self.assertNotIn(clave, ayuda_manual.ANCLAS)


class TestAbrirDocumento(unittest.TestCase):

    def _instalacion(self, tmp):
        instalacion = Path(tmp) / "app"
        manual = instalacion / "docs" / "es" / "MANUAL.html"
        manual.parent.mkdir(parents=True)
        manual.write_text(
            '<h2 id="panel-obs">Panel de OBS</h2>', encoding="utf-8")
        return instalacion, manual

    def test_la_pagina_de_redireccion_lleva_la_ruta_y_el_ancla(self):
        with tempfile.TemporaryDirectory() as tmp:
            instalacion, manual = self._instalacion(tmp)
            pagina = Path(tmp) / "redirige.html"
            with mock.patch.object(paths, "carpeta_instalacion",
                                   return_value=instalacion), \
                    mock.patch.object(gui_menu, "idioma_actual",
                                      return_value="es"), \
                    mock.patch.object(paths, "pagina_redireccion",
                                      return_value=pagina), \
                    mock.patch.object(gui_menu.confirmar, "avisar") as cuadro, \
                    mock.patch.object(gui_menu.os, "startfile") as abrir:
                gui_menu.abrir_documento_paquete(
                    None, "MANUAL", "Manual de uso", "panel-obs")
            abrir.assert_called_once_with(str(pagina))
            cuadro.assert_not_called()
            texto = pagina.read_text(encoding="utf-8")
            self.assertIn(manual.as_uri(), texto)
            self.assertIn("#panel-obs", texto)

    def test_p5_sin_ancla_abre_el_manual_al_principio(self):
        with tempfile.TemporaryDirectory() as tmp:
            instalacion, manual = self._instalacion(tmp)
            with mock.patch.object(paths, "carpeta_instalacion",
                                   return_value=instalacion), \
                    mock.patch.object(gui_menu, "idioma_actual",
                                      return_value="es"), \
                    mock.patch.object(paths, "pagina_redireccion") as pagina, \
                    mock.patch.object(gui_menu.os, "startfile") as abrir:
                gui_menu.abrir_documento_paquete(
                    None, "MANUAL", "Manual de uso")
            abrir.assert_called_once_with(str(manual))
            pagina.assert_not_called()


@unittest.skipUnless(_HAY_WX, "wxPython no está instalado")
class TestF1EnUnaVentana(unittest.TestCase):
    """El cableado de una ventana real: F1 abre el manual en su sección."""

    def setUp(self):
        self.app = app_de_prueba()
        parche = mock.patch.object(
            elegir.ganchos, "cargar_perfiles", return_value=[])
        parche.start()
        self.addCleanup(parche.stop)

    def _dialogo(self):
        dialogo = elegir.DialogoElegirDestino(None, "YouTube", "")
        self.addCleanup(destruir, dialogo)
        return dialogo

    def _abrir_con(self, dialogo, pagina):
        evento = mock.Mock()
        evento.GetKeyCode.return_value = wx.WXK_F1
        with mock.patch.object(paths, "pagina_redireccion",
                               return_value=pagina), \
                mock.patch.object(gui_menu, "idioma_actual",
                                  return_value="es"), \
                mock.patch.object(gui_menu.confirmar, "avisar") as cuadro, \
                mock.patch.object(gui_menu.os, "startfile") as abrir:
            dialogo._al_tecla(evento)
        return abrir, cuadro

    def test_p1_f1_abre_el_manual_en_la_seccion_de_la_ventana(self):
        with tempfile.TemporaryDirectory() as tmp:
            pagina = Path(tmp) / "redirige.html"
            abrir, cuadro = self._abrir_con(self._dialogo(), pagina)
            abrir.assert_called_once_with(str(pagina))
            cuadro.assert_not_called()
            texto = pagina.read_text(encoding="utf-8")
        self.assertIn("#transmitir", texto)

    def test_p3_el_ancla_sale_del_registro(self):
        with tempfile.TemporaryDirectory() as tmp:
            pagina = Path(tmp) / "redirige.html"
            with mock.patch.dict(
                    ayuda_manual.ANCLAS, {"transmitir": "otra-seccion"}):
                _, cuadro = self._abrir_con(self._dialogo(), pagina)
            cuadro.assert_not_called()
            self.assertIn("#otra-seccion", pagina.read_text(encoding="utf-8"))
