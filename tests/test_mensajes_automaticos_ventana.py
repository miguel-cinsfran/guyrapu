# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Ventana de mensajes automáticos: lista, acciones y cableado.

Abre ventanas.
"""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import wx

from guyrapu.capture import programados
from guyrapu.ui import atajos_captura
from guyrapu.core import paths
from guyrapu.interaction import paquetes
from guyrapu.ui import comando_comandos_chat
from guyrapu.ui import comando_mensajes_automaticos
from guyrapu.ui import comando_estilos
from guyrapu.ui import gui
from guyrapu.ui import mensaje_automatico_cuadro
from guyrapu.ui import mensajes_automaticos_ventana
from guyrapu.ui import menu_interaccion
from tests.letras_acceso import letras_repetidas
from tests.rutas_temporales import redirigir_rutas
from tests.ventanas_prueba import app_de_prueba, destruir


def _mensaje(nombre, texto=None, destino="chat", activo=True, estilo="clasico"):
    return {
        "nombre": nombre, "texto": texto or nombre, "minutos_min": 10,
        "minutos_max": 10, "activo": activo, "proximo": 0.0,
        "destino": destino, "estilo": estilo, "segundos_pantalla": 10,
        "mensajes_entre": 0,
    }


def _letra(rotulo):
    indice = rotulo.find("&")
    if indice < 0 or indice + 1 >= len(rotulo):
        return None
    return rotulo[indice + 1].lower()


class FrameDoble:
    def __init__(self):
        self._config = {"programados_activo": False}
        self.mi_programados_activo = mock.Mock()
        self.programador = mock.Mock()
        self._bind_menu = mock.Mock()

    def _accel(self, _accion):
        return "\tCtrl+Mayús+A"


class BaseVentana(unittest.TestCase):
    def setUp(self):
        self.app = app_de_prueba()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        parche = redirigir_rutas(self.tmp.name)
        parche.__enter__()
        self.addCleanup(parche.__exit__, None, None, None)

    def _padre(self):
        padre = wx.Frame(None)
        padre._config = {"programados_activo": False}
        padre.mi_programados_activo = mock.Mock()
        padre.programador = mock.Mock()
        self.addCleanup(destruir, padre)
        return padre

    def _ventana(self, mensajes=None):
        if mensajes is not None:
            programados.guardar(paths.mensajes_programados(), mensajes)
        ventana = mensajes_automaticos_ventana.VentanaMensajesAutomaticos(
            self._padre())
        self.addCleanup(destruir, ventana)
        return ventana

    def _nombres_en_disco(self):
        return [m["nombre"] for m in programados.cargar(
            paths.mensajes_programados())]

    def _cuadro(self, mensaje=None, otros=()):
        cuadro = mensaje_automatico_cuadro.DialogoMensaje(
            None, mensaje or {}, otros)
        self.addCleanup(destruir, cuadro)
        return cuadro

    def _paquete(self, elementos):
        ruta = Path(self.tmp.name) / "paquete.zip"
        paquetes.exportar(ruta, "avisos", elementos)
        return ruta


class TestContratos(BaseVentana):

    def test_la_lista_tiene_nombre_accesible_y_foco_al_abrir(self):
        ventana = self._ventana([])
        self.assertEqual(ventana.panel.lista.GetName(),
                         "Mensajes automáticos guardados")
        ventana.Show()
        try:
            self.assertIs(wx.Window.FindFocus(), ventana.panel.lista)
        finally:
            ventana.Hide()

    def test_el_panel_funciona_dentro_de_un_frame(self):
        programados.guardar(paths.mensajes_programados(),
                            [_mensaje("A", texto="Hola", destino="chat")])
        marco = wx.Frame(None)
        self.addCleanup(destruir, marco)
        panel = mensajes_automaticos_ventana.PanelMensajesAutomaticos(
            marco, self._padre())
        self.addCleanup(destruir, panel)
        panel.lista.SetSelection(0)
        with mock.patch.object(mensajes_automaticos_ventana, "anunciar") as decir:
            panel._escuchar()
        decir.assert_called_once_with("Hola")

    def test_el_mensaje_nuevo_nace_activo(self):
        cuadro = mensaje_automatico_cuadro.DialogoMensaje(None, {}, [])
        self.addCleanup(destruir, cuadro)
        self.assertTrue(cuadro.chk_activo.GetValue())

    def test_el_cuadro_tiene_todos_los_campos_en_su_rango(self):
        cuadro = mensaje_automatico_cuadro.DialogoMensaje(None, {}, [])
        self.addCleanup(destruir, cuadro)
        self.assertEqual(cuadro.cho_destino.GetStrings(),
                         ["Chat", "Vídeo", "Chat y vídeo"])
        self.assertEqual(cuadro.cho_estilo.GetCount(), 4)
        self.assertEqual((cuadro.sp_segundos.GetMin(), cuadro.sp_segundos.GetMax()),
                         (3, 60))
        self.assertEqual((cuadro.sp_min.GetMin(), cuadro.sp_min.GetMax()),
                         (5, 240))
        self.assertEqual((cuadro.sp_entre.GetMin(), cuadro.sp_entre.GetMax()),
                         (0, 100))

    def test_las_letras_de_acceso_no_se_repiten_en_la_ventana(self):
        self.assertEqual(letras_repetidas(self._ventana([])), {})

    def test_la_ventana_tiene_cerrar_ultimo_y_su_letra_no_se_repite(self):
        ventana = self._ventana([])
        botones = [hijo for hijo in ventana.GetChildren()
                   if isinstance(hijo, wx.Button)]
        self.assertIs(botones[-1], ventana.btn_cerrar)
        self.assertEqual(ventana.btn_cerrar.GetLabel(), "&Cerrar")
        self.assertEqual(letras_repetidas(ventana), {})

    def test_la_ventana_solo_tiene_el_panel_y_cerrar(self):
        ventana = self._ventana([])
        sizer = ventana.GetSizer()
        self.assertEqual([sizer.GetItem(posicion).GetWindow()
                          for posicion in range(sizer.GetItemCount())],
                         [ventana.panel, ventana.btn_cerrar])

    def test_el_cuadro_no_guarda_con_nombre_vacio_o_repetido(self):
        cuadro = self._cuadro()
        cuadro.txt_texto.SetValue("Hola")
        with mock.patch.object(mensaje_automatico_cuadro, "anunciar") as decir, \
                mock.patch.object(cuadro, "EndModal") as cerrar, \
                mock.patch.object(cuadro.txt_nombre, "SetFocus") as foco:
            cuadro._aceptar(None)
        cerrar.assert_not_called()
        decir.assert_called_once_with("El mensaje necesita un nombre.")
        foco.assert_called_once()
        repetido = self._cuadro(otros=[{"nombre": "A"}])
        repetido.txt_nombre.SetValue("A")
        with mock.patch.object(mensaje_automatico_cuadro, "anunciar") as decir, \
                mock.patch.object(repetido, "EndModal") as cerrar:
            repetido._aceptar(None)
        cerrar.assert_not_called()
        decir.assert_called_once_with("Ya hay un mensaje llamado A.")

    def test_el_cuadro_no_guarda_con_texto_o_intervalo_rechazado(self):
        cuadro = self._cuadro()
        cuadro.txt_nombre.SetValue("A")
        with mock.patch.object(mensaje_automatico_cuadro, "anunciar") as decir, \
                mock.patch.object(cuadro, "EndModal") as cerrar, \
                mock.patch.object(cuadro.txt_texto, "SetFocus") as foco:
            cuadro._aceptar(None)
        cerrar.assert_not_called()
        decir.assert_called_once_with("El mensaje no puede estar vacío.")
        foco.assert_called_once()
        cuadro.txt_texto.SetValue("Hola")
        with mock.patch.object(cuadro.sp_min, "GetValue", return_value=10), \
                mock.patch.object(cuadro.sp_max, "GetValue", return_value=4), \
                mock.patch.object(mensaje_automatico_cuadro, "anunciar") as decir, \
                mock.patch.object(cuadro, "EndModal") as cerrar, \
                mock.patch.object(cuadro.sp_max, "SetFocus") as foco:
            cuadro._aceptar(None)
        cerrar.assert_not_called()
        decir.assert_called_once_with(
            "El intervalo máximo no puede ser menor que el mínimo.")
        foco.assert_called_once()

    def test_las_letras_de_acceso_no_se_repiten_en_el_cuadro(self):
        cuadro = mensaje_automatico_cuadro.DialogoMensaje(None, {}, [])
        self.addCleanup(destruir, cuadro)
        self.assertEqual(letras_repetidas(cuadro), {})

    def test_las_letras_de_acceso_no_se_repiten_en_el_menu(self):
        etiquetas = []

        def crear_menu(*_args, **_kwargs):
            menu = mock.MagicMock()
            menu.Append.side_effect = (
                lambda *args: etiquetas.append(args[1]) or mock.Mock())
            menu.AppendCheckItem.side_effect = (
                lambda *args: etiquetas.append(args[1]) or mock.Mock())
            return menu

        frame = mock.Mock()
        frame._accel.return_value = ""
        frame._config = {}
        barra = mock.Mock()
        with mock.patch.object(menu_interaccion.wx, "Menu",
                               side_effect=crear_menu):
            menu_interaccion.construir(frame, barra)
        etiquetas.append(barra.Append.call_args.args[1])
        letras = [letra for letra in map(_letra, etiquetas) if letra]
        self.assertEqual(len(letras), len(set(letras)))


class TestAcciones(BaseVentana):

    def test_p3_tiene_las_acciones_con_sus_teclas(self):
        ventana = self._ventana([])
        claves = [(accion.clave, accion.tecla) for accion in ventana.panel._acciones]
        self.assertEqual(claves, [
            ("agregar", None), ("editar", "intro"), ("renombrar", "f2"),
            ("duplicar", "ctrl+d"), ("subir", None), ("bajar", None),
            ("pausar", None), ("escuchar", None), ("eliminar", "suprimir"),
            ("exportar", None), ("importar", None)])
        sin_elemento = {accion.clave for accion in ventana.panel._acciones
                        if not accion.necesita_elemento}
        self.assertEqual(sin_elemento, {"agregar", "exportar", "importar"})

    def test_duplicar_deja_la_copia_debajo_del_original(self):
        ventana = self._ventana([_mensaje("A"), _mensaje("B")])
        ventana.panel.lista.SetSelection(0)
        with mock.patch.object(mensajes_automaticos_ventana, "anunciar") as decir:
            ventana.panel._duplicar()
        self.assertEqual(self._nombres_en_disco(), ["A", "A (copia)", "B"])
        self.assertEqual(ventana.panel.lista.GetSelection(), 1)
        decir.assert_called_once_with("Mensaje duplicado")

    def test_subir_y_bajar_mueven_y_guardan_el_orden(self):
        ventana = self._ventana([_mensaje("A"), _mensaje("B"), _mensaje("C")])
        ventana.panel.lista.SetSelection(2)
        with mock.patch.object(mensajes_automaticos_ventana, "anunciar"):
            ventana.panel._mover(-1)
        self.assertEqual(self._nombres_en_disco(), ["A", "C", "B"])
        ventana.panel.lista.SetSelection(0)
        with mock.patch.object(mensajes_automaticos_ventana, "anunciar") as decir:
            ventana.panel._mover(-1)
        decir.assert_called_once_with("Posición 1 de 3")
        self.assertEqual(self._nombres_en_disco(), ["A", "C", "B"])

    def test_escuchar_dice_el_estilo_si_sale_en_el_video(self):
        ventana = self._ventana([
            _mensaje("A", texto="Hola", destino="video", estilo="clasico")])
        ventana.panel.lista.SetSelection(0)
        with mock.patch.object(mensajes_automaticos_ventana, "anunciar") as decir:
            ventana.panel._escuchar()
        decir.assert_called_once_with("Hola. Estilo: Clásico.")

    def test_escuchar_solo_el_texto_si_no_sale_en_el_video(self):
        ventana = self._ventana([_mensaje("A", texto="Hola", destino="chat")])
        ventana.panel.lista.SetSelection(0)
        with mock.patch.object(mensajes_automaticos_ventana, "anunciar") as decir:
            ventana.panel._escuchar()
        decir.assert_called_once_with("Hola")

    def test_los_botones_nunca_se_deshabilitan(self):
        ventana = self._ventana([])
        botones = [hijo for hijo in ventana.panel.GetChildren()
                   if isinstance(hijo, wx.Button)]
        self.assertTrue(botones)
        self.assertTrue(all(boton.IsEnabled() for boton in botones))

    def test_sin_seleccion_las_acciones_dicen_por_que(self):
        ventana = self._ventana([])
        with mock.patch("guyrapu.ui.lista_acciones.anunciar") as decir:
            ventana.panel._lista.ejecutar("editar")
        decir.assert_called_once_with(
            "No hay mensajes automáticos. Usa Agregar para crear uno.")

    def test_el_boton_cerrar_cierra_la_ventana(self):
        ventana = self._ventana([])
        evento = wx.CommandEvent(wx.EVT_BUTTON.typeId,
                                 ventana.btn_cerrar.GetId())
        with mock.patch.object(ventana, "EndModal") as cerrar:
            ventana.btn_cerrar.GetEventHandler().ProcessEvent(evento)
        cerrar.assert_called_once_with(wx.ID_CANCEL)

    def test_escape_cierra_la_ventana_y_el_cuadro(self):
        evento = mock.Mock()
        evento.GetKeyCode.return_value = wx.WXK_ESCAPE
        ventana = self._ventana([])
        with mock.patch.object(ventana, "EndModal") as cerrar:
            ventana._al_tecla(evento)
        cerrar.assert_called_once_with(wx.ID_CANCEL)
        cuadro = self._cuadro()
        with mock.patch.object(cuadro, "EndModal") as cerrar:
            cuadro._al_tecla(evento)
        cerrar.assert_called_once_with(wx.ID_CANCEL)

    def test_eliminar_pide_confirmacion_con_no_predeterminado(self):
        ventana = self._ventana([_mensaje("A"), _mensaje("B")])
        ventana.panel.lista.SetSelection(0)
        with mock.patch.object(
                mensajes_automaticos_ventana.confirmar, "preguntar",
                return_value=True) as preguntar, \
                mock.patch.object(mensajes_automaticos_ventana,
                                  "anunciar") as decir:
            ventana.panel._eliminar()
        pregunta = preguntar.call_args
        self.assertFalse(pregunta.kwargs["predeterminado_si"])
        self.assertEqual(self._nombres_en_disco(), ["B"])
        decir.assert_called_once_with("Mensaje eliminado")


class TestImportarExportar(BaseVentana):

    def _importar(self, ruta, reemplazar):
        ventana = self._ventana([_mensaje("A"), _mensaje("B")])
        with mock.patch.object(ventana.panel, "_pedir_ruta", return_value=ruta), \
                mock.patch.object(ventana.panel, "_preguntar_reemplazo",
                                  return_value=reemplazar), \
                mock.patch.object(mensajes_automaticos_ventana,
                                  "anunciar") as decir:
            ventana.panel._importar()
        return ventana, decir

    def test_importar_con_reemplazo_reemplaza_en_el_lugar(self):
        ruta = self._paquete([_mensaje("A", texto="nuevoA"),
                              _mensaje("Nuevo")])
        ventana, _ = self._importar(ruta, True)
        self.assertEqual([m["nombre"] for m in ventana.panel._mensajes],
                         ["A", "B", "Nuevo"])
        self.assertEqual(ventana.panel._mensajes[0]["texto"], "nuevoA")
        self.assertFalse(ventana.panel._mensajes[0]["activo"])

    def test_importar_sin_reemplazo_agrega_con_nombre_de_copia(self):
        ruta = self._paquete([_mensaje("A"), _mensaje("Nuevo")])
        ventana, decir = self._importar(ruta, False)
        self.assertEqual([m["nombre"] for m in ventana.panel._mensajes],
                         ["A", "B", "A (copia)", "Nuevo"])
        decir.assert_called_once_with("Se importaron 2 mensajes.")

    def test_lo_importado_queda_pausado_y_sin_proximo(self):
        ruta = self._paquete([_mensaje("A"), _mensaje("Nuevo")])
        ventana, _ = self._importar(ruta, False)
        importados = [m for m in ventana.panel._mensajes
                      if m["nombre"] in ("A (copia)", "Nuevo")]
        self.assertEqual([m["activo"] for m in importados], [False, False])
        self.assertEqual([m["proximo"] for m in importados], [0.0, 0.0])

    def test_un_paquete_rechazado_se_informa_con_su_motivo(self):
        ruta = Path(self.tmp.name) / "estilos.zip"
        paquetes.exportar(ruta, "estilos", [{"nombre": "Oscuro"}])
        with self.assertRaises(paquetes.PaqueteRechazado) as error:
            paquetes.leer(ruta, "avisos")
        ventana = self._ventana([])
        with mock.patch.object(ventana.panel, "_pedir_ruta", return_value=ruta), \
                mock.patch.object(mensajes_automaticos_ventana.confirmar,
                                  "avisar") as avisar:
            ventana.panel._importar()
        avisar.assert_called_once_with(
            ventana.panel, str(error.exception), "Importar mensajes automáticos",
            "Aceptar", icono=mensajes_automaticos_ventana.confirmar.ICON_ERROR)

    def test_exportar_con_la_lista_vacia_no_abre_nada(self):
        ventana = self._ventana([])
        with mock.patch.object(ventana.panel, "_pedir_ruta") as pedir, \
                mock.patch.object(mensajes_automaticos_ventana, "anunciar") as decir:
            ventana.panel._exportar()
        pedir.assert_not_called()
        decir.assert_called_once_with(
            "No hay mensajes automáticos para exportar.")

    def test_exportar_escribe_todos_los_mensajes(self):
        ventana = self._ventana([_mensaje("A"), _mensaje("B")])
        ruta = Path(self.tmp.name) / "salida.zip"
        with mock.patch.object(ventana.panel, "_pedir_ruta", return_value=ruta):
            ventana.panel._exportar()
        self.assertEqual([m["nombre"] for m in
                          paquetes.leer(ruta, "avisos").elementos],
                         ["A", "B"])

    def test_un_error_al_exportar_sale_en_un_cuadro(self):
        ventana = self._ventana([_mensaje("A")])
        with mock.patch.object(ventana.panel, "_pedir_ruta",
                               return_value="salida.zip"), \
                mock.patch.object(mensajes_automaticos_ventana.paquetes,
                                  "exportar", side_effect=OSError("disco lleno")), \
                mock.patch.object(mensajes_automaticos_ventana.confirmar,
                                  "avisar") as avisar:
            ventana.panel._exportar()
        avisar.assert_called_once()
        self.assertIn("disco lleno", avisar.call_args.args[1])


class TestCableado(BaseVentana):

    def test_el_atajo_de_fabrica_es_ctrl_mayus_a(self):
        from guyrapu.core.config import parsear_atajos
        self.assertEqual(parsear_atajos({})["mensajes_automaticos"].texto,
                         "ctrl+shift+a")
        self.assertEqual(
            atajos_captura.ETIQUETAS["mensajes_automaticos"],
            "Abrir los mensajes automáticos")

    def test_el_menu_enlaza_abrir_y_alternar(self):
        frame = FrameDoble()
        barra = mock.Mock()
        with mock.patch.object(menu_interaccion.wx, "Menu", return_value=mock.Mock()):
            menu_interaccion.construir(frame, barra)
        llamadas = [(llamada.args[1], llamada.args[2])
                    for llamada in frame._bind_menu.call_args_list]
        self.assertEqual(llamadas, [
            (comando_mensajes_automaticos.abrir, frame),
            (comando_comandos_chat.abrir, frame),
            (comando_mensajes_automaticos.alternar, frame),
            (comando_estilos.abrir, frame)])

    def test_alternar_guarda_marca_la_casilla_y_anuncia(self):
        frame = FrameDoble()
        with mock.patch.object(gui, "guardar_opcion") as guardar, \
                mock.patch.object(gui, "anunciar") as decir:
            comando_mensajes_automaticos.alternar(frame)
            self.assertTrue(frame._config["programados_activo"])
            guardar.assert_called_once_with(
                gui.RUTA_CONFIG, "programados", "activo", "true")
            frame.mi_programados_activo.Check.assert_called_once_with(True)
            decir.assert_called_once_with("Mensajes automáticos activados")
            comando_mensajes_automaticos.alternar(frame)
        self.assertFalse(frame._config["programados_activo"])
        decir.assert_called_with("Mensajes automáticos desactivados")

    def test_la_casilla_de_la_ventana_relee_el_valor(self):
        frame = FrameDoble()
        ventana = self._ventana([])
        ventana.panel._padre = frame
        with mock.patch.object(gui, "guardar_opcion"), \
                mock.patch.object(gui, "anunciar"):
            ventana.panel._al_alternar(None)
        self.assertTrue(ventana.panel.chk_programados.GetValue())
        with mock.patch.object(gui, "guardar_opcion"), \
                mock.patch.object(gui, "anunciar"):
            ventana.panel._al_alternar(None)
        self.assertFalse(ventana.panel.chk_programados.GetValue())

    def test_al_cerrar_la_ventana_se_recarga_el_programador(self):
        frame = FrameDoble()
        with mock.patch.object(mensajes_automaticos_ventana, "abrir",
                               side_effect=lambda _padre, al_cerrar=None:
                               al_cerrar()) as abrir, \
                mock.patch.object(comando_mensajes_automaticos.programados,
                                  "cargar", return_value=["nueva"]) as cargar, \
                mock.patch.object(comando_mensajes_automaticos.paths,
                                  "mensajes_programados", return_value="ruta"):
            comando_mensajes_automaticos.abrir(frame)
        abrir.assert_called_once()
        cargar.assert_called_once_with("ruta")
        frame.programador.recargar.assert_called_once_with(["nueva"])


if __name__ == "__main__":
    unittest.main()
