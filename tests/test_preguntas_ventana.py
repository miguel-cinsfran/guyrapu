# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""La página Preguntas: filas, vacío, cola en vivo y acciones.

Abre ventanas.
"""

import types
import unittest
from unittest import mock

import wx

from guyrapu.interaction import preguntas
from guyrapu.interaction.evento import desde_entrante
from guyrapu.ui import lista_acciones, preguntas_en_vivo, preguntas_ventana
from tests.ventanas_prueba import app_de_prueba, destruir


class _Frame:
    """Ventana principal mínima: sesión, conexión y cola de preguntas."""

    def __init__(self, conectado=False):
        self._conectado = conectado
        self.sesion = types.SimpleNamespace(
            chat_propio=False, conexion_propia=False, es_tiktok=False,
            live_chat_id=None)
        self._atajos = {}

    def _sesion_api_disponible(self):
        return False


class BasePanel(unittest.TestCase):

    def setUp(self):
        self.app = app_de_prueba()
        self.padre = wx.Frame(None)
        self.addCleanup(destruir, self.padre)
        self.frame = _Frame(conectado=True)
        self.anuncios = []
        self.immediato = mock.patch.object(
            preguntas_ventana.wx, "CallAfter",
            side_effect=lambda funcion: funcion())
        self.immediato.start()
        self.addCleanup(self.immediato.stop)
        for modulo in (preguntas_ventana, lista_acciones):
            anunciar = mock.patch.object(
                modulo, "anunciar", side_effect=self.anuncios.append)
            anunciar.start()
            self.addCleanup(anunciar.stop)
        self.panel = self._panel()

    def _panel(self, conectado=True):
        self.frame._conectado = conectado
        panel = preguntas_ventana.PanelPreguntas(self.padre, self.frame)
        self.addCleanup(destruir, panel)
        return panel

    def _recibir(self, texto, autor="Ana", autor_id="A", plataforma="youtube"):
        invocacion = preguntas.leer(texto)
        self.frame._preguntas_en_vivo.cola.agregar(
            desde_entrante(autor, texto, "texto", "", autor_id, "",
                           plataforma),
            invocacion.argumentos, [], 1.0)

    def _elegir(self, indice=0):
        self.panel.lista.SetSelection(indice)


class TestFilas(BasePanel):

    def test_p2_la_fila_lleva_autor_plataforma_y_texto(self):
        self._recibir("!pregunta Primera", "Ana", "A", "youtube")
        self._recibir("!pregunta Segunda", "Beto", "B", "tiktok")
        self.assertEqual(
            [self.panel.lista.GetString(indice)
             for indice in range(self.panel.lista.GetCount())],
            ["Ana, YouTube: Primera", "Beto, TikTok: Segunda"])

    def test_p3_sin_preguntas_muestra_el_texto_exacto(self):
        self.assertEqual(self.panel.lista.GetCount(), 1)
        self.assertEqual(self.panel.lista.GetString(0), preguntas_ventana.VACIO)
        self.assertEqual(self.panel.lista.GetName(), "Preguntas del público")

    def test_p4_la_lista_se_actualiza_cuando_cambia_la_cola(self):
        self._recibir("!pregunta Primera", "Ana", "A")
        self.assertEqual(self.panel.lista.GetCount(), 1)
        self._recibir("!pregunta Segunda", "Beto", "B")
        self.assertEqual(self.panel.lista.GetCount(), 2)
        primera = self.frame._preguntas_en_vivo.cola.siguiente()
        preguntas_en_vivo.responder(self.frame, primera.id)
        self.assertEqual(self.panel.lista.GetCount(), 1)
        self.assertEqual(self.panel.lista.GetString(0), "Beto, YouTube: Segunda")

    def test_p4_al_destruir_el_panel_se_desuscribe(self):
        aviso = self.panel._al_cambiar
        suscriptores = self.frame._preguntas_en_vivo.cola._suscriptores
        self.assertIn(aviso, suscriptores)
        self.panel.Destroy()
        wx.Yield()
        self.assertNotIn(aviso, suscriptores)

    def test_p4_la_elegida_se_conserva_aunque_cambie_de_lugar(self):
        self._recibir("!pregunta Primera", "Ana", "A")
        self._recibir("!pregunta Segunda", "Beto", "B")
        self._recibir("!pregunta Tercera", "Carla", "C")
        self._elegir(2)
        tercera = self.panel._elegida()
        self.assertEqual(tercera.texto, "Tercera")
        primera = self.frame._preguntas_en_vivo.cola.siguiente()
        preguntas_en_vivo.responder(self.frame, primera.id)
        self.assertEqual(self.panel.lista.GetCount(), 2)
        self.assertEqual(self.panel.lista.GetSelection(), 1)
        self.assertEqual(self.panel._elegida().id, tercera.id)
        self.assertEqual(self.panel._elegida().texto, "Tercera")

    def test_p4_la_elegida_se_conserva_si_no_queda_ultima(self):
        frame = _Frame(conectado=True)
        preguntas_en_vivo.suscribir(frame, lambda: None)
        for texto, autor, autor_id in (
                ("!pregunta Primera", "Ana", "A"),
                ("!pregunta Segunda", "Beto", "B"),
                ("!pregunta Tercera", "Carla", "C"),
                ("!pregunta Cuarta", "Dora", "D")):
            invocacion = preguntas.leer(texto)
            frame._preguntas_en_vivo.cola.agregar(
                desde_entrante(autor, texto, "texto", "", autor_id, "",
                               "youtube"),
                invocacion.argumentos, [], 1.0)
        panel = preguntas_ventana.PanelPreguntas(self.padre, frame)
        self.addCleanup(destruir, panel)
        panel.lista.SetSelection(2)
        tercera = panel._elegida()
        primera = frame._preguntas_en_vivo.cola.siguiente()
        preguntas_en_vivo.responder(frame, primera.id)
        self.assertEqual(panel.lista.GetCount(), 3)
        self.assertEqual(panel.lista.GetSelection(), 1)
        self.assertEqual(panel._elegida().id, tercera.id)


class TestAcciones(BasePanel):

    def test_p5_mostrar_anuncia_y_suma_al_video(self):
        self._recibir("!pregunta Primera")
        self._elegir()
        with mock.patch.object(preguntas_en_vivo, "mostrar",
                               return_value=True) as mostrar:
            self.panel._lista.ejecutar("mostrar")
        mostrar.assert_called_once_with(self.frame, 1)
        self.assertEqual(self.anuncios, ["Pregunta en el vídeo"])

    def test_p5_responder_anuncia_y_saca_de_la_cola(self):
        self._recibir("!pregunta Primera")
        self._elegir()
        self.panel._lista.ejecutar("responder")
        self.assertEqual(self.anuncios, ["Pregunta respondida"])
        self.assertEqual(self.frame._preguntas_en_vivo.cola.pendientes(), [])

    def test_p5_eliminar_anuncia_y_saca_de_la_cola(self):
        self._recibir("!pregunta Primera")
        self._elegir()
        self.panel._lista.ejecutar("eliminar")
        self.assertEqual(self.anuncios, ["Pregunta eliminada"])
        self.assertEqual(self.frame._preguntas_en_vivo.cola.pendientes(), [])

    def test_p5_vaciar_pregunta_antes_y_anuncia(self):
        self._recibir("!pregunta Primera", "Ana", "A")
        self._recibir("!pregunta Segunda", "Beto", "B")
        with mock.patch.object(preguntas_ventana.confirmar, "preguntar",
                               return_value=True) as preguntar:
            self.panel._lista.ejecutar("vaciar")
        preguntar.assert_called_once()
        self.assertFalse(preguntar.call_args.kwargs["predeterminado_si"])
        self.assertEqual(self.anuncios, ["Cola de preguntas vaciada"])
        self.assertEqual(self.frame._preguntas_en_vivo.cola.pendientes(), [])

    def test_p5_vaciar_cancelado_no_toca_la_cola(self):
        self._recibir("!pregunta Primera")
        with mock.patch.object(preguntas_ventana.confirmar, "preguntar",
                               return_value=False):
            self.panel._lista.ejecutar("vaciar")
        self.assertEqual(self.anuncios, [])
        self.assertEqual(len(self.frame._preguntas_en_vivo.cola.pendientes()), 1)


class TestMotivoDelVideo(BasePanel):

    def test_p6_con_el_video_conectado_se_puede_mostrar(self):
        self.panel = self._panel(conectado=True)
        self._recibir("!pregunta Primera")
        self._elegir()
        accion = self.panel._lista._accion("mostrar")
        self.assertEqual(accion.motivo(), "")
        with mock.patch.object(preguntas_en_vivo, "mostrar",
                               return_value=True):
            self.panel._lista.ejecutar("mostrar")
        self.assertEqual(self.anuncios, ["Pregunta en el vídeo"])

    def test_p6_sin_video_avisa_el_motivo_y_no_muestra(self):
        self.panel = self._panel(conectado=False)
        self._recibir("!pregunta Primera")
        self._elegir()
        accion = self.panel._lista._accion("mostrar")
        self.assertEqual(accion.motivo(), "Sin conexión con OBS")
        with mock.patch.object(preguntas_en_vivo, "mostrar") as mostrar:
            self.panel._lista.ejecutar("mostrar")
        mostrar.assert_not_called()
        self.assertEqual(self.anuncios, ["Sin conexión con OBS."])


if __name__ == "__main__":
    unittest.main()
