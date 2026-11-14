# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas del cuadro Buscar en el chat.

Abren ventanas: quedan escritas para correrlas después. Toda ventana de
primer nivel se libera con `tests/ventanas_prueba.destruir`.
"""

import unittest
from unittest import mock

from guyrapu.core.avisos_tiktok import pasa_filtro
from guyrapu.core.config import TIPO_SUPERCHAT, TIPO_TEXTO
from guyrapu.ui import chat_acciones, chat_buscar
from guyrapu.ui.chat_vivo import ControladorChat
from guyrapu.ui.lista_chat import MensajeChat
from tests.ventanas_prueba import app_de_prueba, destruir

try:
    import wx
    _HAY_WX = True
except Exception:
    _HAY_WX = False


class Evento:
    """Doble mínimo de un evento de teclado de wx."""

    def __init__(self, keycode=0, mods=0):
        self._keycode = keycode
        self._mods = mods
        self.skipped = False

    def GetKeyCode(self):
        return self._keycode

    def GetModifiers(self):
        return self._mods

    def Skip(self):
        self.skipped = True


def _mensaje(autor="Ana", texto="hola", hora="12:00", tipo=TIPO_TEXTO):
    return MensajeChat(plataforma="youtube", autor=autor, identificador="C",
                       texto=texto, hora=hora, tipo=tipo, monto="", rol="")


@unittest.skipUnless(_HAY_WX, "wx no está instalado")
class TestCuadroBuscarChat(unittest.TestCase):

    def setUp(self):
        app_de_prueba()
        self.config = {"silenciados_ocultar": set()}
        self.frame = wx.Frame(None)
        self.lb = wx.ListBox(self.frame)
        self.chat = ControladorChat(
            self.lb, 500, activo=lambda: True,
            autor_oculto=lambda autor: (
                autor.lower().strip()
                in self.config["silenciados_ocultar"]),
            formatear=lambda autor, texto, hora, tipo, monto: (
                f"{autor}: {texto}, {hora}"),
            al_superchat=lambda monto: None, config=self.config)
        self.chat.filtro = TIPO_TEXTO
        self.acciones = chat_acciones.AccionesChat(
            self.lb, self.chat, mock.Mock(), self.config, lambda: None,
            self.frame)
        self.addCleanup(destruir, self.frame)

    def _agregar(self, mensaje):
        visible = pasa_filtro(self.chat.filtro, mensaje.tipo)
        self.chat.modelo.agregar(mensaje, visible)
        if visible:
            self.lb.Append(f"{mensaje.autor}: {mensaje.texto}, {mensaje.hora}")

    def _abrir(self):
        dialogo = chat_buscar.CuadroBuscarChat(self.frame, self.acciones)
        self.addCleanup(destruir, dialogo)
        return dialogo

    # ── Escribir filtra y anuncia ─────────────────────────────────────────

    def test_escribir_filtra_y_anuncia_cuantos_hay(self):
        self._agregar(_mensaje("Ana", "pregunta uno", "12:00"))
        self._agregar(_mensaje("Beto", "Pregunta dos", "12:01"))
        self._agregar(_mensaje("Carla", "otra cosa", "12:02"))
        dialogo = self._abrir()
        dialogo.txt_buscar.SetValue("PREGUNTA")
        with mock.patch.object(chat_buscar.wx, "CallLater") as diferir, \
                mock.patch.object(chat_buscar, "anunciar") as anunciar:
            dialogo._al_escribir(Evento())
            self.assertEqual(diferir.call_args.args[0], 700)
            dialogo._avisar_coincidencias()
        self.assertEqual(
            list(dialogo.lb_resultados.GetStrings()),
            ["Beto: Pregunta dos, 12:01", "Ana: pregunta uno, 12:00"])
        anunciar.assert_called_once_with("2 mensajes coinciden")

    def test_texto_vacio_muestra_la_ayuda(self):
        self._agregar(_mensaje("Ana", "hola", "12:00"))
        dialogo = self._abrir()
        self.assertTrue(dialogo.lista_vacia.vacia())
        self.assertEqual(dialogo.lb_resultados.GetString(0),
                         "Escribe para buscar en los mensajes del chat.")

    def test_sin_coincidencias_muestra_el_texto_buscado(self):
        self._agregar(_mensaje("Ana", "hola", "12:00"))
        dialogo = self._abrir()
        dialogo.txt_buscar.SetValue("zzz")
        dialogo._al_escribir(Evento())
        self.assertTrue(dialogo.lista_vacia.vacia())
        self.assertEqual(dialogo.lb_resultados.GetString(0),
                         "No hay mensajes con «zzz».")

    # ── Intro lleva al mensaje en la lista del chat ──────────────────────

    def test_intro_enfoca_el_mensaje_que_el_filtro_de_tipo_ocultaba(self):
        visible = _mensaje("Ana", "pregunta uno", "12:00")
        superchat = _mensaje("Beto", "pregunta dos", "12:01", TIPO_SUPERCHAT)
        self._agregar(visible)
        self._agregar(superchat)
        dialogo = self._abrir()
        dialogo.txt_buscar.SetValue("dos")
        dialogo._al_escribir(Evento())
        dialogo.lb_resultados.SetSelection(0)
        with mock.patch.object(dialogo, "EndModal") as cerrar, \
                mock.patch.object(chat_acciones, "guardar_opcion"), \
                mock.patch.object(chat_acciones, "anunciar"):
            dialogo._elegir(Evento(wx.WXK_RETURN))

        cerrar.assert_called_once_with(wx.ID_OK)
        self.assertIsNone(self.chat.filtro)
        self.assertIs(self.chat.modelo.dato_en_fila(self.lb.GetSelection()),
                      superchat)
        self.assertIs(wx.Window.FindFocus(), self.lb)

    def test_intro_con_un_mensaje_que_ya_salio_no_cierra(self):
        self._agregar(_mensaje("Ana", "pregunta uno", "12:00"))
        dialogo = self._abrir()
        dialogo.txt_buscar.SetValue("uno")
        dialogo._al_escribir(Evento())
        self.chat.modelo.todos.clear()
        dialogo.lb_resultados.SetSelection(0)
        with mock.patch.object(dialogo, "EndModal") as cerrar, \
                mock.patch.object(chat_acciones, "anunciar") as anunciar:
            dialogo._elegir(Evento(wx.WXK_RETURN))

        cerrar.assert_not_called()
        anunciar.assert_called_once_with("Ese mensaje ya no está en el chat.")

    # ── Escape borra y después cierra ────────────────────────────────────

    def test_escape_con_texto_lo_borra(self):
        self._agregar(_mensaje("Ana", "hola", "12:00"))
        dialogo = self._abrir()
        dialogo.txt_buscar.SetValue("hola")
        dialogo._al_escribir(Evento())
        with mock.patch.object(chat_buscar, "anunciar") as anunciar:
            dialogo._tecla_dialogo(Evento(wx.WXK_ESCAPE))
        self.assertEqual(dialogo.txt_buscar.GetValue(), "")
        self.assertEqual(dialogo.lb_resultados.GetString(0),
                         "Escribe para buscar en los mensajes del chat.")
        anunciar.assert_called_once_with("Búsqueda vaciada")

    def test_escape_con_el_campo_vacio_cierra(self):
        dialogo = self._abrir()
        with mock.patch.object(dialogo, "EndModal") as cerrar:
            dialogo._tecla_dialogo(Evento(wx.WXK_ESCAPE))
        cerrar.assert_called_once_with(wx.ID_CANCEL)

    # ── Autores ocultos ───────────────────────────────────────────────────

    def test_los_mensajes_de_autores_ocultos_no_aparecen(self):
        self.config["silenciados_ocultar"] = {"ana"}
        self._agregar(_mensaje("Ana", "secreto", "12:00"))
        self._agregar(_mensaje("Beto", "secreto", "12:01"))
        dialogo = self._abrir()
        dialogo.txt_buscar.SetValue("secreto")
        dialogo._al_escribir(Evento())
        self.assertEqual(list(dialogo.lb_resultados.GetStrings()),
                         ["Beto: secreto, 12:01"])

    # ── Accesibilidad ──────────────────────────────────────────────────────

    def test_nombres_y_orden_de_tab(self):
        dialogo = self._abrir()
        controles = [
            control for control in dialogo._panel.GetChildren()
            if isinstance(control, (wx.TextCtrl, wx.ListBox, wx.Button))]
        self.assertEqual([control.GetName() for control in controles],
                         ["Buscar en el chat", "Resultados", "Cerrar"])
        self.assertIs(dialogo.FindFocus(), dialogo.txt_buscar)

    def test_letras_de_acceso_sin_repetir(self):
        dialogo = self._abrir()
        etiquetas = [
            control.GetLabel() for control in dialogo._panel.GetChildren()
            if isinstance(control, (wx.StaticText, wx.Button))]
        letras = [etiqueta[etiqueta.index("&") + 1].lower()
                  for etiqueta in etiquetas if "&" in etiqueta]
        self.assertEqual(len(letras), len(set(letras)))
        self.assertEqual(letras, ["b", "r", "c"])


if __name__ == "__main__":
    unittest.main()
