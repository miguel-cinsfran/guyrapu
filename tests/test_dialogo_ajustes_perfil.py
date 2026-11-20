# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas del cuadro con los ajustes de un perfil de OBS."""

import dataclasses
import unittest
from unittest import mock

import wx

from tests.ventanas_prueba import app_de_prueba, destruir
from guyrapu.core.idioma import _
from guyrapu.obs import ajustes_perfil
from guyrapu.obs import textos_perfil
from guyrapu.ui import formulario, paleta, tema
from guyrapu.ui.dialogo_ajustes_perfil import DialogoAjustesPerfil


def de_prueba(**cambios):
    base = ajustes_perfil.valores_iniciales(False, "nvenc")
    return dataclasses.replace(base, **cambios)


class BaseDialogo(unittest.TestCase):

    def setUp(self):
        self.app = app_de_prueba()

    def _dialogo(self, ajustes=None, **kwargs):
        dialogo = DialogoAjustesPerfil(
            None, ajustes or de_prueba(), "Prueba", **kwargs)
        self.addCleanup(destruir, dialogo)
        return dialogo


class TestIdaYVuelta(BaseDialogo):

    def test_devuelve_los_diez_y_siete_ajustes_sin_perder_ninguno(self):
        ajustes = de_prueba(
            ancho_lienzo=1600, alto_lienzo=900,
            ancho_salida=1280, alto_salida=720,
            fps=50, servidor="rtmp://servidor", clave="clave",
            codificador="nvenc", bitrate_video=4500, bitrate_audio=192,
            preset="p6", bitrate_dinamico=True, reconectar=False,
            espera_reconexion=10, reintentos=20,
            carpeta_grabacion="C:\\Grabaciones", formato_grabacion="mov",
            calidad_grabacion="HQ", buffer_clips=True, segundos_buffer=45,
            muestreo=44100, canales="Mono", monitoreo_id="{0.0.0.9}",
            monitoreo_nombre="Altavoces")
        dialogo = self._dialogo(
            ajustes, personalizado=True,
            salidas=(("default", "Por defecto"), ("{0.0.0.9}", "Altavoces")))
        resultado = dialogo.ajustes()
        for campo in dataclasses.fields(ajustes_perfil.AjustesPerfil):
            with self.subTest(campo=campo.name):
                self.assertEqual(getattr(resultado, campo.name),
                                 getattr(ajustes, campo.name))
        self.assertEqual(resultado, ajustes)

    def test_el_servidor_es_de_solo_lectura_si_no_es_personalizado(self):
        dialogo = self._dialogo(personalizado=False)
        self.assertFalse(dialogo.txt_servidor.IsEditable())

    def test_el_servidor_es_editable_si_es_personalizado(self):
        dialogo = self._dialogo(personalizado=True)
        self.assertTrue(dialogo.txt_servidor.IsEditable())


class TestPreset(BaseDialogo):

    def test_cambia_de_lista_con_el_codificador_y_elige_el_intermedio(self):
        dialogo = self._dialogo(de_prueba(codificador="x264",
                                          preset="veryfast"))
        dialogo.cho_codificador.SetValue("nvenc")
        dialogo._al_cambiar_codificador(None)
        self.assertEqual(len(dialogo.cho_preset.GetItems()), 7)
        self.assertEqual(dialogo.cho_preset.GetValue(), "p4")
        dialogo.cho_codificador.SetValue("qsv")
        dialogo._al_cambiar_codificador(None)
        self.assertEqual(len(dialogo.cho_preset.GetItems()), 3)
        self.assertEqual(dialogo.cho_preset.GetValue(), "balanced")
        self.assertEqual(
            [etiqueta for _valor, etiqueta
             in textos_perfil.opciones_preset("qsv")],
            dialogo.cho_preset.GetItems())


