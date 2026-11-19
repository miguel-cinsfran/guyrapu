# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""La ventana Prueba sin directo con wx real: campos, envío y cierre.

Abre ventanas.
"""

import tempfile
import unittest
from unittest import mock

import wx

from guyrapu.core.config import TIPO_SUPERCHAT, TIPO_TEXTO
from guyrapu.ui import chat_vivo, ensayo_ventana, gui_sesion
from tests.rutas_temporales import redirigir_rutas
from tests.ventanas_prueba import app_de_prueba, destruir


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = app_de_prueba()

    @classmethod
    def tearDownClass(cls):
        del cls.app

    def _frame(self):
        frame = wx.Frame(None)
        self.addCleanup(destruir, frame)
        frame._ensayo = True
        frame._conectado = False
        frame.chat_vivo = mock.Mock()
        frame._capa_video = mock.Mock()
        frame._reiniciar_datos_sesion = mock.Mock()
        frame._encuesta_en_vivo = mock.Mock()
        frame._preguntas_en_vivo = mock.Mock()
        return frame

    def _ventana(self, frame):
        ventana = ensayo_ventana.VentanaEnsayo(frame)
        self.addCleanup(destruir, ventana)
        return ventana

    @staticmethod
    def _pulsar(boton):
        evento = wx.CommandEvent(wx.EVT_BUTTON.typeId, boton.GetId())
        evento.SetEventObject(boton)
        boton.GetEventHandler().ProcessEvent(evento)


class TestCampos(Base):
    def test_el_orden_de_tab_es_autor_plataforma_tipo_cantidad_mensaje_enviar_cerrar(self):
        ventana = self._ventana(self._frame())
        panel = ventana.GetChildren()[0]
        controles = [control for control in panel.GetChildren()
                     if not isinstance(control, wx.StaticText)]
        self.assertEqual(controles, [
            ventana.txt_autor, ventana.cho_plataforma, ventana.cho_tipo,
            ventana.txt_cantidad, ventana.txt_mensaje,
            ventana.btn_enviar, ventana.btn_cerrar])

    def test_cada_control_tiene_su_nombre_accesible(self):
        ventana = self._ventana(self._frame())
        nombres = {
            "txt_autor": "Autor", "cho_plataforma": "Plataforma",
            "cho_tipo": "Tipo", "txt_cantidad": "Cantidad",
            "txt_mensaje": "Mensaje", "btn_enviar": "Enviar",
            "btn_cerrar": "Cerrar",
        }
        for atributo, nombre in nombres.items():
            with self.subTest(control=atributo):
                self.assertEqual(getattr(ventana, atributo).GetName(), nombre)

    def test_abrir_marca_el_ensayo_y_crea_la_ventana(self):
        frame = self._frame()
        abierta = []
        with mock.patch.object(ensayo_ventana, "VentanaEnsayo",
                               side_effect=lambda f: abierta.append(f) or mock.Mock()):
            ensayo_ventana.abrir(frame)
        self.assertTrue(frame._ensayo)
        self.assertEqual(abierta, [frame])

    def test_el_foco_al_abrir_esta_en_el_autor_con_sus_valores_de_fabrica(self):
        ventana = self._ventana(self._frame())
        self.assertIs(wx.Window.FindFocus(), ventana.txt_autor)
        self.assertEqual(ventana.txt_autor.GetValue(), "Público de prueba")
        self.assertEqual(ventana.cho_plataforma.GetStringSelection(), "YouTube")
        self.assertEqual(ventana.cho_tipo.GetStringSelection(), "Mensaje")
        self.assertEqual(ventana.txt_cantidad.GetValue(), "")
        self.assertEqual(ventana.txt_mensaje.GetValue(), "")


class TestEnviar(Base):
    def test_un_mensaje_llega_al_reparto_y_el_foco_vuelve_a_mensaje_vacio(self):
        frame = self._frame()
        ventana = self._ventana(frame)
        ventana.txt_mensaje.SetValue("hola")
        with mock.patch.object(ensayo_ventana, "anunciar") as anunciar:
            self._pulsar(ventana.btn_enviar)
        registro = frame.chat_vivo.encolar.call_args.args[0]
        self.assertEqual(registro.autor, "Público de prueba")
        self.assertEqual(registro.plataforma, "youtube")
        self.assertEqual(registro.texto, "hola")
        self.assertEqual(registro.tipo, TIPO_TEXTO)
        self.assertEqual(ventana.txt_mensaje.GetValue(), "")
        self.assertIs(wx.Window.FindFocus(), ventana.txt_mensaje)
        anunciar.assert_called_once_with("Enviado a la prueba.")

    def test_la_cantidad_se_ignora_en_un_mensaje_sin_sacarla_del_tab(self):
        frame = self._frame()
        ventana = self._ventana(frame)
        self.assertTrue(ventana.txt_cantidad.IsEnabled())
        ventana.txt_cantidad.SetValue("99")
        with mock.patch.object(ensayo_ventana, "anunciar"):
            self._pulsar(ventana.btn_enviar)
        registro = frame.chat_vivo.encolar.call_args.args[0]
        self.assertEqual(registro.monto, "")

    def test_un_regalo_de_tiktok_lleva_la_cantidad_en_diamantes(self):
        frame = self._frame()
        ventana = self._ventana(frame)
        ventana.txt_autor.SetValue("Ana")
        ventana.cho_plataforma.SetSelection(1)
        ventana.cho_tipo.SetSelection(2)
        ventana.txt_cantidad.SetValue("100")
        ventana.txt_mensaje.SetValue("un regalo")
        with mock.patch.object(ensayo_ventana, "anunciar"):
            self._pulsar(ventana.btn_enviar)
        registro = frame.chat_vivo.encolar.call_args.args[0]
        self.assertEqual(registro.autor, "Ana")
        self.assertEqual(registro.plataforma, "tiktok")
        self.assertEqual(registro.tipo, TIPO_SUPERCHAT)
        self.assertEqual(registro.monto, "100 diamantes")


class TestCerrar(Base):
    def test_cerrar_termina_el_ensayo_con_la_limpieza_completa(self):
        frame = self._frame()
        ventana = self._ventana(frame)
        with mock.patch.object(ensayo_ventana, "anunciar"):
            self._pulsar(ventana.btn_cerrar)
        self.assertFalse(frame._ensayo)
        frame._reiniciar_datos_sesion.assert_called_once_with()
        frame._capa_video.vaciar.assert_called_once_with()
        frame._encuesta_en_vivo._descartar.assert_called_once_with()
        frame._preguntas_en_vivo.cola.vaciar.assert_called_once_with()
        self.assertTrue(ventana.cerrado)


class TestConectarConEnsayo(Base):
    def test_intentar_conectar_dice_que_cierre_la_ventana(self):
        frame = mock.Mock()
        frame._ensayo = True
        with mock.patch.object(gui_sesion, "anunciar") as anunciar, \
                mock.patch.object(gui_sesion._snd, "reproducir") as sonar:
            gui_sesion.on_conectar(frame, None)
        anunciar.assert_called_once_with(
            "Cierra Prueba sin directo para conectar un directo.")
        sonar.assert_called_once_with("error")
        frame.on_conectar_cb.assert_not_called()


class TestMensajeEnLaListaDelChat(Base):
    """El mensaje de la ventana recorre el encolado y el volcado del chat."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        parche = redirigir_rutas(self.tmp.name)
        parche.__enter__()
        self.addCleanup(parche.__exit__, None, None, None)

    def _frame_con_chat(self, ensayo):
        frame = wx.Frame(None)
        self.addCleanup(destruir, frame)
        frame._alive = True
        frame._conectado = False
        frame._ensayo = ensayo
        frame.lista_chat = wx.ListBox(frame, name="ChatDelEnsayo")
        frame.chat_vivo = chat_vivo.ControladorChat(
            frame.lista_chat, 500,
            activo=lambda: frame._alive and frame._conectado,
            autor_oculto=lambda autor: False,
            formatear=lambda autor, texto, hora, tipo, monto: (
                f"{autor}: {texto}"),
            al_superchat=lambda monto: None)
        return frame

    def _enviar_y_volcar(self, frame):
        ventana = self._ventana(frame)
        ventana.txt_mensaje.SetValue("mensaje en la lista")
        with mock.patch.object(ensayo_ventana, "anunciar"), \
                mock.patch.object(chat_vivo._snd, "reproducir"):
            self._pulsar(ventana.btn_enviar)
            frame.chat_vivo.volcar_ya()
        return frame.lista_chat

    def test_en_ensayo_el_mensaje_aparece_en_la_lista_del_chat(self):
        frame = self._frame_con_chat(ensayo=True)
        lista = self._enviar_y_volcar(frame)
        self.assertEqual(lista.GetCount(), 1)
        self.assertIn("mensaje en la lista", lista.GetString(0))

    def test_sin_ensayo_ni_conexion_el_mensaje_no_aparece(self):
        frame = self._frame_con_chat(ensayo=False)
        lista = self._enviar_y_volcar(frame)
        self.assertEqual(lista.GetCount(), 0)


if __name__ == "__main__":
    unittest.main()
