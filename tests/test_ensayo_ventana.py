# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""La ventana Prueba sin directo con wx real: campos, envío y cierre.

Abre ventanas.
"""

import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

import wx

from guyrapu.core import paths
from guyrapu.core.idioma import _
from guyrapu.interaction import disparadores_guardados
from guyrapu.core.config import TIPO_SUPERCHAT, TIPO_TEXTO
from guyrapu.core.sonidos_eventos import ROL_MODERADOR
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
    def test_el_orden_de_tab_es_plataforma_tipo_rol_autor_campos_botones_resultados(self):
        ventana = self._ventana(self._frame())
        panel = ventana.GetChildren()[0]
        controles = [control for control in panel.GetChildren()
                     if not isinstance(control, wx.StaticText)]
        self.assertEqual(controles, [
            ventana.cho_plataforma, ventana.cho_tipo, ventana.cho_rol,
            ventana.txt_autor, ventana.txt_regalo, ventana.txt_cantidad,
            ventana.txt_mensaje, ventana.btn_enviar, ventana.btn_cerrar,
            ventana.lista_resultados])

    def test_cada_control_tiene_su_nombre_accesible(self):
        ventana = self._ventana(self._frame())
        nombres = {
            "cho_plataforma": "Plataforma", "cho_tipo": "Tipo", "cho_rol": "Rol",
            "txt_autor": "Autor", "txt_regalo": "Nombre del regalo",
            "txt_cantidad": "Cantidad", "txt_mensaje": "Mensaje",
            "btn_enviar": "Enviar", "btn_cerrar": "Cerrar",
            "lista_resultados": "Resultados",
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

    def test_el_foco_al_abrir_esta_en_mensaje_con_los_valores_de_fabrica(self):
        ventana = self._ventana(self._frame())
        self.assertIs(wx.Window.FindFocus(), ventana.txt_mensaje)
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
        self._pulsar(ventana.btn_enviar)
        registro = frame.chat_vivo.encolar.call_args.args[0]
        self.assertEqual(registro.autor, "Público de prueba")
        self.assertEqual(registro.plataforma, "youtube")
        self.assertEqual(registro.texto, "hola")
        self.assertEqual(registro.tipo, TIPO_TEXTO)
        self.assertEqual(ventana.txt_mensaje.GetValue(), "")
        self.assertIs(wx.Window.FindFocus(), ventana.txt_mensaje)

    def test_la_cantidad_se_ignora_en_un_mensaje_sin_sacarla_del_tab(self):
        frame = self._frame()
        ventana = self._ventana(frame)
        self.assertFalse(ventana.txt_cantidad.IsShown())
        ventana.txt_cantidad.SetValue("99")
        self._pulsar(ventana.btn_enviar)
        registro = frame.chat_vivo.encolar.call_args.args[0]
        self.assertEqual(registro.monto, "")

    def test_un_regalo_de_tiktok_lleva_la_cantidad_en_diamantes(self):
        frame = self._frame()
        ventana = self._ventana(frame)
        ventana.txt_autor.SetValue("Ana")
        ventana.cho_plataforma.SetSelection(1)
        ventana.cho_tipo.SetSelection(1)
        ventana._actualizar_campos()
        ventana.txt_regalo.SetValue("Rosa")
        ventana.txt_cantidad.SetValue("100")
        self._pulsar(ventana.btn_enviar)
        registro = frame.chat_vivo.encolar.call_args.args[0]
        self.assertEqual(registro.autor, "Ana")
        self.assertEqual(registro.plataforma, "tiktok")
        self.assertEqual(registro.tipo, TIPO_SUPERCHAT)
        self.assertEqual(registro.texto, "Rosa")
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

    def _frame_con_chat(self, ensayo, reloj=None):
        frame = wx.Frame(None)
        self.addCleanup(destruir, frame)
        frame._alive = True
        frame._conectado = False
        frame._ensayo = ensayo
        frame._capa_video = mock.Mock()
        frame.lista_chat = wx.ListBox(frame, name="ChatDelEnsayo")
        frame.chat_vivo = chat_vivo.ControladorChat(
            frame.lista_chat, 500,
            activo=lambda: frame._alive and frame._conectado,
            autor_oculto=lambda autor: False,
            formatear=lambda autor, texto, hora, tipo, monto: (
                f"{autor}: {texto}"),
            al_superchat=lambda monto: None,
            reloj=reloj or (lambda: 0.0))
        return frame

    def _enviar_y_volcar(self, frame):
        ventana = self._ventana(frame)
        ventana.txt_mensaje.SetValue("mensaje en la lista")
        with mock.patch.object(chat_vivo, "anunciar_con_sonido"), \
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


class TestTiposYCampos(Base):

    def test_los_tipos_cambian_con_la_plataforma_y_el_foco_se_queda(self):
        ventana = self._ventana(self._frame())
        self.assertEqual(ventana.cho_tipo.GetStrings(),
                         ["Mensaje", "Super Chat", "Membresía"])
        ventana.cho_plataforma.SetFocus()
        ventana.cho_plataforma.SetSelection(1)
        ventana._actualizar_tipos()
        self.assertIs(wx.Window.FindFocus(), ventana.cho_plataforma)
        self.assertEqual(ventana.cho_tipo.GetStrings(),
                         ["Mensaje", "Regalo", "Seguidor nuevo", "Me gusta",
                          "Directo compartido"])
        ventana.cho_tipo.SetFocus()
        ventana.cho_tipo.SetSelection(1)
        ventana._actualizar_campos()
        self.assertIs(wx.Window.FindFocus(), ventana.cho_tipo)

    def test_solo_se_ven_los_campos_del_tipo_elegido(self):
        ventana = self._ventana(self._frame())
        casos = (
            (0, 0, (False, False, True), True),
            (0, 1, (False, True, True), True),
            (0, 2, (False, False, False), True),
            (1, 0, (False, False, True), False),
            (1, 1, (True, True, False), False),
            (1, 2, (False, False, False), False),
            (1, 3, (False, False, False), False),
            (1, 4, (False, False, False), False),
        )
        for plataforma, tipo, visibles, con_rol in casos:
            with self.subTest(plataforma=plataforma, tipo=tipo):
                ventana.cho_plataforma.SetSelection(plataforma)
                ventana._actualizar_tipos()
                ventana.cho_tipo.SetSelection(tipo)
                ventana._actualizar_campos()
                controles = (ventana.txt_regalo, ventana.txt_cantidad,
                             ventana.txt_mensaje)
                self.assertEqual([c.IsShown() for c in controles],
                                 list(visibles))
                self.assertEqual(
                    [ventana._rotulos[c].IsShown()
                     for c in ("txt_regalo", "txt_cantidad", "txt_mensaje")],
                    list(visibles))
                self.assertEqual(ventana.cho_rol.IsShown(), con_rol)
                self.assertEqual(
                    ventana._rotulos["cho_rol"].IsShown(), con_rol)
                self.assertTrue(ventana.txt_autor.IsShown())

    def test_el_rol_llega_al_registro_y_tiktok_no_lo_muestra(self):
        frame = self._frame()
        ventana = self._ventana(frame)
        ventana.cho_rol.SetSelection(1)
        self._pulsar(ventana.btn_enviar)
        self.assertEqual(
            frame.chat_vivo.encolar.call_args.args[0].rol, ROL_MODERADOR)
        ventana.cho_plataforma.SetSelection(1)
        ventana._actualizar_tipos()
        self.assertFalse(ventana.cho_rol.IsShown())


class TestResultados(Base):

    def test_los_resultados_se_agregan_al_final_con_hora_y_lo_enviado(self):
        ventana = self._ventana(self._frame())
        self.assertEqual(ventana.lista_resultados.GetCount(), 1)
        self.assertEqual(ventana.lista_resultados.GetString(0),
                         _(ensayo_ventana.VACIO_RESULTADOS))
        registro = SimpleNamespace(hora="12:30:05", texto="hola", autor="Ana")
        ventana.agregar_resultado(registro, "Respondió el comando hola.")
        ventana.agregar_resultado(
            registro, "Nada respondió: el comando hola está en pausa.")
        self.assertEqual(
            [ventana.lista_resultados.GetString(i)
             for i in range(ventana.lista_resultados.GetCount())],
            ["12:30:05 hola: Respondió el comando hola.",
             "12:30:05 hola: Nada respondió: el comando hola está en pausa."])


class TestResultadoDesdeLaVentana(TestMensajeEnLaListaDelChat):

    def test_un_super_chat_con_una_alerta_anuncia_y_deja_la_respuesta(self):
        disparadores_guardados.guardar(paths.disparadores(), [{
            "nombre": "Agradecimiento", "cuando": "evento",
            "evento": "superchat", "minimo": None, "regalo": "",
            "medio": "", "tarjeta": "Gracias", "estilo": "", "segundos": 8,
            "permiso": "todos", "nombres": [], "espera_general": 5.0,
            "espera_persona": 30.0, "activo": True,
        }])
        frame = self._frame_con_chat(ensayo=True)
        ventana = self._ventana(frame)
        frame._ventana_ensayo = ventana
        ventana.cho_tipo.SetSelection(1)
        ventana._actualizar_campos()
        ventana.txt_cantidad.SetValue("5,00 €")
        ventana.txt_mensaje.SetValue("gracias")
        with mock.patch.object(chat_vivo, "anunciar_con_sonido") as avisar:
            self._pulsar(ventana.btn_enviar)
        avisar.assert_called_once_with(
            "Respondió la alerta Agradecimiento.", "listo")
        self.assertIn("gracias: Respondió la alerta Agradecimiento.",
                      ventana.lista_resultados.GetString(0))


if __name__ == "__main__":
    unittest.main()
