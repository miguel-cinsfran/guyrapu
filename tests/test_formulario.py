# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Medidas de la pieza común y tamaño de los cuadros que la usan.

Abre ventanas.
"""

import tempfile
import unittest

import wx

from guyrapu.core import paths
from guyrapu.interaction import medios_guardados
from guyrapu.ui import (comando_cuadro, disparador_cuadro, encuesta_cuadro,
                        ensayo_ventana, estilo_cuadro, estilo_tipos_cuadro,
                        formulario, medio_cuadro, mensaje_automatico_cuadro,
                        meta_cuadro)
from guyrapu.ui.preferencias_comun import fila_label
from tests.rutas_temporales import redirigir_rutas
from tests.ventanas_prueba import app_de_prueba, destruir


class BaseMedidas(unittest.TestCase):
    def setUp(self):
        self.app = app_de_prueba()
        self.cuadro = wx.Frame(None)
        self.addCleanup(destruir, self.cuadro)
        self.panel = wx.Panel(self.cuadro)
        self.contenido = wx.BoxSizer(wx.VERTICAL)

    def _medir(self):
        formulario.ajustar_tamano(self.cuadro, self.panel, self.contenido)
        self.cuadro.Layout()
        self.cuadro.Show()
        self.addCleanup(self.cuadro.Hide)
        self.cuadro.SendSizeEvent()
        self.cuadro.Layout()

    def _fila(self, texto, control, sizer=None, **opciones):
        rotulo = fila_label(self.panel, texto)
        formulario.agregar_fila(sizer or self.contenido, rotulo, control,
                                **opciones)
        return rotulo, control

    def _caja(self):
        return next(hijo for hijo in self.panel.GetChildren()
                    if isinstance(hijo, wx.StaticBox))


class TestMedidas(BaseMedidas):

    def test_las_medidas_viven_en_la_pieza(self):
        self.assertEqual(formulario.MARGEN, 16)
        self.assertEqual(formulario.ETIQUETA_A_CONTROL, 4)
        self.assertEqual(formulario.CONTROL_A_ETIQUETA, 12)
        self.assertEqual(formulario.ANTES_DE_TITULO, 20)
        self.assertEqual(formulario.ANCHO_MINIMO, 440)
        self.assertEqual(formulario.ANCHO_COLUMNA, 300)
        self.assertEqual(formulario.ANCHO_NUMERICO, 96)
        self.assertEqual(formulario.ENTRE_CASILLAS, 8)
        self.assertEqual(formulario.ENTRE_BOTONES, 8)
        self.assertEqual(formulario.ANTES_DEL_PIE, 16)
        self.assertEqual(formulario.ALTO_MAXIMO, 728)

    def test_margen_y_huecos_de_una_fila_con_real_geometria(self):
        rotulo, campo = self._fila("&Uno:", wx.TextCtrl(self.panel))
        _, segundo = self._fila("&Dos:", wx.TextCtrl(self.panel))
        aceptar = wx.Button(self.panel, wx.ID_OK, "&Aceptar")
        cancelar = wx.Button(self.panel, wx.ID_CANCEL, "&Cancelar")
        formulario.agregar_pie(self.contenido, [aceptar, cancelar])
        self._medir()
        self.assertEqual(campo.GetPosition().x, 16)
        self.assertEqual(campo.GetPosition().y - (
            rotulo.GetPosition().y + rotulo.GetSize().height), 4)
        self.assertIsNotNone(segundo)
        self.assertEqual(segundo.GetPosition().x, 16)
        ancho = self.panel.GetClientSize().width
        self.assertEqual(ancho - segundo.GetPosition().x
                         - segundo.GetSize().width, 16)
        self.assertEqual(aceptar.GetPosition().y - (
            segundo.GetPosition().y + segundo.GetSize().height), 16)

    def test_el_titulo_de_seccion_separa_veinte_pixeles(self):
        columna = wx.BoxSizer(wx.VERTICAL)
        _, anterior = self._fila("&Uno:", wx.TextCtrl(self.panel),
                                 sizer=columna)
        formulario.agregar_seccion(columna, self.panel, "Sección")
        self.contenido.Add(columna, 0, wx.EXPAND)
        self._medir()
        caja = self._caja()
        self.assertEqual(caja.GetPosition().y - (
            anterior.GetPosition().y + anterior.GetSize().height), 20)

    def test_el_contenido_de_la_seccion_separa_ocho_pixeles_del_borde(self):
        columna = wx.BoxSizer(wx.VERTICAL)
        seccion = formulario.agregar_seccion(columna, self.panel, "Sección")
        rotulo, campo = self._fila("&Uno:", wx.TextCtrl(self.panel),
                                   sizer=seccion)
        self.contenido.Add(columna, 0, wx.EXPAND)
        self._medir()
        caja = self._caja()
        interior = columna.GetChildren()[0].GetSizer().GetChildren()[0]
        self.assertEqual(interior.GetBorder(), 8)
        self.assertEqual(interior.GetFlag() & (wx.TOP | wx.LEFT | wx.RIGHT),
                         wx.TOP | wx.LEFT | wx.RIGHT)
        # wx devuelve el par (vertical, horizontal) del borde de la caja.
        borde = caja.GetBordersForSizer()[1]
        self.assertEqual(
            rotulo.GetPosition().x - caja.GetPosition().x - borde, 8)
        self.assertEqual(caja.GetPosition().x + caja.GetSize().width - borde - (
            campo.GetPosition().x + campo.GetSize().width), 8)

    def test_agregar_seccion_con_caja_devuelve_el_interior_y_su_caja(self):
        columna = wx.BoxSizer(wx.VERTICAL)
        interior, caja_sizer = formulario.agregar_seccion_con_caja(
            columna, self.panel, "Destinos")
        self.assertIsInstance(caja_sizer, wx.StaticBoxSizer)
        self.assertEqual(caja_sizer.GetStaticBox().GetLabel(), "Destinos")
        self.assertIs(caja_sizer.GetChildren()[0].GetSizer(), interior)

    def test_el_campo_numerico_no_se_estira(self):
        _, numero = self._fila("&Número:", wx.SpinCtrl(
            self.panel, min=0, max=100, initial=1), numerico=True)
        self._medir()
        self.assertEqual(numero.GetSize().width, 96)

    def test_las_casillas_se_separan_ocho_pixeles(self):
        una = wx.CheckBox(self.panel, label="Una")
        otra = wx.CheckBox(self.panel, label="Otra")
        formulario.agregar_casillas(self.contenido, (una, otra))
        self._medir()
        self.assertEqual(otra.GetPosition().x - (
            una.GetPosition().x + una.GetSize().width), 8)

    def test_el_pie_es_igual_y_va_a_la_derecha(self):
        aceptar = wx.Button(self.panel, wx.ID_OK, "&Aceptar")
        cancelar = wx.Button(self.panel, wx.ID_CANCEL, "&Cancelar")
        formulario.agregar_pie(self.contenido, [aceptar, cancelar])
        self._medir()
        self.assertEqual(aceptar.GetSize().width, cancelar.GetSize().width)
        self.assertGreaterEqual(aceptar.GetSize().width, 96)
        self.assertEqual(cancelar.GetPosition().x - (
            aceptar.GetPosition().x + aceptar.GetSize().width), 8)
        ancho = self.panel.GetClientSize().width
        self.assertEqual(ancho - cancelar.GetPosition().x
                         - cancelar.GetSize().width, 16)

    def test_el_ancho_nunca_baja_del_minimo(self):
        self._medir()
        self.assertGreaterEqual(self.cuadro.GetSize().width,
                                formulario.ANCHO_MINIMO)

    def test_el_hueco_entre_dos_filas_va_arriba_de_la_segunda(self):
        _, primero = self._fila("&Uno:", wx.TextCtrl(self.panel))
        rotulo, _ = self._fila("&Dos:", wx.TextCtrl(self.panel))
        self._medir()
        self.assertEqual(
            rotulo.GetPosition().y - (
                primero.GetPosition().y + primero.GetSize().height),
            formulario.CONTROL_A_ETIQUETA)

    def test_la_primera_fila_de_un_sizer_vacio_no_tiene_hueco_arriba(self):
        rotulo, _ = self._fila("&Uno:", wx.TextCtrl(self.panel))
        self._medir()
        self.assertEqual(rotulo.GetPosition().y, formulario.MARGEN)

    def test_la_nota_separa_del_control_de_arriba(self):
        _, control = self._fila("&Uno:", wx.TextCtrl(self.panel))
        nota = wx.StaticText(self.panel, label="Ayuda")
        formulario.agregar_nota(self.contenido, nota)
        self._medir()
        self.assertEqual(
            nota.GetPosition().y - (
                control.GetPosition().y + control.GetSize().height),
            formulario.ETIQUETA_A_CONTROL)
        self.assertGreaterEqual(nota.GetSize().width,
                                self.panel.GetClientSize().width
                                - 2 * formulario.MARGEN)

    def test_el_contenido_de_la_seccion_tambien_separa_abajo(self):
        columna = wx.BoxSizer(wx.VERTICAL)
        seccion = formulario.agregar_seccion(columna, self.panel, "Sección")
        _, campo = self._fila("&Uno:", wx.TextCtrl(self.panel), sizer=seccion)
        self.contenido.Add(columna, 0, wx.EXPAND)
        self._medir()
        interior = columna.GetChildren()[0].GetSizer().GetChildren()[0]
        self.assertEqual(interior.GetFlag() & wx.BOTTOM, wx.BOTTOM)
        self.assertEqual(interior.GetBorder(), formulario.MARGEN_DE_SECCION)
        caja = self._caja()
        self.assertGreaterEqual(
            caja.GetPosition().y + caja.GetSize().height - (
                campo.GetPosition().y + campo.GetSize().height),
            formulario.MARGEN_DE_SECCION)

    def test_el_marco_no_pasa_del_alto_maximo(self):
        self.contenido.Add((-1, 1000), 0, wx.EXPAND)
        self._medir()
        self.assertLessEqual(self.cuadro.GetSize().height,
                             formulario.ALTO_MAXIMO)


class BaseCuadros(unittest.TestCase):
    def setUp(self):
        self.app = app_de_prueba()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        parche = redirigir_rutas(self.tmp.name)
        parche.__enter__()
        self.addCleanup(parche.__exit__, None, None, None)
        medios_guardados.guardar(paths.medios(), [{
            "nombre": "aplauso.gif", "tipo": "imagen",
            "archivo": "aplauso.gif"}])

    def _comprobar(self, cuadro):
        self.addCleanup(destruir, cuadro)
        ancho, alto = cuadro.GetSize()
        self.assertGreaterEqual(ancho, formulario.ANCHO_MINIMO)
        self.assertLessEqual(ancho, 1366)
        self.assertLessEqual(alto, formulario.ALTO_MAXIMO)


class TestCuadros(BaseCuadros):

    def test_el_cuadro_del_comando_cabe(self):
        self._comprobar(comando_cuadro.DialogoComando(None, {}, ()))

    def test_el_cuadro_de_la_palabra_cabe(self):
        self._comprobar(comando_cuadro.DialogoPalabra(None, "hola"))

    def test_el_cuadro_del_mensaje_cabe(self):
        self._comprobar(mensaje_automatico_cuadro.DialogoMensaje(None, {}, ()))

    def test_el_cuadro_de_la_encuesta_cabe(self):
        self._comprobar(encuesta_cuadro.DialogoEncuesta(None, {}))

    def test_el_cuadro_del_estilo_cabe(self):
        self._comprobar(estilo_cuadro.DialogoEstilo(None, None, ()))

    def test_el_cuadro_de_los_tipos_cabe(self):
        self._comprobar(estilo_tipos_cuadro.DialogoTipos(None, set()))

    def test_el_cuadro_del_medio_cabe(self):
        self._comprobar(medio_cuadro.DialogoMedio(None, {}))

    def test_el_cuadro_de_la_meta_cabe(self):
        self._comprobar(meta_cuadro.DialogoMeta(None, {}, ()))

    def test_el_cuadro_del_nombre_cabe(self):
        self._comprobar(meta_cuadro.DialogoNombre(None, "hola"))

    def test_el_cuadro_del_disparador_cabe(self):
        self._comprobar(disparador_cuadro.DialogoDisparador(None, {}, ()))

    def test_la_ventana_de_ensayo_cabe(self):
        marco = wx.Frame(None)
        self.addCleanup(destruir, marco)
        self._comprobar(ensayo_ventana.VentanaEnsayo(marco))


if __name__ == "__main__":
    unittest.main()
