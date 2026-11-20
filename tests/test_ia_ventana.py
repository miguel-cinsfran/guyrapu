# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de la ventana Preguntar a la IA.

Con ventana: abren diálogos.
"""

import unittest
from types import SimpleNamespace
from unittest import mock

try:
    import wx
    _HAY_WX = True
except Exception:
    _HAY_WX = False

from guyrapu.ai import consulta
from guyrapu.ai import conversacion
from guyrapu.ai import protocolos
from guyrapu.ai import ventana_ia
from guyrapu.ui import formulario
from guyrapu.ui import ia_guardar_conversacion as guardar_conv
from guyrapu.ui import ia_ventana as ventana
from guyrapu.ui import lista_acciones
from guyrapu.ui import tema
from tests.pseudo_prueba import con_pseudo, textos_sin_marcar
from tests.ventanas_prueba import app_de_prueba, destruir


def _hilo_directo(target, nombre, **kwargs):
    args = kwargs.get("args", ())
    target(*args)
    hilo = mock.Mock()
    hilo.start.return_value = None
    return hilo


def _ajustes_falsos(privacidad_aceptada=True, decir_analizando=True):
    return SimpleNamespace(proveedor="gemini", modelo="m", direccion="",
                           pregunta="", largo="media", tiempo_espera=60,
                           decir_analizando=decir_analizando,
                           privacidad_aceptada=privacidad_aceptada)


class PortapapelesDoble:
    def __init__(self):
        self.texto = None

    def Open(self):
        return True

    def SetData(self, datos):
        self.texto = datos.GetText()

    def Flush(self):
        return True

    def Close(self):
        pass


@unittest.skipUnless(_HAY_WX, "wxPython no está instalado")
class TestVentanaIAVentana(unittest.TestCase):

    def setUp(self):
        self.app = app_de_prueba()
        parche_hilo = mock.patch.object(
            ventana.diagnostico, "crear_hilo", side_effect=_hilo_directo)
        parche_hilo.start()
        self.addCleanup(parche_hilo.stop)
        parche_llamada = mock.patch.object(
            ventana.wx, "CallAfter",
            side_effect=lambda funcion, *args, **kwargs: funcion(*args,
                                                                **kwargs))
        parche_llamada.start()
        self.addCleanup(parche_llamada.stop)

    def _ventana(self):
        dialogo = ventana.VentanaIA(None)
        self.addCleanup(destruir, dialogo)
        return dialogo

    def _enviar_en_curso(self, fallo=None):
        dialogo = self._ventana()
        dialogo._charla.agregar_captura(b"j", "Fuente", "10:00")
        dialogo.txt_mensaje.ChangeValue("¿qué se ve?")
        preparada = consulta.Preparada(object(), "¿qué se ve?", 60)
        guardadas = []

        def _hilo_guardado(target, nombre, **kwargs):
            guardadas.append((target, kwargs.get("args", ())))
            hilo = mock.Mock()
            hilo.start.return_value = None
            return hilo

        enviar = (mock.Mock(side_effect=fallo) if fallo is not None
                  else mock.Mock(return_value=protocolos.Respuesta(
                      "Se ve bien.", False)))
        with mock.patch.object(ventana.ajustes_ia, "leer",
                               return_value=_ajustes_falsos()), \
                mock.patch.object(ventana.catalogo, "cargar",
                                   return_value={}), \
                mock.patch.object(ventana.claves, "leer",
                                   return_value="clave"), \
                mock.patch.object(ventana.consulta, "preparar",
                                   return_value=preparada), \
                mock.patch.object(ventana.envio_ia, "enviar", enviar), \
                mock.patch.object(ventana.diagnostico, "crear_hilo",
                                   side_effect=_hilo_guardado), \
                mock.patch.object(ventana, "anunciar"), \
                mock.patch.object(ventana, "reproducir"):
            dialogo._al_enviar(None)
        return dialogo, guardadas

    def _completar(self, guardadas):
        destino, args = guardadas[0]
        with mock.patch.object(ventana, "anunciar"), \
                mock.patch.object(ventana, "reproducir"):
            destino(*args)

    def test_nombres(self):
        dialogo = self._ventana()
        self.assertEqual(dialogo.GetTitle(), "Preguntar a la IA")
        self.assertEqual(dialogo.GetName(), "VentanaIA")
        self.assertEqual(dialogo.lst_conversacion.GetName(), "Conversación")
        self.assertEqual(dialogo.txt_mensaje.GetName(), "Mensaje")
        self.assertEqual(dialogo.btn_enviar.GetName(), "Enviar")
        self.assertEqual(dialogo.btn_captura.GetName(), "Agregar captura")
        self.assertEqual(dialogo.btn_copiar.GetName(), "Copiar respuesta")
        self.assertEqual(dialogo.btn_nueva.GetName(), "Nueva conversación")
        self.assertEqual(dialogo.btn_cerrar.GetName(), "Cerrar")

    def test_busqueda_por_tecleo_sigue_en_la_conversacion(self):
        dialogo = self._ventana()
        dialogo._charla.agregar_captura(b"j", "Fuente", "10:00")
        dialogo._charla.confirmar("pregunta", "respuesta")
        dialogo._rehacer_lista()
        dialogo.lst_conversacion.SetSelection(0)
        with mock.patch.object(wx, "CallLater"), \
                mock.patch("guyrapu.ui.busqueda_teclado.anunciar"):
            evento = wx.KeyEvent(wx.wxEVT_CHAR)
            evento.SetUnicodeKey(ord("R"))
            dialogo.lst_conversacion.GetEventHandler().ProcessEvent(evento)
        self.assertEqual(dialogo.lst_conversacion.GetSelection(), 2)

    def test_orden_de_tab(self):
        dialogo = self._ventana()
        navegables = [hijo.GetName() for hijo in dialogo.GetChildren()
                      if isinstance(hijo, (wx.ListBox, wx.TextCtrl,
                                          wx.CheckBox, wx.Button))]
        self.assertEqual(navegables, ["Conversación", "Mensaje",
                                      "Enviar", "Agregar captura",
                                      "Copiar respuesta",
                                      "Nueva conversación", "Cerrar"])
        self.assertIs(dialogo.FindFocus(), dialogo.txt_mensaje)

    def test_mnemonicos_sin_repetir(self):
        dialogo = self._ventana()
        rotulos = [dialogo.rotulo_conv.GetLabel(),
                   dialogo.rotulo_msg.GetLabel(),
                   dialogo.btn_enviar.GetLabel(),
                   dialogo.btn_captura.GetLabel(),
                   dialogo.btn_copiar.GetLabel(),
                   dialogo.btn_nueva.GetLabel(),
                   dialogo.btn_cerrar.GetLabel()]
        letras = set()
        for rotulo in rotulos:
            posicion = rotulo.find("&")
            self.assertNotEqual(posicion, -1, f"Sin tecla en {rotulo!r}.")
            self.assertLess(posicion + 1, len(rotulo))
            letras.add(rotulo[posicion + 1].lower())
        self.assertEqual(letras, {"v", "m", "e", "c", "o", "n", "r"})

    def test_fila_guia_con_lista_vacia(self):
        dialogo = self._ventana()
        self.assertEqual(dialogo.lst_conversacion.GetCount(), 1)
        self.assertEqual(dialogo.lst_conversacion.GetString(0),
                         ventana_ia.FILA_GUIA)

    def test_detalle_muestra_texto_y_escape_cierra(self):
        dialogo = self._ventana()
        dialogo._charla.agregar_captura(b"j", "Fuente", "10:00")
        dialogo._rehacer_lista()
        dialogo.lst_conversacion.SetSelection(0)
        esperado = dialogo.lst_conversacion.GetString(0)
        visto = {}

        def _falso_mostrar(uno_mismo):
            visto["texto"] = uno_mismo.txt.GetValue()
            return wx.ID_OK

        with mock.patch.object(ventana.DialogoMensaje, "ShowModal",
                               _falso_mostrar):
            dialogo._mostrar_mensaje()
        self.assertEqual(visto.get("texto"), esperado)
        # El detalle se mostró y se destruyó sin romper la ventana.
        self.assertEqual(dialogo.lst_conversacion.GetCount(), 1)

    def test_intro_por_char_hook_muestra_el_mensaje(self):
        dialogo = self._ventana()
        dialogo._charla.agregar_captura(b"j", "Fuente", "10:00")
        dialogo._rehacer_lista()
        esperado = dialogo.lst_conversacion.GetString(0)
        evento = wx.KeyEvent(wx.wxEVT_CHAR_HOOK)
        evento.KeyCode = wx.WXK_RETURN
        with mock.patch.object(ventana, "DialogoMensaje") as mostrar:
            mostrar.return_value.ShowModal.return_value = wx.ID_OK
            dialogo.lst_conversacion.GetEventHandler().ProcessEvent(evento)
        self.assertEqual(mostrar.call_args.args, (dialogo, esperado))

    def test_doble_clic_muestra_el_mensaje(self):
        dialogo = self._ventana()
        dialogo._charla.agregar_captura(b"j", "Fuente", "10:00")
        dialogo._rehacer_lista()
        with mock.patch.object(ventana, "DialogoMensaje") as mostrar:
            mostrar.return_value.ShowModal.return_value = wx.ID_OK
            dialogo.lst_conversacion.ProcessEvent(wx.CommandEvent(
                wx.wxEVT_LISTBOX_DCLICK, dialogo.lst_conversacion.GetId()))
        mostrar.assert_called_once()

    def test_sin_mensajes_intro_y_ctrl_c_anuncian_la_guia(self):
        dialogo = self._ventana()
        with mock.patch.object(lista_acciones, "anunciar") as anunciar, \
                mock.patch.object(dialogo, "_copiar_texto") as copiar, \
                mock.patch.object(ventana, "DialogoMensaje") as mensaje:
            intro = wx.KeyEvent(wx.wxEVT_CHAR_HOOK)
            intro.SetKeyCode(wx.WXK_RETURN)
            dialogo.lst_conversacion.GetEventHandler().ProcessEvent(intro)
            ctrl_c = wx.KeyEvent(wx.wxEVT_KEY_DOWN)
            ctrl_c.SetKeyCode(ord("C"))
            ctrl_c.SetControlDown(True)
            dialogo.lst_conversacion.GetEventHandler().ProcessEvent(ctrl_c)
        self.assertEqual([llamada.args[0]
                          for llamada in anunciar.call_args_list],
                         [ventana_ia.FILA_GUIA, ventana_ia.FILA_GUIA])
        copiar.assert_not_called()
        mensaje.assert_not_called()

    def test_la_orilla_suena_en_la_conversacion(self):
        dialogo = self._ventana()
        dialogo._charla.agregar_captura(b"j", "Fuente", "10:00")
        dialogo._rehacer_lista()
        dialogo.lst_conversacion.SetSelection(0)
        evento = wx.KeyEvent(wx.wxEVT_KEY_DOWN)
        evento.SetKeyCode(wx.WXK_UP)
        with mock.patch.object(lista_acciones._snd, "reproducir") as sonar:
            dialogo.lst_conversacion.GetEventHandler().ProcessEvent(evento)
        sonar.assert_called_once_with("orilla")

    def test_tecla_aplicaciones_abre_el_menu_con_las_tres_acciones(self):
        dialogo = self._ventana()
        dialogo._charla.agregar_captura(b"j", "Fuente", "10:00")
        dialogo._rehacer_lista()
        vistos = []

        def _popup(menu):
            vistos.extend((item.GetItemLabel(), item.IsEnabled())
                          for item in menu.GetMenuItems())

        evento = wx.KeyEvent(wx.wxEVT_KEY_DOWN)
        evento.SetKeyCode(wx.WXK_WINDOWS_MENU)
        with mock.patch.object(dialogo.lst_conversacion, "PopupMenu",
                               side_effect=_popup) as popup:
            dialogo.lst_conversacion.GetEventHandler().ProcessEvent(evento)
        popup.assert_called_once()
        self.assertEqual(vistos, [("Ver mensaje completo…\tEnter", True),
                                  ("Copiar mensaje\tCtrl+C", True),
                                  ("Guardar conversación…\tCtrl+S", True)])

    def test_ctrl_s_en_la_lista_guarda_la_conversacion(self):
        dialogo = self._ventana()
        dialogo._charla.agregar_captura(b"j", "Fuente", "10:00")
        dialogo._charla.confirmar("pregunta", "respuesta")
        dialogo._rehacer_lista()
        evento = wx.KeyEvent(wx.wxEVT_KEY_DOWN)
        evento.SetKeyCode(ord("S"))
        evento.SetControlDown(True)
        with mock.patch.object(guardar_conv, "guardar") as guardar:
            dialogo.lst_conversacion.GetEventHandler().ProcessEvent(evento)
        guardar.assert_called_once_with(dialogo, dialogo._charla)

    def test_conversacion_vacia_sigue_en_el_menu_y_dice_el_motivo(self):
        dialogo = self._ventana()
        evento = wx.KeyEvent(wx.wxEVT_KEY_DOWN)
        evento.SetKeyCode(ord("s"))
        evento.SetControlDown(True)
        with mock.patch.object(guardar_conv, "guardar") as guardar, \
                mock.patch.object(lista_acciones, "anunciar") as anunciar:
            dialogo.lst_conversacion.GetEventHandler().ProcessEvent(evento)
        guardar.assert_not_called()
        anunciar.assert_called_once_with("La conversación está vacía.")
        vistos = []

        def _popup(menu):
            vistos.extend((item.GetItemLabel(), item.IsEnabled())
                          for item in menu.GetMenuItems())

        menu_evento = wx.KeyEvent(wx.wxEVT_KEY_DOWN)
        menu_evento.SetKeyCode(wx.WXK_WINDOWS_MENU)
        with mock.patch.object(dialogo.lst_conversacion, "PopupMenu",
                               side_effect=_popup):
            dialogo.lst_conversacion.GetEventHandler().ProcessEvent(
                menu_evento)
        self.assertIn(
            ("Guardar conversación… (la conversación está vacía)\tCtrl+S",
             True), vistos)

    def test_rehacer_lista_elige_la_ultima_fila(self):
        dialogo = self._ventana()
        dialogo._charla.confirmar("pregunta", "respuesta")
        dialogo._rehacer_lista()
        self.assertEqual(dialogo.lst_conversacion.GetCount(), 2)
        self.assertEqual(dialogo.lst_conversacion.GetSelection(), 1)
        self.assertEqual(dialogo.lst_conversacion.GetString(1),
                         "Respuesta: respuesta")

    def test_ctrl_c_copia_el_texto_de_la_fila_elegida(self):
        dialogo = self._ventana()
        dialogo._charla.agregar_captura(b"j", "Fuente", "10:00")
        dialogo._charla.confirmar("pregunta", "respuesta final")
        dialogo._rehacer_lista()
        self.assertEqual(dialogo.lst_conversacion.GetCount(), 3)
        dialogo.lst_conversacion.SetSelection(1)
        esperado = dialogo.lst_conversacion.GetString(1)
        falso = PortapapelesDoble()
        evento = wx.KeyEvent(wx.wxEVT_KEY_DOWN)
        evento.SetKeyCode(ord("C"))
        evento.SetControlDown(True)
        with mock.patch.object(ventana.wx, "TheClipboard", falso), \
                mock.patch.object(ventana, "anunciar") as anunciar, \
                mock.patch.object(ventana, "reproducir") as sonar:
            dialogo.lst_conversacion.GetEventHandler().ProcessEvent(evento)
        self.assertEqual(falso.texto, esperado)
        sonar.assert_called_once_with("copiar")
        anunciar.assert_called_once_with("Respuesta copiada.")

    def test_dialogo_mensaje_accesible_y_escape_cierra(self):
        dialogo = self._ventana()
        detalle = ventana.DialogoMensaje(dialogo, "texto largo")
        self.addCleanup(destruir, detalle)
        self.assertEqual(detalle.txt.GetName(), "Mensaje completo")
        estilo = detalle.txt.GetWindowStyleFlag()
        self.assertTrue(estilo & wx.TE_MULTILINE)
        self.assertTrue(estilo & wx.TE_READONLY)
        evento = mock.Mock()
        evento.GetKeyCode.return_value = wx.WXK_ESCAPE
        with mock.patch.object(detalle, "EndModal") as fin:
            detalle._al_tecla(evento)
        fin.assert_called_once_with(wx.ID_CANCEL)

    def test_enviar_sin_captura_anuncia_y_no_envia(self):
        dialogo = self._ventana()
        dialogo.txt_mensaje.ChangeValue("¿qué se ve?")
        envio = mock.Mock()
        with mock.patch.object(ventana.ajustes_ia, "leer",
                               return_value=_ajustes_falsos()), \
                mock.patch.object(ventana.catalogo, "cargar",
                                   return_value={}), \
                mock.patch.object(ventana.claves, "leer",
                                   return_value="clave"), \
                mock.patch.object(ventana.consulta, "preparar",
                                   side_effect=conversacion.SinCaptura("x")), \
                mock.patch.object(ventana.envio_ia, "enviar", envio), \
                mock.patch.object(ventana, "anunciar") as anunciar, \
                mock.patch.object(ventana, "reproducir") as sonar:
            dialogo._al_enviar(None)
        anunciar.assert_called_once_with(
            "Agrega una captura antes de preguntar.")
        sonar.assert_called_once_with("ia_error")
        envio.assert_not_called()
        self.assertIs(dialogo.FindFocus(), dialogo.txt_mensaje)

    def test_sin_aceptar_privacidad_no_envia_ni_suena(self):
        dialogo = self._ventana()
        dialogo._charla.agregar_captura(b"j", "Fuente", "10:00")
        dialogo.txt_mensaje.ChangeValue("¿qué se ve?")
        preparada = consulta.Preparada(object(), "¿qué se ve?", 60)
        with mock.patch.object(ventana.ajustes_ia, "leer",
                               return_value=_ajustes_falsos(
                                   privacidad_aceptada=False)), \
                mock.patch.object(ventana.catalogo, "cargar",
                                   return_value={}), \
                mock.patch.object(ventana.claves, "leer",
                                   return_value="clave"), \
                mock.patch.object(ventana.consulta, "preparar",
                                   return_value=preparada), \
                mock.patch.object(ventana.ia_privacidad.confirmaciones,
                                   "preguntar", return_value=False), \
                mock.patch.object(ventana.ia_privacidad.ajustes_ia,
                                   "guardar_privacidad_aceptada") as guardar, \
                mock.patch.object(ventana.diagnostico,
                                   "crear_hilo") as hilo, \
                mock.patch.object(ventana, "anunciar") as anunciar, \
                mock.patch.object(ventana, "reproducir") as sonar:
            dialogo._al_enviar(None)
        hilo.assert_not_called()
        guardar.assert_not_called()
        sonar.assert_not_called()
        anunciar.assert_not_called()
        self.assertFalse(dialogo._en_curso)
        self.assertIs(dialogo.FindFocus(), dialogo.txt_mensaje)

    def test_aceptar_privacidad_guarda_y_envia(self):
        dialogo = self._ventana()
        dialogo._charla.agregar_captura(b"j", "Fuente", "10:00")
        dialogo.txt_mensaje.ChangeValue("¿qué se ve?")
        preparada = consulta.Preparada(object(), "¿qué se ve?", 60)
        respuesta = protocolos.Respuesta("Se ve bien.", False)
        with mock.patch.object(ventana.ajustes_ia, "leer",
                               return_value=_ajustes_falsos(
                                   privacidad_aceptada=False)), \
                mock.patch.object(ventana.catalogo, "cargar",
                                   return_value={}), \
                mock.patch.object(ventana.claves, "leer",
                                   return_value="clave"), \
                mock.patch.object(ventana.consulta, "preparar",
                                   return_value=preparada), \
                mock.patch.object(ventana.envio_ia, "enviar",
                                   return_value=respuesta), \
                mock.patch.object(ventana.ia_privacidad.confirmaciones,
                                   "preguntar", return_value=True), \
                mock.patch.object(ventana.ia_privacidad.ajustes_ia,
                                   "guardar_privacidad_aceptada",
                                   return_value=True) as guardar, \
                mock.patch.object(ventana, "anunciar"), \
                mock.patch.object(ventana, "reproducir") as sonar:
            dialogo._al_enviar(None)
        guardar.assert_called_once_with(ventana.paths.config_ini(), True)
        sonar.assert_any_call("ia_enviada")
        self.assertEqual(dialogo.lst_conversacion.GetCount(), 3)

    def test_privacidad_ya_aceptada_no_muestra_aviso(self):
        dialogo = self._ventana()
        dialogo._charla.agregar_captura(b"j", "Fuente", "10:00")
        dialogo.txt_mensaje.ChangeValue("¿qué se ve?")
        preparada = consulta.Preparada(object(), "¿qué se ve?", 60)
        respuesta = protocolos.Respuesta("Se ve bien.", False)
        with mock.patch.object(ventana.ajustes_ia, "leer",
                               return_value=_ajustes_falsos()), \
                mock.patch.object(ventana.catalogo, "cargar",
                                   return_value={}), \
                mock.patch.object(ventana.claves, "leer",
                                   return_value="clave"), \
                mock.patch.object(ventana.consulta, "preparar",
                                   return_value=preparada), \
                mock.patch.object(ventana.envio_ia, "enviar",
                                   return_value=respuesta), \
                mock.patch.object(ventana.ia_privacidad.confirmaciones,
                                   "preguntar") as caja, \
                mock.patch.object(ventana, "anunciar"), \
                mock.patch.object(ventana, "reproducir"):
            dialogo._al_enviar(None)
        caja.assert_not_called()
        self.assertEqual(dialogo.lst_conversacion.GetCount(), 3)

    def test_captura_agregada_aparece_y_se_anuncia(self):
        dialogo = self._ventana()
        captura = SimpleNamespace(jpeg=b"jpg-falso")

        def _pedir(padre, al_terminar):
            al_terminar(("Cámara", captura))

        class _Gestor:
            def conectar(self):
                pass

            def descripcion_escena(self):
                return "Escena con una cámara."

            def cerrar(self):
                pass

        with mock.patch.object(ventana, "pedir_captura",
                               side_effect=_pedir), \
                mock.patch.object(ventana, "GestorPanelObs",
                                   return_value=_Gestor()):
            orden = mock.Mock()
            with mock.patch.object(ventana, "anunciar", orden.anunciar), \
                    mock.patch.object(ventana, "reproducir", orden.sonar):
                dialogo._al_captura(None)
        self.assertEqual(dialogo.lst_conversacion.GetCount(), 1)
        self.assertTrue(dialogo.lst_conversacion.GetString(0).startswith(
            "Captura: Cámara, "))
        self.assertEqual(
            orden.mock_calls,
            [mock.call.sonar("ia_captura"),
             mock.call.anunciar("Captura agregada: Cámara.")])
        self.assertEqual(dialogo._descripcion, "Escena con una cámara.")
        self.assertIs(dialogo.FindFocus(), dialogo.txt_mensaje)

    def test_envio_bueno_deja_dos_filas_anuncia_y_suena(self):
        dialogo = self._ventana()
        dialogo._charla.agregar_captura(b"j", "Fuente", "10:00")
        dialogo.txt_mensaje.ChangeValue("¿qué se ve?")
        preparada = consulta.Preparada(object(), "¿qué se ve?", 60)
        respuesta = protocolos.Respuesta("Se ve bien.", False)
        with mock.patch.object(ventana.ajustes_ia, "leer",
                               return_value=_ajustes_falsos()), \
                mock.patch.object(ventana.catalogo, "cargar",
                                   return_value={}), \
                mock.patch.object(ventana.claves, "leer",
                                   return_value="clave"), \
                mock.patch.object(ventana.consulta, "preparar",
                                   return_value=preparada), \
                mock.patch.object(ventana.envio_ia, "enviar",
                                   return_value=respuesta), \
                mock.patch.object(ventana, "anunciar") as anunciar, \
                mock.patch.object(ventana, "reproducir") as sonar:
            dialogo._al_enviar(None)
        self.assertEqual(dialogo.lst_conversacion.GetCount(), 3)
        self.assertEqual(dialogo.lst_conversacion.GetString(2),
                         "Respuesta: Se ve bien.")
        anunciar.assert_called_once_with("Se ve bien.")
        sonar.assert_any_call("ia_enviada")
        sonar.assert_any_call("ia_respuesta")
        self.assertEqual(dialogo.txt_mensaje.GetValue(), "")
        self.assertEqual(dialogo.lst_conversacion.GetSelection(), 2)

    def test_error_de_cuota_anuncia_su_frase_y_no_agrega(self):
        dialogo = self._ventana()
        dialogo._charla.agregar_captura(b"j", "Fuente", "10:00")
        dialogo.txt_mensaje.ChangeValue("¿qué se ve?")
        preparada = consulta.Preparada(object(), "¿qué se ve?", 60)
        fallo = protocolos.ErrorIA(protocolos.CUOTA, "sin saldo")
        with mock.patch.object(ventana.ajustes_ia, "leer",
                               return_value=_ajustes_falsos()), \
                mock.patch.object(ventana.catalogo, "cargar",
                                   return_value={}), \
                mock.patch.object(ventana.claves, "leer",
                                   return_value="clave"), \
                mock.patch.object(ventana.consulta, "preparar",
                                   return_value=preparada), \
                mock.patch.object(ventana.envio_ia, "enviar",
                                   side_effect=fallo), \
                mock.patch.object(ventana, "anunciar") as anunciar, \
                mock.patch.object(ventana, "reproducir") as sonar:
            dialogo._al_enviar(None)
        anunciar.assert_called_once_with(
            "Se agotó la cuota del proveedor. Espera unos minutos "
            "o elige otro modelo.")
        self.assertEqual(sonar.mock_calls, [mock.call("ia_enviada"),
                                            mock.call("ia_error")])
        self.assertEqual(dialogo.lst_conversacion.GetCount(), 1)
        self.assertEqual(dialogo.txt_mensaje.GetValue(), "¿qué se ve?")

    def test_resultado_tras_cancelar_no_agrega_ni_anuncia(self):
        dialogo = self._ventana()
        dialogo._charla.agregar_captura(b"j", "Fuente", "10:00")
        dialogo.txt_mensaje.ChangeValue("¿qué se ve?")
        preparada = consulta.Preparada(object(), "¿qué se ve?", 60)
        respuesta = protocolos.Respuesta("Tarde.", False)
        guardadas = []

        def _hilo_guardado(target, nombre, **kwargs):
            guardadas.append((target, kwargs.get("args", ())))
            hilo = mock.Mock()
            hilo.start.return_value = None
            return hilo

        evento = mock.Mock()
        evento.GetKeyCode.return_value = wx.WXK_ESCAPE
        with mock.patch.object(ventana.ajustes_ia, "leer",
                               return_value=_ajustes_falsos()), \
                mock.patch.object(ventana.catalogo, "cargar",
                                   return_value={}), \
                mock.patch.object(ventana.claves, "leer",
                                   return_value="clave"), \
                mock.patch.object(ventana.consulta, "preparar",
                                   return_value=preparada), \
                mock.patch.object(ventana.envio_ia, "enviar",
                                   return_value=respuesta), \
                mock.patch.object(ventana.diagnostico, "crear_hilo",
                                   side_effect=_hilo_guardado), \
                mock.patch.object(ventana, "anunciar") as anunciar, \
                mock.patch.object(ventana, "reproducir") as sonar, \
                mock.patch.object(dialogo, "EndModal") as fin:
            dialogo._al_enviar(None)
            self.assertEqual(len(guardadas), 1)
            dialogo._al_tecla(evento)
            fin.assert_not_called()
            destino, args = guardadas[0]
            destino(*args)
        anunciar.assert_called_once_with(ventana_ia.TEXTO_CANCELADA)
        self.assertEqual(sonar.mock_calls, [mock.call("ia_enviada"),
                                            mock.call("ia_cancelada")])
        self.assertEqual(dialogo.lst_conversacion.GetCount(), 1)

    def test_escape_sin_consulta_cierra_sin_sonar(self):
        dialogo = self._ventana()
        evento = mock.Mock()
        evento.GetKeyCode.return_value = wx.WXK_ESCAPE
        with mock.patch.object(dialogo, "EndModal") as fin, \
                mock.patch.object(ventana, "reproducir") as sonar:
            dialogo._al_tecla(evento)
        fin.assert_called_once_with(wx.ID_CLOSE)
        sonar.assert_not_called()

    def test_enviar_y_captura_siguen_habilitados_mientras_espera(self):
        dialogo, _guardadas = self._enviar_en_curso()
        self.assertTrue(dialogo._en_curso)
        self.assertTrue(dialogo.btn_enviar.IsEnabled())
        self.assertTrue(dialogo.btn_captura.IsEnabled())

    def test_etiquetas_llevan_el_motivo_solo_mientras_espera(self):
        dialogo = self._ventana()
        self.assertEqual(dialogo.btn_enviar.GetLabel(), "&Enviar")
        self.assertEqual(dialogo.btn_captura.GetLabel(), "Agregar &captura")
        dialogo, _guardadas = self._enviar_en_curso()
        self.assertEqual(dialogo.btn_enviar.GetLabel(),
                         "&Enviar (esperando la respuesta)")
        self.assertEqual(dialogo.btn_captura.GetLabel(),
                         "Agregar &captura (esperando la respuesta)")

    def test_enviar_con_consulta_en_curso_anuncia_y_no_lanza_otra(self):
        dialogo, _guardadas = self._enviar_en_curso()
        with mock.patch.object(ventana.diagnostico, "crear_hilo") as hilo, \
                mock.patch.object(ventana.consulta, "preparar") as preparar, \
                mock.patch.object(ventana, "anunciar") as anunciar:
            dialogo._al_enviar(None)
        preparar.assert_not_called()
        hilo.assert_not_called()
        anunciar.assert_called_once_with("Esperando la respuesta.")
        self.assertEqual(dialogo._n_consulta, 0)

    def test_intro_en_el_mensaje_espera_y_no_lanza_otra(self):
        dialogo, _guardadas = self._enviar_en_curso()
        evento = wx.CommandEvent(wx.EVT_TEXT_ENTER.typeId,
                                 dialogo.txt_mensaje.GetId())
        with mock.patch.object(ventana.diagnostico, "crear_hilo") as hilo, \
                mock.patch.object(ventana.consulta, "preparar") as preparar, \
                mock.patch.object(ventana, "anunciar") as anunciar:
            dialogo.txt_mensaje.GetEventHandler().ProcessEvent(evento)
        preparar.assert_not_called()
        hilo.assert_not_called()
        anunciar.assert_called_once_with("Esperando la respuesta.")

    def test_captura_con_consulta_en_curso_anuncia_y_no_abre_el_cuadro(self):
        dialogo, _guardadas = self._enviar_en_curso()
        with mock.patch.object(ventana, "pedir_captura") as pedir, \
                mock.patch.object(ventana, "anunciar") as anunciar:
            dialogo._al_captura(None)
        pedir.assert_not_called()
        anunciar.assert_called_once_with("Esperando la respuesta.")

    def test_al_terminar_bien_las_etiquetas_vuelven_a_la_base(self):
        dialogo, guardadas = self._enviar_en_curso()
        self.assertEqual(dialogo.btn_enviar.GetLabel(),
                         "&Enviar (esperando la respuesta)")
        self._completar(guardadas)
        self.assertEqual(dialogo.btn_enviar.GetLabel(), "&Enviar")
        self.assertEqual(dialogo.btn_captura.GetLabel(), "Agregar &captura")
        self.assertTrue(dialogo.btn_enviar.IsEnabled())
        self.assertTrue(dialogo.btn_captura.IsEnabled())

    def test_al_fallar_las_etiquetas_vuelven_a_la_base(self):
        fallo = protocolos.ErrorIA(protocolos.CUOTA, "sin saldo")
        dialogo, guardadas = self._enviar_en_curso(fallo=fallo)
        self.assertEqual(dialogo.btn_enviar.GetLabel(),
                         "&Enviar (esperando la respuesta)")
        self._completar(guardadas)
        self.assertEqual(dialogo.btn_enviar.GetLabel(), "&Enviar")
        self.assertEqual(dialogo.btn_captura.GetLabel(), "Agregar &captura")

    def test_al_cancelar_con_escape_las_etiquetas_vuelven_a_la_base(self):
        dialogo, _guardadas = self._enviar_en_curso()
        self.assertEqual(dialogo.btn_enviar.GetLabel(),
                         "&Enviar (esperando la respuesta)")
        evento = mock.Mock()
        evento.GetKeyCode.return_value = wx.WXK_ESCAPE
        with mock.patch.object(dialogo, "EndModal") as fin:
            dialogo._al_tecla(evento)
        fin.assert_not_called()
        self.assertFalse(dialogo._en_curso)
        self.assertEqual(dialogo.btn_enviar.GetLabel(), "&Enviar")
        self.assertEqual(dialogo.btn_captura.GetLabel(), "Agregar &captura")

    def test_copiar_respuesta_pone_texto_y_avisa(self):
        dialogo = self._ventana()
        dialogo._charla.agregar_captura(b"j", "Fuente", "10:00")
        dialogo._charla.confirmar("hola", "respuesta final")
        falso = PortapapelesDoble()
        with mock.patch.object(ventana.wx, "TheClipboard", falso), \
                mock.patch.object(ventana, "anunciar") as anunciar, \
                mock.patch.object(ventana, "reproducir") as sonar:
            dialogo._al_copiar(None)
        self.assertEqual(falso.texto, "respuesta final")
        sonar.assert_called_once_with("copiar")
        anunciar.assert_called_once_with("Respuesta copiada.")

    def test_copiar_si_no_abre_avisa_fallo(self):
        dialogo = self._ventana()
        dialogo._charla.agregar_captura(b"j", "Fuente", "10:00")
        dialogo._charla.confirmar("hola", "respuesta final")

        class _Cerrado:
            def Open(self):
                return False

        with mock.patch.object(ventana.wx, "TheClipboard", _Cerrado()), \
                mock.patch.object(ventana, "anunciar") as anunciar, \
                mock.patch.object(ventana, "reproducir") as sonar:
            dialogo._al_copiar(None)
        sonar.assert_called_once_with("ia_error")
        anunciar.assert_called_once_with(ventana_ia.TEXTO_NO_COPIADA)

    def test_copiar_sin_respuesta_avisa_sin_sonido(self):
        dialogo = self._ventana()
        with mock.patch.object(ventana, "anunciar") as anunciar, \
                mock.patch.object(ventana, "reproducir") as sonar:
            dialogo._al_copiar(None)
        anunciar.assert_called_once_with(
            "Todavía no hay ninguna respuesta.")
        sonar.assert_not_called()

    def test_nueva_conversacion_vacia_y_anuncia(self):
        dialogo = self._ventana()
        dialogo._charla.agregar_captura(b"j", "Fuente", "10:00")
        dialogo._descripcion = "algo"
        dialogo._rehacer_lista()
        with mock.patch.object(ventana, "anunciar") as anunciar, \
                mock.patch.object(ventana, "reproducir") as sonar:
            dialogo._al_nueva(None)
        self.assertEqual(dialogo.lst_conversacion.GetCount(), 1)
        self.assertEqual(dialogo.lst_conversacion.GetString(0),
                         ventana_ia.FILA_GUIA)
        self.assertEqual(dialogo._descripcion, "")
        anunciar.assert_called_once_with("Conversación nueva.")
        sonar.assert_not_called()
        self.assertIs(dialogo.FindFocus(), dialogo.txt_mensaje)

    def test_la_ventana_no_tiene_casilla_de_analizando(self):
        dialogo = self._ventana()
        self.assertFalse(hasattr(dialogo, "chk_analizando"))

    def test_no_queda_ningun_texto_visible_sin_envolver(self):
        with con_pseudo():
            dialogo = self._ventana()
            sin_marcar = textos_sin_marcar(dialogo)

        self.assertEqual([], sin_marcar)

    def test_detalle_sin_texto_visible_sin_envolver(self):
        with con_pseudo():
            dialogo = self._ventana()
            detalle = ventana.DialogoMensaje(dialogo, "texto largo")
            self.addCleanup(destruir, detalle)
            sin_marcar = textos_sin_marcar(detalle)

        self.assertEqual([], sin_marcar)

    def test_pseudo_temporizador_anuncia_marcado(self):
        dialogo = self._ventana()
        with con_pseudo(), \
                mock.patch.object(ventana, "anunciar") as anunciar:
            dialogo._al_temporizador(mock.Mock())
        args, kwargs = anunciar.call_args
        self.assertTrue(args[0].startswith("[¡"), args[0])
        self.assertEqual(kwargs, {"urgente": False})

    def test_pseudo_escape_en_curso_anuncia_marcado(self):
        dialogo = self._ventana()
        dialogo._en_curso = True
        evento = mock.Mock()
        evento.GetKeyCode.return_value = wx.WXK_ESCAPE
        with con_pseudo(), \
                mock.patch.object(ventana, "anunciar") as anunciar, \
                mock.patch.object(ventana, "reproducir"):
            dialogo._al_tecla(evento)
        args, _kwargs = anunciar.call_args
        self.assertTrue(args[0].startswith("[¡"), args[0])

    def test_pseudo_copiar_sin_respuesta_anuncia_marcado(self):
        dialogo = self._ventana()
        with con_pseudo(), \
                mock.patch.object(ventana, "anunciar") as anunciar:
            dialogo._al_copiar(None)
        args, _kwargs = anunciar.call_args
        self.assertTrue(args[0].startswith("[¡"), args[0])

    def test_pseudo_copiar_respuesta_anuncia_marcado(self):
        dialogo = self._ventana()
        dialogo._charla.agregar_captura(b"j", "Fuente", "10:00")
        dialogo._charla.confirmar("hola", "respuesta final")
        with con_pseudo(), \
                mock.patch.object(ventana.wx, "TheClipboard",
                                   PortapapelesDoble()), \
                mock.patch.object(ventana, "anunciar") as anunciar, \
                mock.patch.object(ventana, "reproducir"):
            dialogo._al_copiar(None)
        args, _kwargs = anunciar.call_args
        self.assertTrue(args[0].startswith("[¡"), args[0])

    def test_pseudo_nueva_conversacion_anuncia_marcado(self):
        dialogo = self._ventana()
        dialogo._charla.agregar_captura(b"j", "Fuente", "10:00")
        with con_pseudo(), \
                mock.patch.object(ventana, "anunciar") as anunciar:
            dialogo._al_nueva(None)
        args, _kwargs = anunciar.call_args
        self.assertTrue(args[0].startswith("[¡"), args[0])

    def test_pseudo_captura_agregada_anuncia_marcado(self):
        dialogo = self._ventana()
        captura = SimpleNamespace(jpeg=b"jpg-falso")

        def _pedir(padre, al_terminar):
            al_terminar(("Cámara", captura))

        class _Gestor:
            def conectar(self):
                pass

            def descripcion_escena(self):
                return "Escena con una cámara."

            def cerrar(self):
                pass

        with con_pseudo(), \
                mock.patch.object(ventana, "pedir_captura",
                                   side_effect=_pedir), \
                mock.patch.object(ventana, "GestorPanelObs",
                                   return_value=_Gestor()), \
                mock.patch.object(ventana, "anunciar") as anunciar, \
                mock.patch.object(ventana, "reproducir"):
            dialogo._al_captura(None)
        self.assertEqual(anunciar.call_count, 1)
        args, _kwargs = anunciar.call_args
        self.assertTrue(args[0].startswith("[¡"), args[0])

    def _enviar_con_ajuste(self, decir_analizando):
        dialogo = self._ventana()
        dialogo._charla.agregar_captura(b"j", "Fuente", "10:00")
        dialogo.txt_mensaje.ChangeValue("¿qué se ve?")
        preparada = consulta.Preparada(object(), "¿qué se ve?", 60)
        respuesta = protocolos.Respuesta("Se ve bien.", False)
        with mock.patch.object(ventana.ajustes_ia, "leer",
                               return_value=_ajustes_falsos(
                                   decir_analizando=decir_analizando)), \
                mock.patch.object(ventana.catalogo, "cargar",
                                   return_value={}), \
                mock.patch.object(ventana.claves, "leer",
                                   return_value="clave"), \
                mock.patch.object(ventana.consulta, "preparar",
                                   return_value=preparada), \
                mock.patch.object(ventana.envio_ia, "enviar",
                                   return_value=respuesta), \
                mock.patch.object(ventana, "anunciar"), \
                mock.patch.object(ventana, "reproducir"):
            dialogo._al_enviar(None)
        return dialogo

    def test_melodia_suena_ia_analizando(self):
        dialogo = self._ventana()
        with mock.patch.object(ventana, "reproducir") as sonar:
            dialogo._al_temporizador_melodia(mock.Mock())
        sonar.assert_called_once_with("ia_analizando")

    def test_el_aviso_analizando_lee_el_ajuste_del_envio(self):
        for valor in (False, True):
            with self.subTest(decir_analizando=valor):
                dialogo = self._enviar_con_ajuste(valor)
                self.assertIs(dialogo._decir_analizando, valor)
                with mock.patch.object(ventana, "anunciar") as anunciar:
                    dialogo._al_temporizador(mock.Mock())
                if valor:
                    anunciar.assert_called_once_with(
                        ventana_ia.TEXTO_ANALIZANDO, urgente=False)
                else:
                    anunciar.assert_not_called()

    def test_enviar_arranca_los_dos_avisos_y_al_llegar_paran(self):
        dialogo = self._ventana()
        dialogo._charla.agregar_captura(b"j", "Fuente", "10:00")
        dialogo.txt_mensaje.ChangeValue("¿qué se ve?")
        preparada = consulta.Preparada(object(), "¿qué se ve?", 60)
        respuesta = protocolos.Respuesta("Se ve bien.", False)
        guardadas = []

        def _hilo_guardado(target, nombre, **kwargs):
            guardadas.append((target, kwargs.get("args", ())))
            hilo = mock.Mock()
            hilo.start.return_value = None
            return hilo

        with mock.patch.object(ventana.ajustes_ia, "leer",
                               return_value=_ajustes_falsos()), \
                mock.patch.object(ventana.catalogo, "cargar",
                                   return_value={}), \
                mock.patch.object(ventana.claves, "leer",
                                   return_value="clave"), \
                mock.patch.object(ventana.consulta, "preparar",
                                   return_value=preparada), \
                mock.patch.object(ventana.envio_ia, "enviar",
                                   return_value=respuesta), \
                mock.patch.object(ventana.diagnostico, "crear_hilo",
                                   side_effect=_hilo_guardado), \
                mock.patch.object(ventana, "anunciar"), \
                mock.patch.object(ventana, "reproducir"):
            dialogo._al_enviar(None)
            self.assertTrue(dialogo._temporizador.IsRunning())
            self.assertTrue(dialogo._temporizador_melodia.IsRunning())
            destino, args = guardadas[0]
            destino(*args)
        self.assertFalse(dialogo._temporizador.IsRunning())
        self.assertFalse(dialogo._temporizador_melodia.IsRunning())

    def test_abre_con_area_cliente_de_al_menos_640_por_480(self):
        dialogo = self._ventana()
        cliente = dialogo.GetClientSize()
        self.assertGreaterEqual(cliente.width, 640)
        self.assertGreaterEqual(cliente.height, 480)

    def test_la_conversacion_crece_al_agrandar_la_ventana(self):
        dialogo = self._ventana()
        alto = dialogo.lst_conversacion.GetSize().height
        cliente = dialogo.GetClientSize()
        dialogo.SetClientSize((cliente.width + 120, cliente.height + 120))
        self.assertGreater(dialogo.lst_conversacion.GetSize().height, alto)

    def test_enviar_es_el_boton_por_defecto_y_principal(self):
        dialogo = self._ventana()
        self.assertIs(dialogo.GetDefaultItem(), dialogo.btn_enviar)
        self.assertEqual(dialogo.btn_enviar.GetBackgroundColour(),
                         tema._T.primary)
        self.assertEqual(dialogo.btn_enviar.GetForegroundColour(),
                         tema._T.primary_t)

    def test_hueco_entre_el_mensaje_y_las_acciones(self):
        dialogo = self._ventana()
        mensaje = dialogo.txt_mensaje
        self.assertEqual(
            dialogo.btn_enviar.GetPosition().y - (
                mensaje.GetPosition().y + mensaje.GetSize().height),
            formulario.CONTROL_A_ETIQUETA)

    def test_cerrar_va_en_el_pie_y_las_acciones_en_una_fila(self):
        dialogo = self._ventana()
        cliente = dialogo.GetClientSize()
        acciones = [dialogo.btn_enviar, dialogo.btn_captura,
                    dialogo.btn_copiar, dialogo.btn_nueva]
        self.assertEqual(len({boton.GetPosition().y for boton in acciones}), 1)
        self.assertEqual(len({boton.GetSize().width for boton in acciones}), 1)
        cerrar = dialogo.btn_cerrar
        self.assertGreater(cerrar.GetPosition().y, acciones[0].GetPosition().y)
        self.assertEqual(
            cliente.width - (cerrar.GetPosition().x + cerrar.GetSize().width),
            formulario.MARGEN)
        self.assertEqual(
            cliente.height - (cerrar.GetPosition().y + cerrar.GetSize().height),
            formulario.MARGEN)

    def test_margenes_y_huecos_son_del_formulario(self):
        dialogo = self._ventana()
        self.assertEqual(dialogo.lst_conversacion.GetPosition().x,
                         formulario.MARGEN)
        self.assertEqual(dialogo.rotulo_conv.GetPosition().x,
                         dialogo.lst_conversacion.GetPosition().x)
        self.assertEqual(
            dialogo.rotulo_msg.GetPosition().y
            + dialogo.rotulo_msg.GetSize().height,
            dialogo.txt_mensaje.GetPosition().y
            - formulario.ETIQUETA_A_CONTROL)


if __name__ == "__main__":
    unittest.main()
