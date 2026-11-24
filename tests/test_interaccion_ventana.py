# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Ventana Interacción: páginas, foco, página recordada y cableado.

Abre ventanas.
"""

import tempfile
import unittest
from unittest import mock

import wx

from guyrapu.core import config_predeterminada
from guyrapu.ui import (
    atajos_captura, botonera_atajos, comando_comandos_chat, comando_estilos,
    comando_interaccion, comando_mensajes_automaticos, comandos_ventana,
    disparadores_ventana, encuestas_ventana, ensayo_ventana, estilos_ventana,
    gui, gui_menu, interaccion_ventana, medios_ventana,
    mensajes_automaticos_ventana, menu_interaccion, metas_ventana,
    palabras_bloqueadas_ventana, preguntas_ventana)
from tests.letras_acceso import letras_repetidas, repetidas_con_lo_de_fuera
from tests.rutas_temporales import redirigir_rutas
from tests.ventanas_prueba import app_de_prueba, destruir


class FrameDoble(wx.Frame):
    def __init__(self):
        super().__init__(None)
        self._config = {}
        self.mi_programados_activo = mock.Mock()
        self.programador = mock.Mock()
        self._enlaces = []

    def _accel(self, _accion):
        return ""

    def _bind_menu(self, item, fn, *args):
        self._enlaces.append((fn, args))


class BaseVentana(unittest.TestCase):
    def setUp(self):
        self.app = app_de_prueba()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        parche = redirigir_rutas(self.tmp.name)
        parche.__enter__()
        self.addCleanup(parche.__exit__, None, None, None)

    def _padre(self, configuracion=None):
        padre = wx.Frame(None)
        padre._config = dict(configuracion or {})
        padre.mi_programados_activo = mock.Mock()
        padre.programador = mock.Mock()
        self.addCleanup(destruir, padre)
        return padre

    def _ventana(self, pagina=None, configuracion=None):
        ventana = interaccion_ventana.VentanaInteraccion(
            self._padre(configuracion), pagina)
        self.addCleanup(destruir, ventana)
        return ventana

    def _menu(self):
        etiquetas = []

        def crear_menu(*_args, **_kwargs):
            menu = mock.MagicMock()
            menu.Append.side_effect = (
                lambda *args: etiquetas.append(args[1]) or mock.Mock())
            menu.AppendCheckItem.side_effect = (
                lambda *args: etiquetas.append(args[1]) or mock.Mock())
            menu.AppendSeparator.side_effect = (
                lambda *args: etiquetas.append("---"))
            return menu

        frame = FrameDoble()
        self.addCleanup(destruir, frame)
        with mock.patch.object(menu_interaccion.wx, "Menu",
                               side_effect=crear_menu):
            menu_interaccion.construir(frame, mock.Mock())
        return frame, etiquetas


class TestPaginas(BaseVentana):

    def test_p1_las_paginas_van_en_orden_y_son_los_paneles(self):
        ventana = self._ventana()
        self.assertEqual(
            [ventana.libro.GetPageText(indice)
             for indice in range(ventana.libro.GetPageCount())],
            ["Comandos", "Alertas", "Mensajes automáticos", "Encuestas",
             "Preguntas", "Metas", "Medios", "Estilos", "Palabras bloqueadas"])
        self.assertIsInstance(ventana.libro.GetPage(0),
                              comandos_ventana.PanelComandos)
        self.assertIsInstance(ventana.libro.GetPage(1),
                              disparadores_ventana.PanelDisparadores)
        self.assertIsInstance(
            ventana.libro.GetPage(2),
            mensajes_automaticos_ventana.PanelMensajesAutomaticos)
        self.assertIsInstance(ventana.libro.GetPage(3),
                              encuestas_ventana.PanelEncuestas)
        self.assertIsInstance(ventana.libro.GetPage(4),
                              preguntas_ventana.PanelPreguntas)
        self.assertIsInstance(ventana.libro.GetPage(5),
                              metas_ventana.PanelMetas)
        self.assertIsInstance(ventana.libro.GetPage(6),
                              medios_ventana.PanelMedios)
        self.assertIsInstance(ventana.libro.GetPage(7),
                              estilos_ventana.PanelEstilos)
        self.assertIsInstance(
            ventana.libro.GetPage(8),
            palabras_bloqueadas_ventana.PanelPalabrasBloqueadas)

    def test_recargar_comandos_usa_la_pagina_de_comandos(self):
        ventana = self._ventana()
        with mock.patch.object(ventana._paginas["comandos"], "recargar") as recargar:
            ventana.recargar_comandos()
        recargar.assert_called_once_with()

    def test_p2_el_boton_ayuda_va_despues_de_cerrar_y_abre_la_pagina(self):
        ventana = self._ventana("estilos")
        botones = [hijo for hijo in ventana.GetChildren()
                   if isinstance(hijo, wx.Button)]
        self.assertEqual(botones, [ventana.btn_probar, ventana.btn_cerrar,
                                   ventana.btn_ayuda])
        self.assertEqual([boton.GetLabel() for boton in botones],
                         ["Probar sin direc&to", "&Cerrar", "A&yuda"])
        self.assertEqual([boton.GetName() for boton in botones],
                         ["Probar sin directo", "Cerrar", "Ayuda"])
        with mock.patch.object(gui_menu, "abrir_documento_paquete") as abrir:
            evento = wx.CommandEvent(wx.EVT_BUTTON.typeId,
                                     ventana.btn_ayuda.GetId())
            evento.SetEventObject(ventana.btn_ayuda)
            ventana.btn_ayuda.GetEventHandler().ProcessEvent(evento)
        abrir.assert_called_once_with(ventana, "MANUAL", mock.ANY, "estilos")

    def test_p1_el_pie_tiene_diez_pixeles_de_margen_a_la_derecha_y_abajo(self):
        ventana = self._ventana()
        ventana.Layout()
        cliente = ventana.GetClientSize()
        ayuda = ventana.btn_ayuda
        self.assertEqual(
            cliente.width - ayuda.GetPosition().x - ayuda.GetSize().width, 10)
        for boton in (ventana.btn_probar, ventana.btn_cerrar, ayuda):
            self.assertEqual(
                cliente.height - boton.GetPosition().y - boton.GetSize().height,
                10)

    def test_p1_f1_abre_la_pagina_a_la_vista_con_el_foco_dentro_de_ella(self):
        ventana = self._ventana("disparadores")
        ventana.Show()
        try:
            lista = ventana.libro.GetCurrentPage().lista
            lista.SetFocus()
            self.assertIs(wx.Window.FindFocus(), lista)
            evento = wx.KeyEvent(wx.EVT_CHAR_HOOK.typeId)
            evento.SetKeyCode(wx.WXK_F1)
            with mock.patch.object(gui_menu, "abrir_documento_paquete") as abrir:
                ventana.GetEventHandler().ProcessEvent(evento)
            abrir.assert_called_once_with(ventana, "MANUAL", mock.ANY,
                                          "alertas")
        finally:
            ventana.Hide()

    def test_cerrar_sigue_cerrando(self):
        ventana = self._ventana()
        evento = wx.CommandEvent(wx.EVT_BUTTON.typeId,
                                 ventana.btn_cerrar.GetId())
        with mock.patch.object(ventana, "EndModal") as cerrar:
            ventana.btn_cerrar.GetEventHandler().ProcessEvent(evento)
        cerrar.assert_called_once_with(wx.ID_CANCEL)

    def test_p8_probar_sin_directo_llama_a_la_misma_ventana_con_el_marco(self):
        padre = self._padre()
        ventana = interaccion_ventana.VentanaInteraccion(padre)
        self.addCleanup(destruir, ventana)
        with mock.patch.object(ensayo_ventana, "abrir") as abrir:
            evento = wx.CommandEvent(wx.EVT_BUTTON.typeId,
                                     ventana.btn_probar.GetId())
            evento.SetEventObject(ventana.btn_probar)
            ventana.btn_probar.GetEventHandler().ProcessEvent(evento)
        abrir.assert_called_once_with(padre)

    def test_p1_escape_cierra(self):
        evento = mock.Mock()
        evento.GetKeyCode.return_value = wx.WXK_ESCAPE
        ventana = self._ventana()
        with mock.patch.object(ventana, "EndModal") as cerrar:
            ventana._al_tecla(evento)
        cerrar.assert_called_once_with(wx.ID_CANCEL)

    def test_escape_detiene_la_escucha_antes_de_cerrar(self):
        evento = mock.Mock()
        evento.GetKeyCode.return_value = wx.WXK_ESCAPE
        ventana = self._ventana("medios")
        with mock.patch.object(ventana._paginas["medios"],
                               "detener_escucha", return_value=True), \
                mock.patch.object(ventana, "EndModal") as cerrar:
            ventana._al_tecla(evento)
        cerrar.assert_not_called()

    def test_cerrar_suelta_la_escucha_previa(self):
        ventana = self._ventana()
        with mock.patch.object(ventana._paginas["medios"],
                               "soltar") as soltar, \
                mock.patch.object(ventana, "EndModal"):
            ventana._al_cerrar(None)
        soltar.assert_called_once_with()

    def test_la_lista_de_paginas_tiene_su_nombre_accesible(self):
        ventana = self._ventana()
        self.assertEqual(ventana.lista_paginas.GetName(),
                         "Páginas de interacción")

    def test_las_listas_de_las_paginas_conservan_su_nombre(self):
        ventana = self._ventana()
        self.assertEqual(
            [ventana.libro.GetPage(indice).lista.GetName()
             for indice in range(ventana.libro.GetPageCount())],
             ["Comandos del chat guardados", "Alertas guardadas",
              "Mensajes automáticos guardados", "Encuestas guardadas",
              "Preguntas del público", "Metas guardadas", "Medios guardados",
              "Estilos del vídeo guardados", "Palabras bloqueadas"])

    def test_las_letras_no_se_repiten_en_el_dialogo_ni_en_sus_paginas(self):
        ventana = self._ventana()
        self.assertEqual(letras_repetidas(ventana), {})
        self.assertEqual(
            repetidas_con_lo_de_fuera(ventana, ventana.libro),
             {"Comandos": {}, "Alertas": {}, "Mensajes automáticos": {},
              "Encuestas": {}, "Preguntas": {}, "Metas": {}, "Medios": {},
              "Estilos": {}, "Palabras bloqueadas": {}})


class TestPaginaRecordada(BaseVentana):

    def test_p2_sin_pagina_abre_en_la_guardada(self):
        ventana = self._ventana(configuracion={"interaccion_pagina": "comandos"})
        self.assertEqual(ventana.pagina_actual(), "comandos")
        self.assertEqual(ventana.libro.GetCurrentPage().GetName(),
                         "PanelComandos")

    def test_p2_una_pagina_despues_de_encuestas_sigue_abriendo(self):
        # La última página se guarda por clave, no por número: sumar Encuestas
        # en el medio no puede cambiar la página de quien ya usaba Estilos.
        ventana = self._ventana(configuracion={"interaccion_pagina": "estilos"})
        self.assertEqual(ventana.pagina_actual(), "estilos")
        self.assertEqual(ventana.libro.GetCurrentPage().GetName(),
                         "PanelEstilos")

    def test_p2_un_valor_desconocido_abre_en_comandos(self):
        for guardada in ("raro", ""):
            with self.subTest(guardada=guardada):
                ventana = self._ventana(
                    configuracion={"interaccion_pagina": guardada})
                self.assertEqual(ventana.pagina_actual(), "comandos")

    def test_p2_la_pagina_pedida_gana_sobre_la_guardada(self):
        ventana = self._ventana(
            "estilos", configuracion={"interaccion_pagina": "comandos"})
        self.assertEqual(ventana.pagina_actual(), "estilos")

    def test_p3_el_foco_queda_en_la_lista_de_la_pagina(self):
        for pagina in ("mensajes", "comandos", "encuestas", "preguntas",
                       "disparadores", "metas", "medios", "estilos",
                       "palabras"):
            with self.subTest(pagina=pagina):
                ventana = self._ventana(pagina)
                ventana.Show()
                try:
                    self.assertIs(wx.Window.FindFocus(),
                                  ventana.libro.GetCurrentPage().lista)
                finally:
                    ventana.Hide()

    def test_p4_al_cerrar_guarda_la_pagina_y_recarga_el_programador(self):
        frame = self._padre()
        with mock.patch.object(interaccion_ventana.VentanaInteraccion,
                               "ShowModal", lambda _ventana: wx.ID_CANCEL), \
                mock.patch.object(gui, "guardar_opcion") as guardar, \
                mock.patch.object(comando_interaccion.programados, "cargar",
                                  return_value=[]) as cargar, \
                mock.patch.object(comando_interaccion.paths,
                                  "mensajes_programados",
                                  return_value="ruta"):
            comando_interaccion.abrir(frame, "estilos")
        self.assertEqual(frame._config["interaccion_pagina"], "estilos")
        guardar.assert_called_once_with(
            gui.RUTA_CONFIG, "ui", "interaccion_pagina", "estilos")
        cargar.assert_any_call("ruta")
        frame.programador.recargar.assert_called_once_with([])


class TestCableado(BaseVentana):

    def test_construir_deja_la_botonera_de_atajos_y_no_la_repite(self):
        frame = FrameDoble()
        self.addCleanup(destruir, frame)
        with mock.patch.object(menu_interaccion.wx, "Menu",
                               return_value=mock.MagicMock()), \
                mock.patch.object(botonera_atajos.wx, "CallAfter"):
            menu_interaccion.construir(frame, mock.Mock())
            primera = frame._botonera_atajos
            menu_interaccion.construir(frame, mock.Mock())
        self.assertIsInstance(primera, botonera_atajos.BotoneraAtajos)
        self.assertIs(frame._botonera_atajos, primera)

    def test_p5_los_tres_comandos_abren_su_pagina(self):
        frame = mock.Mock()
        with mock.patch.object(comando_interaccion, "abrir") as abrir:
            comando_mensajes_automaticos.abrir(frame)
            comando_comandos_chat.abrir(frame)
            comando_estilos.abrir(frame)
        self.assertEqual(abrir.call_args_list, [
            mock.call(frame, "mensajes"),
            mock.call(frame, "comandos"),
            mock.call(frame, "estilos")])

    def test_p6_el_menu_queda_en_orden_y_sin_letras_repetidas(self):
        _, etiquetas = self._menu()
        self.assertEqual(etiquetas[:6], [
            "&Abrir Interacción…", "Probar sin &directo…",
            "&Mensajes automáticos…", "&Comandos del chat…",
            "Es&tilos del vídeo…", "---"])
        letras = [etiqueta[etiqueta.index("&") + 1].lower()
                  for etiqueta in etiquetas if "&" in etiqueta]
        self.assertEqual(len(letras), len(set(letras)))

    def test_p6_cada_entrada_abre_su_pagina(self):
        frame, _ = self._menu()
        abiertas = []

        def mostrar(dialogo):
            abiertas.append(dialogo.pagina_actual())
            return wx.ID_CANCEL

        with mock.patch.object(interaccion_ventana.VentanaInteraccion,
                               "ShowModal", mostrar), \
                mock.patch.object(gui, "guardar_opcion"), \
                mock.patch.object(comando_interaccion.programados, "cargar",
                                  return_value=[]), \
                mock.patch.object(comando_interaccion.paths,
                                  "mensajes_programados",
                                  return_value="ruta"):
            abren = (comando_interaccion.abrir,
                     comando_mensajes_automaticos.abrir,
                     comando_comandos_chat.abrir, comando_estilos.abrir)
            for fn, args in frame._enlaces:
                if fn in abren:
                    fn(*args)
        self.assertEqual(abiertas,
                         ["comandos", "mensajes", "comandos", "estilos"])

    def test_p7_la_accion_conserva_su_nombre_y_cambia_la_etiqueta(self):
        self.assertEqual(
            config_predeterminada.obtener(
                "atajos", "mensajes_automaticos", "ctrl+shift+a"),
            "ctrl+shift+a")
        self.assertEqual(
            atajos_captura.ETIQUETAS["mensajes_automaticos"],
            "Abrir la ventana Interacción")

    def test_p8_las_ventanas_sueltas_ya_no_existen(self):
        for modulo, nombres in (
                (mensajes_automaticos_ventana,
                 ("VentanaMensajesAutomaticos", "abrir")),
                (comandos_ventana, ("VentanaComandos", "abrir")),
                (estilos_ventana, ("VentanaEstilos", "abrir"))):
            for nombre in nombres:
                with self.subTest(nombre=nombre):
                    self.assertFalse(hasattr(modulo, nombre))

    def test_al_cerrar_tambien_se_recarga_abriendo_por_comandos(self):
        frame = self._padre()
        with mock.patch.object(interaccion_ventana.VentanaInteraccion,
                               "ShowModal", lambda _ventana: wx.ID_CANCEL), \
                mock.patch.object(gui, "guardar_opcion"), \
                mock.patch.object(comando_interaccion.programados, "cargar",
                                  return_value=[]) as cargar, \
                mock.patch.object(comando_interaccion.paths,
                                  "mensajes_programados",
                                  return_value="ruta"):
            comando_interaccion.abrir(frame, "comandos")
        self.assertEqual(frame._config["interaccion_pagina"], "comandos")
        cargar.assert_any_call("ruta")
        frame.programador.recargar.assert_called_once_with([])


if __name__ == "__main__":
    unittest.main()
