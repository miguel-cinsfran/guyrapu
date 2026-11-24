# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Página de encuestas y su cuadro: lista, acciones, foco y guardado.

Abre ventanas.
"""

import tempfile
import unittest
from unittest import mock

import wx

from guyrapu.core import paths
from guyrapu.interaction import encuestas_guardadas, estilo_elegido
from guyrapu.interaction.encuestas import validar_encuesta
from guyrapu.ui import encuesta_cuadro, encuestas_ventana
from tests.letras_acceso import letras_repetidas
from tests.rutas_temporales import redirigir_rutas
from tests.ventanas_prueba import app_de_prueba, destruir


def _datos(pregunta="¿Qué pizza?", **cambios):
    datos = {
        "pregunta": pregunta,
        "nombre": pregunta,
        "opciones": ["muzzarella", "napolitana"],
        "segundos": 120,
        "destino": "video",
        "estilo": "clasico",
        "avisar": True,
    }
    datos.update(cambios)
    return datos


class BaseVentana(unittest.TestCase):
    def setUp(self):
        self.app = app_de_prueba()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        parche = redirigir_rutas(self.tmp.name)
        parche.__enter__()
        self.addCleanup(parche.__exit__, None, None, None)

    def _panel(self, lista=None):
        if lista is not None:
            encuestas_guardadas.guardar(paths.encuestas(), lista)
        marco = wx.Frame(None)
        self.addCleanup(destruir, marco)
        panel = encuestas_ventana.PanelEncuestas(marco)
        self.addCleanup(destruir, panel)
        return panel

    def _cuadro(self, datos=None):
        cuadro = encuesta_cuadro.DialogoEncuesta(None, datos or {})
        self.addCleanup(destruir, cuadro)
        return cuadro

    def _preguntas_en_disco(self):
        return [encuesta["pregunta"]
                for encuesta in encuestas_guardadas.cargar(paths.encuestas())]

    def _mostrada(self, ventana):
        ventana.Show()
        self.addCleanup(ventana.Hide)


class TestPagina(BaseVentana):

    def test_la_lista_tiene_su_nombre_y_la_linea_vacia(self):
        panel = self._panel([])
        self.assertEqual(panel.lista.GetName(), "Encuestas guardadas")
        self.assertEqual(panel.lista.GetCount(), 1)
        self.assertEqual(
            panel.lista.GetString(0),
            "No hay encuestas. Aquí aparecen las encuestas listas para "
            "iniciar en el directo. El público vota con un número precedido "
            "de un signo de exclamación, como 1 o 2. "
            "Usa Agregar para crear una.")

    def test_un_archivo_danado_deja_la_lista_vacia(self):
        paths.encuestas().write_text("{roto", encoding="utf-8")
        panel = self._panel()
        self.assertEqual(
            panel.lista.GetString(0),
            "No hay encuestas. Aquí aparecen las encuestas listas para "
            "iniciar en el directo. El público vota con un número precedido "
            "de un signo de exclamación, como 1 o 2. "
            "Usa Agregar para crear una.")

    def test_la_fila_dice_pregunta_opciones_y_duracion(self):
        panel = self._panel([_datos("¿Qué pizza?")])
        self.assertEqual(panel.lista.GetString(0),
                         "¿Qué pizza?, 2 opciones, 2 minutos")

    def test_las_acciones_son_las_de_comandos_sin_renombrar_ni_pausar(self):
        panel = self._panel([])
        self.assertEqual([(accion.clave, accion.tecla)
                          for accion in panel._acciones], [
            ("agregar", None), ("editar", "intro"), ("iniciar", None),
            ("duplicar", "ctrl+d"), ("escuchar", None),
            ("eliminar", "suprimir"), ("exportar", None), ("importar", None)])
        sin_elemento = {accion.clave for accion in panel._acciones
                        if not accion.necesita_elemento}
        self.assertEqual(sin_elemento, {"agregar", "exportar", "importar"})

    def test_iniciar_sin_encuesta_elegida_dice_por_que(self):
        from guyrapu.ui import lista_acciones

        panel = self._panel([])
        with mock.patch.object(lista_acciones, "anunciar") as decir:
            panel._lista.ejecutar("iniciar")
        decir.assert_called_once_with(
            "No hay encuestas. Aquí aparecen las encuestas listas para "
            "iniciar en el directo. El público vota con un número precedido "
            "de un signo de exclamación, como 1 o 2. "
            "Usa Agregar para crear una.")

    def test_iniciar_abre_la_encuesta_elegida(self):
        panel = self._panel([_datos("A"), _datos("B")])
        panel.lista.SetSelection(1)
        with mock.patch.object(
                encuestas_ventana.encuesta_en_vivo, "abierta",
                return_value=False), \
                mock.patch.object(
                    encuestas_ventana.encuesta_en_vivo, "iniciar") as iniciar:
            panel._iniciar()
        iniciar.assert_called_once_with(panel.GetTopLevelParent(),
                                        panel._encuestas[1])

    def test_iniciar_con_otra_abierta_pregunta_con_no_y_no_cambia_nada(self):
        panel = self._panel([_datos("A"), _datos("B")])
        panel.lista.SetSelection(1)
        with mock.patch.object(
                encuestas_ventana.encuesta_en_vivo, "abierta",
                return_value=True), \
                mock.patch.object(
                    encuestas_ventana.confirmar, "preguntar",
                    return_value=False) as preguntar, \
                mock.patch.object(
                    encuestas_ventana.encuesta_en_vivo, "cerrar") as cerrar, \
                mock.patch.object(
                    encuestas_ventana.encuesta_en_vivo, "iniciar") as iniciar:
            panel._iniciar()
        self.assertFalse(preguntar.call_args.kwargs["predeterminado_si"])
        cerrar.assert_not_called()
        iniciar.assert_not_called()

    def test_iniciar_con_otra_abierta_la_cierra_y_abre_la_nueva(self):
        panel = self._panel([_datos("A"), _datos("B")])
        panel.lista.SetSelection(1)
        with mock.patch.object(
                encuestas_ventana.encuesta_en_vivo, "abierta",
                return_value=True), \
                mock.patch.object(
                    encuestas_ventana.confirmar, "preguntar",
                    return_value=True), \
                mock.patch.object(
                    encuestas_ventana.encuesta_en_vivo, "cerrar") as cerrar, \
                mock.patch.object(
                    encuestas_ventana.encuesta_en_vivo, "iniciar") as iniciar:
            panel._iniciar()
        cerrar.assert_called_once_with(panel.GetTopLevelParent())
        iniciar.assert_called_once_with(panel.GetTopLevelParent(),
                                        panel._encuestas[1])

    def test_agregar_guarda_y_deja_el_foco_en_la_nueva(self):
        panel = self._panel([])
        self._mostrada(panel.GetParent())
        with mock.patch.object(encuestas_ventana.encuesta_cuadro, "abrir",
                               return_value=_datos("¿Nueva?")), \
                mock.patch.object(encuestas_ventana, "anunciar") as decir:
            panel._agregar()
        self.assertEqual(self._preguntas_en_disco(), ["¿Nueva?"])
        self.assertEqual(panel.lista.GetSelection(), 0)
        self.assertIs(wx.Window.FindFocus(), panel.lista)
        decir.assert_called_once_with("Encuesta agregada")

    def test_editar_guarda_y_deja_el_foco_en_esa(self):
        panel = self._panel([_datos("A"), _datos("B")])
        self._mostrada(panel.GetParent())
        panel.lista.SetSelection(1)
        with mock.patch.object(encuestas_ventana.encuesta_cuadro, "abrir",
                               return_value=_datos("¿Otra?")), \
                mock.patch.object(encuestas_ventana, "anunciar") as decir:
            panel._editar()
        self.assertEqual(self._preguntas_en_disco(), ["A", "¿Otra?"])
        self.assertEqual(panel.lista.GetSelection(), 1)
        self.assertIs(wx.Window.FindFocus(), panel.lista)
        decir.assert_called_once_with("Encuesta guardada")

    def test_duplicar_deja_la_copia_debajo(self):
        panel = self._panel([_datos("A"), _datos("B")])
        panel.lista.SetSelection(0)
        with mock.patch.object(encuestas_ventana, "anunciar") as decir:
            panel._duplicar()
        self.assertEqual(self._preguntas_en_disco(),
                         ["A", "A (copia)", "B"])
        self.assertEqual(panel.lista.GetSelection(), 1)
        decir.assert_called_once_with("Encuesta duplicada")

    def test_escuchar_dice_la_pregunta_y_las_opciones(self):
        panel = self._panel([_datos("¿Qué pizza?")])
        panel.lista.SetSelection(0)
        with mock.patch.object(encuestas_ventana, "anunciar") as decir:
            panel._escuchar()
        self.assertEqual(
            decir.call_args.args[0],
            "Encuesta: ¿Qué pizza?. Opciones: muzzarella, napolitana.")

    def test_eliminar_pide_confirmacion_con_no_y_deja_el_siguiente(self):
        panel = self._panel([_datos("A"), _datos("B"), _datos("C")])
        self._mostrada(panel.GetParent())
        panel.lista.SetSelection(1)
        with mock.patch.object(encuestas_ventana.confirmar, "preguntar",
                               return_value=True) as preguntar, \
                mock.patch.object(encuestas_ventana, "anunciar") as decir:
            panel._eliminar()
        self.assertFalse(preguntar.call_args.kwargs["predeterminado_si"])
        self.assertEqual(self._preguntas_en_disco(), ["A", "C"])
        self.assertEqual(panel.lista.GetSelection(), 1)
        self.assertIs(wx.Window.FindFocus(), panel.lista)
        decir.assert_called_once_with("Encuesta eliminada")

    def test_exportar_con_la_lista_vacia_no_abre_nada(self):
        panel = self._panel([])
        with mock.patch.object(panel, "_pedir_ruta") as pedir, \
                mock.patch.object(encuestas_ventana, "anunciar") as decir:
            panel._exportar()
        pedir.assert_not_called()
        decir.assert_called_once_with("No hay encuestas para exportar.")


class TestCuadro(BaseVentana):

    def test_tiene_todos_los_campos(self):
        cuadro = self._cuadro()
        self.assertEqual(cuadro.cho_duracion.GetStrings(), [
            "30 segundos", "1 minuto", "2 minutos", "3 minutos",
            "5 minutos", "10 minutos", "15 minutos", "30 minutos"])
        self.assertEqual(cuadro.cho_duracion.GetSelection(), 2)
        self.assertEqual(cuadro.cho_destino.GetStrings(), [
            "Vídeo", "Chat de YouTube", "Vídeo y chat de YouTube"])
        self.assertEqual(cuadro.cho_destino.GetSelection(), 0)
        self.assertEqual(cuadro.cho_estilo.GetCount(), 5)
        self.assertTrue(cuadro.txt_respuestas.GetWindowStyle()
                        & wx.TE_MULTILINE)

    def test_p6_la_casilla_de_avisos_nace_marcada(self):
        cuadro = self._cuadro()
        self.assertEqual(
            cuadro.chk_avisar.GetLabel(),
            "Avisar cuando quedan 10 segundos y cuando cambia &quién gana")
        self.assertTrue(cuadro.chk_avisar.GetValue())

    def test_p6_la_casilla_de_avisos_llega_a_datos(self):
        cuadro = self._cuadro()
        cuadro.chk_avisar.SetValue(False)
        self.assertFalse(cuadro.datos()["avisar"])

    def test_las_letras_de_acceso_no_se_repiten_en_el_cuadro(self):
        self.assertEqual(letras_repetidas(self._cuadro()), {})

    def test_el_foco_nace_en_pregunta(self):
        cuadro = self._cuadro()
        self._mostrada(cuadro)
        self.assertIs(wx.Window.FindFocus(), cuadro.txt_pregunta)

    def test_carga_los_datos_de_la_encuesta(self):
        cuadro = self._cuadro(_datos(
            "¿Qué?", opciones=["uno", "dos"], segundos=300,
            destino="chat", estilo="banda"))
        self.assertEqual(cuadro.txt_pregunta.GetValue(), "¿Qué?")
        self.assertEqual(cuadro.txt_respuestas.GetValue(), "uno\ndos")
        self.assertEqual(cuadro.cho_duracion.GetSelection(), 4)
        self.assertEqual(cuadro.cho_destino.GetSelection(), 1)
        self.assertEqual(
            estilo_elegido.clave_de(
                cuadro.cho_estilo.GetSelection(), cuadro._estilos),
            "banda")

    def test_guarda_cada_campo_y_descarta_las_lineas_vacias(self):
        cuadro = self._cuadro()
        cuadro.txt_pregunta.SetValue("¿Qué?")
        cuadro.txt_respuestas.SetValue("uno\n\ndos\n")
        cuadro.cho_duracion.SetSelection(4)
        cuadro.cho_destino.SetSelection(2)
        cuadro._elegir_estilo("banda")
        self.assertEqual(cuadro.datos(), {
            "pregunta": "¿Qué?", "opciones": ["uno", "dos"],
            "segundos": 300, "destino": "ambos", "estilo": "banda",
            "avisar": True})

    def _aceptar_con_error(self, cuadro):
        with mock.patch.object(encuesta_cuadro, "anunciar") as decir, \
                mock.patch.object(cuadro, "EndModal") as cerrar:
            cuadro._aceptar(None)
        cerrar.assert_not_called()
        return decir

    def test_una_sola_opcion_no_cierra_y_deja_el_foco_en_respuestas(self):
        cuadro = self._cuadro()
        self._mostrada(cuadro)
        cuadro.txt_pregunta.SetValue("¿Qué?")
        cuadro.txt_respuestas.SetValue("uno")
        decir = self._aceptar_con_error(cuadro)
        decir.assert_called_once_with(validar_encuesta("¿Qué?", ["uno"]))
        self.assertIs(wx.Window.FindFocus(), cuadro.txt_respuestas)

    def test_una_pregunta_vacia_manda_el_foco_a_pregunta(self):
        cuadro = self._cuadro()
        self._mostrada(cuadro)
        cuadro.txt_pregunta.SetValue("  ")
        cuadro.txt_respuestas.SetValue("uno\ndos")
        decir = self._aceptar_con_error(cuadro)
        decir.assert_called_once_with(
            validar_encuesta("  ", ["uno", "dos"]))
        self.assertIs(wx.Window.FindFocus(), cuadro.txt_pregunta)

    def test_escape_cierra_el_cuadro(self):
        evento = mock.Mock()
        evento.GetKeyCode.return_value = wx.WXK_ESCAPE
        cuadro = self._cuadro()
        with mock.patch.object(cuadro, "EndModal") as cerrar:
            cuadro._al_tecla(evento)
        cerrar.assert_called_once_with(wx.ID_CANCEL)


if __name__ == "__main__":
    unittest.main()
