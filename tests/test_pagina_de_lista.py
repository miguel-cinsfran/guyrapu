# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""El armado común de las páginas de lista de Interacción.

Abre controles de wx.
"""

import tempfile
import unittest
from unittest import mock

import wx

from guyrapu.ui import (
    botonera, comandos_ventana, formulario, medios_ventana,
    mensajes_automaticos_ventana, pagina_de_lista)
from tests.rutas_temporales import redirigir_rutas
from tests.ventanas_prueba import app_de_prueba, destruir


def _hueco(arriba, abajo):
    """Píxeles entre el borde inferior de un control y el superior del otro."""
    return (abajo.GetPosition().y - arriba.GetPosition().y
            - arriba.GetSize().height)


class PaginaDeListaTest(unittest.TestCase):
    """El ritmo de los cuadros, medido en el sizer armado."""

    def setUp(self):
        app_de_prueba()
        self.marco = wx.Frame(None)
        self.addCleanup(destruir, self.marco)

    def _armar(self, **cambios):
        sizer = wx.BoxSizer(wx.VERTICAL)
        rotulo = wx.StaticText(self.marco, label="Lista:")
        lista = wx.ListBox(self.marco)
        fila = wx.BoxSizer(wx.HORIZONTAL)
        fila.Add(wx.Button(self.marco, label="Agregar"), 0)
        pagina_de_lista.agregar_lista(sizer, rotulo, lista, **cambios)
        pagina_de_lista.agregar_botones(sizer, fila)
        return sizer, rotulo, lista, fila

    def test_cada_control_va_con_el_ritmo_de_formulario(self):
        sizer, rotulo, lista, fila = self._armar()
        items = sizer.GetChildren()
        self.assertEqual(len(items), 6)
        self.assertIs(items[0].GetWindow(), rotulo)
        self.assertIs(items[2].GetWindow(), lista)
        self.assertIs(items[4].GetSizer(), fila)
        self.assertEqual(
            (items[0].GetProportion(), items[0].GetFlag(),
             items[0].GetBorder()),
            (0, wx.LEFT | wx.RIGHT | wx.TOP, formulario.MARGEN))
        self.assertEqual(items[1].GetSpacer().GetHeight(),
                         formulario.ETIQUETA_A_CONTROL)
        self.assertEqual(
            (items[2].GetProportion(), items[2].GetFlag(),
             items[2].GetBorder()),
            (1, wx.EXPAND | wx.LEFT | wx.RIGHT, formulario.MARGEN))
        self.assertEqual(items[3].GetSpacer().GetHeight(),
                         formulario.CONTROL_A_ETIQUETA)
        self.assertEqual(
            (items[4].GetProportion(), items[4].GetFlag(),
             items[4].GetBorder()),
            (0, wx.EXPAND | wx.LEFT | wx.RIGHT, formulario.MARGEN))
        self.assertEqual(items[5].GetSpacer().GetHeight(),
                         formulario.MARGEN - botonera.HUECO)

    def test_el_rotulo_puede_irse_sin_borde_superior(self):
        sizer, _rotulo, _lista, _fila = self._armar(borde_superior=False)
        items = sizer.GetChildren()
        self.assertEqual(
            (items[0].GetFlag(), items[0].GetBorder()),
            (wx.LEFT | wx.RIGHT, formulario.MARGEN))
        self.assertEqual(items[2].GetFlag(),
                         wx.EXPAND | wx.LEFT | wx.RIGHT)

    def test_una_pagina_real_respeta_los_huecos_entre_controles(self):
        with tempfile.TemporaryDirectory() as carpeta:
            with redirigir_rutas(carpeta):
                panel = comandos_ventana.PanelComandos(self.marco)
                self.addCleanup(destruir, panel)
                panel.SetSize((600, 500))
                panel.Layout()
                items = panel.GetSizer().GetChildren()
                rotulo = items[0].GetWindow()
                lista = items[2].GetWindow()
                fila = items[4].GetSizer()
                boton = fila.GetItem(0).GetWindow()
                ultimo = fila.GetChildren()[-1].GetWindow()
                self.assertEqual(_hueco(rotulo, lista),
                                 formulario.ETIQUETA_A_CONTROL)
                self.assertEqual(
                    _hueco(lista, boton), formulario.CONTROL_A_ETIQUETA)
                self.assertEqual(rotulo.GetPosition().x, formulario.MARGEN)
                self.assertEqual(lista.GetPosition().x, formulario.MARGEN)
                self.assertEqual(boton.GetPosition().x, formulario.MARGEN)
                self.assertEqual(
                    panel.GetClientSize().height - ultimo.GetPosition().y
                    - ultimo.GetSize().height, formulario.MARGEN)

    def test_mensajes_usa_el_mismo_ritmo_arriba_de_la_lista(self):
        self.marco._config = {"programados_activo": False}
        self.marco.mi_programados_activo = mock.Mock()
        self.marco.programador = mock.Mock()
        with tempfile.TemporaryDirectory() as carpeta:
            with redirigir_rutas(carpeta):
                panel = mensajes_automaticos_ventana.PanelMensajesAutomaticos(
                    self.marco, self.marco)
                self.addCleanup(destruir, panel)
                panel.SetSize((600, 500))
                panel.Layout()
                items = panel.GetSizer().GetChildren()
                nota = items[0].GetWindow()
                casilla = items[2].GetWindow()
                rotulo = items[4].GetWindow()
                self.assertEqual(nota.GetPosition().y, formulario.MARGEN)
                self.assertEqual(_hueco(nota, casilla),
                                 formulario.CONTROL_A_ETIQUETA)
                self.assertEqual(_hueco(casilla, rotulo),
                                 formulario.CONTROL_A_ETIQUETA)

    def test_medios_usa_el_mismo_ritmo_alrededor_del_volumen(self):
        with tempfile.TemporaryDirectory() as carpeta:
            with redirigir_rutas(carpeta):
                panel = medios_ventana.PanelMedios(self.marco)
                self.addCleanup(destruir, panel)
                panel.SetSize((600, 500))
                panel.Layout()
                items = panel.GetSizer().GetChildren()
                lista = items[2].GetWindow()
                rotulo = items[4].GetWindow()
                deslizador = items[6].GetWindow()
                self.assertEqual(_hueco(lista, rotulo),
                                 formulario.CONTROL_A_ETIQUETA)
                self.assertEqual(_hueco(rotulo, deslizador),
                                 formulario.ETIQUETA_A_CONTROL)


if __name__ == "__main__":
    unittest.main()