class TestAvanzado(BaseDialogo):

    def test_no_estan_los_tres_controles_y_esta_el_boton(self):
        dialogo = self._dialogo(avanzado=True)
        for nombre in ("cho_codificador", "sp_bitrate_video", "cho_preset"):
            with self.subTest(nombre=nombre):
                self.assertFalse(hasattr(dialogo, nombre))
        self.assertTrue(hasattr(dialogo, "btn_pasar_sencillo"))
        self.assertTrue(hasattr(dialogo, "txt_avanzado"))

    def test_conserva_codificador_bitrate_y_preset(self):
        ajustes = de_prueba(codificador="nvenc", bitrate_video=5000,
                            preset="p6")
        dialogo = self._dialogo(ajustes, avanzado=True)
        resultado = dialogo.ajustes()
        self.assertEqual(resultado.codificador, "nvenc")
        self.assertEqual(resultado.bitrate_video, 5000)
        self.assertEqual(resultado.preset, "p6")

    def test_el_pedido_de_pasar_a_sencillo_nace_apagado(self):
        dialogo = self._dialogo(avanzado=True)
        self.assertFalse(dialogo.pasar_a_sencillo_pedido())


class TestResoluciones(BaseDialogo):

    def test_cambiar_la_orientacion_elige_la_equivalente(self):
        dialogo = self._dialogo(de_prueba(
            ancho_lienzo=1920, alto_lienzo=1080,
            ancho_salida=1280, alto_salida=720))
        dialogo.rad_orientacion.SetSelection(1)
        dialogo._al_cambiar_orientacion(None)
        self.assertEqual(dialogo.cho_lienzo.GetValue(), (1080, 1920))
        self.assertEqual(dialogo.cho_salida.GetValue(), (720, 1280))

    def test_la_salida_no_queda_mayor_que_el_lienzo(self):
        dialogo = self._dialogo(de_prueba(
            ancho_lienzo=1920, alto_lienzo=1080,
            ancho_salida=1920, alto_salida=1080))
        dialogo.cho_lienzo.SetValue((1280, 720))
        dialogo._al_cambiar_lienzo(None)
        salida = dialogo.cho_salida.GetValue()
        self.assertTrue(salida[0] <= 1280 and salida[1] <= 720)
        self.assertEqual(dialogo.ajustes().ancho_salida, salida[0])


class TestGeometria(BaseDialogo):

    def test_el_cuadro_usa_las_medidas_comunes(self):
        dialogo = self._dialogo()
        self.addCleanup(destruir, dialogo)
        dialogo.Show()
        wx.Yield()
        ancho, alto = dialogo.GetClientSize()
        self.assertGreaterEqual(ancho, formulario.ANCHO_MINIMO,
                                f"tamaño {ancho} x {alto}")
        self.assertLessEqual(alto, formulario.ALTO_MAXIMO,
                             f"tamaño {ancho} x {alto}")
        zona = dialogo.cho_lienzo.GetParent()
        titulos = [hijo.GetLabel() for hijo in zona.GetChildren()
                   if isinstance(hijo, wx.StaticBox)]
        self.assertEqual(titulos, [_("Vídeo"), _("Transmisión"),
                                   _("Grabación"), _("Audio")])
        hermanos = zona.GetChildren()
        rotulo = hermanos[hermanos.index(dialogo.cho_lienzo) - 1]
        self.assertIsInstance(rotulo, wx.StaticText,
                              f"tamaño {ancho} x {alto}")
        self.assertLess(rotulo.GetPosition().y + rotulo.GetSize().height,
                        dialogo.cho_lienzo.GetPosition().y)
        self.assertEqual(dialogo.btn_guardar.GetSize().width,
                         dialogo.btn_cancelar.GetSize().width)
        self.assertEqual(dialogo.btn_cancelar.GetPosition().x - (
            dialogo.btn_guardar.GetPosition().x
            + dialogo.btn_guardar.GetSize().width),
            formulario.ENTRE_BOTONES)
        panel = dialogo.btn_guardar.GetParent()
        self.assertEqual(panel.GetClientSize().width - (
            dialogo.btn_cancelar.GetPosition().x
            + dialogo.btn_cancelar.GetSize().width), formulario.MARGEN)
        if not tema.ALTO_CONTRASTE:
            self.assertEqual(dialogo.btn_guardar.GetBackgroundColour(),
                             tema._T.primary)

    def test_guardar_y_cerrar_lleva_el_color_de_la_accion_principal(self):
        with mock.patch.object(paleta, "pintar_ventana"):
            dialogo = self._dialogo()
        if tema.ALTO_CONTRASTE:
            self.skipTest("Windows está en alto contraste")
        self.assertEqual(dialogo.btn_guardar.GetBackgroundColour(),
                         tema._T.primary)


if __name__ == "__main__":
    unittest.main()
