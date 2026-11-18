# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de la ventana de participación en el chat.

Abren ventanas: quedan escritas para correrlas en la PC de pruebas. Toda
ventana de primer nivel se libera con `tests/ventanas_prueba.destruir`.
"""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from guyrapu.core.config import TIPO_SUPERCHAT, TIPO_TEXTO
from guyrapu.ui import chat_acciones, chat_participacion
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

    def __init__(self, keycode=0):
        self._keycode = keycode
        self.skipped = False

    def GetKeyCode(self):
        return self._keycode

    def Skip(self):
        self.skipped = True


def _mensaje(autor="Ana", identificador="C", tipo=TIPO_TEXTO, monto=""):
    return MensajeChat(plataforma="youtube", autor=autor,
                       identificador=identificador, texto="hola",
                       hora="12:00", tipo=tipo, monto=monto, rol="")


@unittest.skipUnless(_HAY_WX, "wx no está instalado")
class TestVentanaParticipacion(unittest.TestCase):

    def setUp(self):
        app_de_prueba()
        self.frame = wx.Frame(None)
        self.lb = wx.ListBox(self.frame)
        self.chat = ControladorChat(
            self.lb, 500, activo=lambda: True,
            autor_oculto=lambda autor: False,
            formatear=lambda *args: "", al_superchat=lambda monto: None)
        self.acciones = chat_acciones.AccionesChat(
            self.lb, self.chat, mock.Mock(), {}, lambda: None, self.frame)
        self.addCleanup(destruir, self.frame)

    def _sumar(self, autor="Ana", identificador="C"):
        self.chat.participacion.sumar(_mensaje(autor, identificador))

    def _sumar_regalo(self, autor, identificador, monto):
        self.chat.participacion.sumar(_mensaje(
            autor, identificador, TIPO_SUPERCHAT, monto))

    def _abrir(self):
        dialogo = chat_participacion.VentanaParticipacion(
            self.frame, self.acciones)
        self.addCleanup(destruir, dialogo)
        return dialogo

    def _cuadro_archivo(self, ruta):
        cuadro = mock.MagicMock()
        cuadro.ShowModal.return_value = wx.ID_OK
        cuadro.GetPath.return_value = str(ruta)
        crear = mock.patch.object(chat_participacion.wx, "FileDialog",
                                  return_value=cuadro)
        parche = crear.start()
        self.addCleanup(parche.stop)
        cuadro.__enter__.return_value = cuadro
        return cuadro

    def test_el_foco_queda_en_la_lista_al_abrir(self):
        self._sumar()
        dialogo = self._abrir()
        self.assertIs(dialogo.FindFocus(), dialogo.lb_participacion)

    def test_la_lista_tiene_el_nombre_accesible_exacto(self):
        dialogo = self._abrir()
        self.assertEqual(dialogo.lb_participacion.GetName(), "Participación")

    def test_sin_mensajes_muestra_la_linea_vacia(self):
        dialogo = self._abrir()
        self.assertTrue(dialogo.lista_vacia.vacia())
        self.assertEqual(dialogo.lb_participacion.GetString(0),
                         "Todavía no hay mensajes en este directo.")

    def test_muestra_las_lineas_ordenadas(self):
        self._sumar("Beto", "B")
        self._sumar("Ana", "A")
        self._sumar("Ana", "A")
        dialogo = self._abrir()
        self.assertEqual(list(dialogo.lb_participacion.GetStrings()),
                         ["Ana: 2 mensajes", "Beto: 1 mensaje"])

    def test_el_cuadro_de_orden_existe_con_su_nombre(self):
        dialogo = self._abrir()
        self.assertEqual(dialogo.cb_orden.GetName(), "Ordenar por")
        self.assertEqual(list(dialogo.cb_orden.GetStrings()),
                         ["Mensajes", "Regalos"])

    def test_el_boton_de_resumenes_existe_con_su_nombre(self):
        dialogo = self._abrir()
        self.assertEqual(dialogo.btn_resumenes.GetName(),
                         "Abrir carpeta de resúmenes")

    def test_cambiar_el_orden_reordena_y_deja_el_foco_en_la_lista(self):
        self._sumar("Ana", "A")
        self._sumar_regalo("Beto", "B", "200 diamantes")
        self._sumar_regalo("Carla", "C", "US$50.00")
        dialogo = self._abrir()
        self.assertEqual(list(dialogo.lb_participacion.GetStrings()),
                         ["Ana: 1 mensaje",
                          "Beto: 1 mensaje, 200 diamantes",
                          "Carla: 1 mensaje, 50,00 US$"])
        dialogo.cb_orden.SetSelection(1)
        dialogo._cambiar_orden()
        self.assertEqual(list(dialogo.lb_participacion.GetStrings()),
                         ["Beto: 1 mensaje, 200 diamantes",
                          "Carla: 1 mensaje, 50,00 US$",
                          "Ana: 1 mensaje"])
        self.assertIs(dialogo.FindFocus(), dialogo.lb_participacion)
        self.assertEqual(dialogo.lb_participacion.GetSelection(), 0)

    def test_abrir_resumenes_usa_el_explorador(self):
        temporal = tempfile.TemporaryDirectory()
        self.addCleanup(temporal.cleanup)
        carpeta = Path(temporal.name) / "resumenes_sesion"
        dialogo = self._abrir()
        with mock.patch.object(chat_participacion.paths, "resumenes_sesion",
                               return_value=carpeta), \
                mock.patch.object(chat_participacion.os, "startfile") as abrir:
            dialogo._abrir_resumenes()
        abrir.assert_called_once_with(str(carpeta))
        self.assertTrue(carpeta.is_dir())

    def test_guarda_las_lineas_y_anuncia(self):
        self._sumar("Ana", "A")
        self._sumar("Ana", "A")
        self._sumar("Beto", "B")
        temporal = tempfile.TemporaryDirectory()
        self.addCleanup(temporal.cleanup)
        ruta = Path(temporal.name) / "participacion.txt"
        self._cuadro_archivo(ruta)
        dialogo = self._abrir()
        with mock.patch.object(chat_participacion._snd, "reproducir") as sonar, \
                mock.patch.object(chat_participacion, "anunciar") as anunciar:
            dialogo._guardar()
        self.assertEqual(ruta.read_text(encoding="utf-8"),
                         "Ana: 2 mensajes\nBeto: 1 mensaje\n")
        sonar.assert_called_once_with("listo")
        anunciar.assert_called_once_with("Participación guardada.")

    def test_guardar_vacio_no_abre_el_cuadro_y_lo_dice(self):
        dialogo = self._abrir()
        with mock.patch.object(chat_participacion.wx, "FileDialog") as crear, \
                mock.patch.object(chat_participacion, "anunciar") as anunciar:
            dialogo._guardar()
        crear.assert_not_called()
        anunciar.assert_called_once_with(
            "Todavía no hay mensajes en este directo.")

    def test_si_falla_avisa_con_el_sonido_de_error(self):
        self._sumar()
        temporal = tempfile.TemporaryDirectory()
        self.addCleanup(temporal.cleanup)
        self._cuadro_archivo(Path(temporal.name) / "participacion.txt")
        dialogo = self._abrir()
        with mock.patch.object(dialogo, "_escribir",
                               side_effect=OSError("disco lleno")), \
                mock.patch.object(chat_participacion._snd,
                                  "reproducir") as sonar, \
                mock.patch.object(chat_participacion.confirmar,
                                  "avisar") as avisar:
            dialogo._guardar()
        sonar.assert_called_once_with("error")
        self.assertIs(avisar.call_args.kwargs["icono"],
                      chat_participacion.confirmar.ICON_ERROR)

    def test_escape_cierra(self):
        dialogo = self._abrir()
        with mock.patch.object(dialogo, "EndModal") as cerrar:
            dialogo._tecla_dialogo(Evento(wx.WXK_ESCAPE))
        cerrar.assert_called_once_with(wx.ID_CANCEL)

    def test_la_foto_no_cambia_mientras_la_ventana_esta_abierta(self):
        self._sumar("Ana", "A")
        dialogo = self._abrir()
        self._sumar("Beto", "B")
        self.assertEqual(list(dialogo.lb_participacion.GetStrings()),
                         ["Ana: 1 mensaje"])

    def test_nombres_y_orden_de_tab(self):
        dialogo = self._abrir()
        controles = [
            control for control in dialogo._panel.GetChildren()
            if isinstance(control, (wx.ListBox, wx.Choice, wx.Button))]
        self.assertEqual([control.GetName() for control in controles],
                         ["Participación", "Ordenar por", "Guardar",
                          "Abrir carpeta de resúmenes", "Cerrar"])

    def test_letras_de_acceso_sin_repetir(self):
        dialogo = self._abrir()
        etiquetas = [
            control.GetLabel() for control in dialogo._panel.GetChildren()
            if isinstance(control, (wx.StaticText, wx.Button))]
        letras = [etiqueta[etiqueta.index("&") + 1].lower()
                  for etiqueta in etiquetas if "&" in etiqueta]
        self.assertEqual(len(letras), len(set(letras)))
        self.assertEqual(letras, ["p", "d", "g", "a", "c"])

    def test_letras_de_acceso_sin_repetir_en_ingles(self):
        from tests.letras_acceso import ingles

        with ingles():
            dialogo = self._abrir()
            etiquetas = [
                control.GetLabel() for control in dialogo._panel.GetChildren()
                if isinstance(control, (wx.StaticText, wx.Button))]
            letras = [etiqueta[etiqueta.index("&") + 1].lower()
                      for etiqueta in etiquetas if "&" in etiqueta]
        self.assertEqual(len(letras), len(set(letras)))
        self.assertEqual(letras, ["p", "t", "s", "o", "c"])


if __name__ == "__main__":
    unittest.main()
