# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Ventana Estilos del vídeo: lista, acciones, cuadro y paquetes.

Abre ventanas.
"""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import wx

from guyrapu.capture import programados
from guyrapu.core import paths
from guyrapu.interaction import animacion, paquetes
from guyrapu.obs import descripcion_estilo, estilos_aviso
from guyrapu.ui import estilo_cuadro, estilos_ventana
from guyrapu.ui.lista_acciones import clave_de_tecla
from tests.letras_acceso import letras_repetidas
from tests.rutas_temporales import redirigir_rutas
from tests.ventanas_prueba import app_de_prueba, destruir

MOTIVO_FABRICA = ("Los estilos de fábrica no se cambian. Usa Duplicar para "
                  "crear uno propio.")


def _estilo(nombre="Mío", clave="mio", **cambios):
    return dict(estilos_aviso.FABRICA[0], clave=clave, nombre=nombre, **cambios)


def _mensaje(nombre, estilo):
    return {"nombre": nombre, "texto": nombre, "estilo": estilo}


class BaseVentana(unittest.TestCase):
    def setUp(self):
        self.app = app_de_prueba()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        parche = redirigir_rutas(self.tmp.name)
        parche.__enter__()
        self.addCleanup(parche.__exit__, None, None, None)

    def _panel(self, estilos=None):
        if estilos is not None:
            estilos_aviso.guardar_estilos(paths.estilos_avisos(), estilos)
        marco = wx.Frame(None)
        self.addCleanup(destruir, marco)
        panel = estilos_ventana.PanelEstilos(marco)
        self.addCleanup(destruir, panel)
        return panel

    def _cuadro(self, estilo=None, otros=()):
        cuadro = estilo_cuadro.DialogoEstilo(None, estilo, otros)
        self.addCleanup(destruir, cuadro)
        return cuadro

    def _nombres_en_disco(self):
        return [estilo["nombre"] for estilo in estilos_aviso.cargar_estilos(
            paths.estilos_avisos())]

    def _textos(self, panel):
        return [panel.lista.GetString(indice)
                for indice in range(panel.lista.GetCount())]

    def _paquete(self, elementos, tipo="estilos"):
        ruta = Path(self.tmp.name) / "paquete.zip"
        paquetes.exportar(ruta, tipo, elementos)
        return ruta


class TestVentana(BaseVentana):

    def test_p1_lista_la_fabrica_primero_y_despues_el_usuario(self):
        panel = self._panel([_estilo("Mío")])
        self.assertEqual(self._textos(panel), [
            "Clásico (de fábrica), predeterminado de mensajes automáticos, "
            "comandos, disparadores, encuestas y metas",
            "Banda (de fábrica)", "Tarjeta (de fábrica)",
            "Alto contraste (de fábrica)", "Mío"])

    def test_p2_la_fila_dice_los_tipos_que_lo_usan(self):
        estilos_aviso.guardar_por_tipo(
            paths.estilos_avisos(), {"comando": "banda", "encuesta": "banda"})
        panel = self._panel([])
        self.assertEqual(
            self._textos(panel)[1],
            "Banda (de fábrica), predeterminado de comandos y encuestas")

    def test_p2_sin_tipos_la_fila_queda_como_hoy(self):
        panel = self._panel([_estilo("Mío")])
        self.assertEqual(self._textos(panel)[4], "Mío")

    def test_el_panel_funciona_dentro_de_un_frame(self):
        frame = wx.Frame(None)
        self.addCleanup(destruir, frame)
        panel = estilos_ventana.PanelEstilos(frame)
        self.addCleanup(destruir, panel)
        self.assertEqual(panel.lista.GetCount(), 4)
        panel.lista.SetSelection(0)
        with mock.patch.object(estilos_ventana, "anunciar") as decir:
            panel._escuchar()
        decir.assert_called_once_with(descripcion_estilo.describir(
            estilos_aviso.FABRICA[0]))


class TestAcciones(BaseVentana):

    def test_p2_las_acciones_con_sus_teclas(self):
        panel = self._panel([])
        claves = [(accion.clave, accion.tecla) for accion in panel._acciones]
        self.assertEqual(claves, [
            ("agregar", None), ("editar", "intro"), ("renombrar", "f2"),
            ("duplicar", "ctrl+d"), ("escuchar", None), ("probar", None),
            ("predeterminado", None), ("eliminar", "suprimir"),
            ("exportar", None), ("importar", None)])
        sin_elemento = {accion.clave for accion in panel._acciones
                        if not accion.necesita_elemento}
        self.assertEqual(sin_elemento, {"agregar", "exportar", "importar"})

    def test_p2_cada_tecla_llega_a_su_accion(self):
        panel = self._panel([])
        for (codigo, modificadores), esperado in (
                ((wx.WXK_RETURN, wx.MOD_NONE), "editar"),
                ((wx.WXK_F2, wx.MOD_NONE), "renombrar"),
                ((ord("D"), wx.MOD_CONTROL), "duplicar"),
                ((wx.WXK_DELETE, wx.MOD_NONE), "eliminar")):
            with self.subTest(tecla=esperado):
                self.assertEqual(clave_de_tecla(
                    codigo, modificadores, panel._acciones), esperado)

    def test_p2_los_botones_y_el_menu_tienen_las_acciones(self):
        panel = self._panel([])
        etiquetas = [hijo.GetLabel() for hijo in panel.GetChildren()
                     if isinstance(hijo, wx.Button)]
        self.assertEqual(etiquetas, [
            "A&gregar", "&Editar", "Cambiar n&ombre", "&Duplicar",
            "Escuc&har", "Pro&bar", "Establecer como &predeterminado…",
            "E&liminar", "Expo&rtar", "&Importar"])
        menu = panel._lista._construir_menu()
        try:
            self.assertEqual(
                [item.GetItemLabel() for item in menu.GetMenuItems()],
                ["A&gregar", "&Editar\tEnter", "Cambiar n&ombre\tF2",
                 "&Duplicar\tCtrl+D", "Escuc&har", "Pro&bar",
                 "Establecer como &predeterminado…",
                 "E&liminar\tDel", "Expo&rtar", "&Importar"])
        finally:
            menu.Destroy()

    def test_los_botones_nunca_se_deshabilitan(self):
        botones = [hijo for hijo in self._panel([]).GetChildren()
                   if isinstance(hijo, wx.Button)]
        self.assertTrue(botones)
        self.assertTrue(all(boton.IsEnabled() for boton in botones))

    def test_p3_la_fabrica_no_se_edita_ni_cambia_ni_elimina(self):
        for metodo in ("_editar", "_renombrar", "_eliminar"):
            with self.subTest(accion=metodo):
                panel = self._panel([])
                panel.lista.SetSelection(0)
                with mock.patch.object(estilos_ventana, "anunciar") as decir:
                    getattr(panel, metodo)()
                decir.assert_called_once_with(MOTIVO_FABRICA)
                self.assertEqual(self._nombres_en_disco(), [])

    def test_p3_duplicar_la_fabrica_crea_un_estilo_del_usuario(self):
        panel = self._panel([])
        panel.lista.SetSelection(0)
        with mock.patch.object(estilos_ventana, "anunciar") as decir:
            panel._duplicar()
        estilos = estilos_aviso.cargar_estilos(paths.estilos_avisos())
        self.assertEqual([estilo["nombre"] for estilo in estilos],
                         ["Clásico (copia)"])
        self.assertNotEqual(estilos[0]["clave"], "clasico")
        self.assertEqual(panel.lista.GetSelection(), 4)
        decir.assert_called_once_with("Estilo duplicado")

    def test_duplicar_un_estilo_del_usuario_lo_deja_debajo(self):
        panel = self._panel([_estilo("A", clave="a"),
                             _estilo("B", clave="b")])
        panel.lista.SetSelection(4)
        with mock.patch.object(estilos_ventana, "anunciar"):
            panel._duplicar()
        self.assertEqual(self._nombres_en_disco(), ["A", "A (copia)", "B"])
        self.assertEqual(panel.lista.GetSelection(), 5)

    def test_p6_escuchar_anuncia_la_descripcion(self):
        panel = self._panel([])
        panel.lista.SetSelection(0)
        with mock.patch.object(estilos_ventana, "anunciar") as decir:
            panel._escuchar()
        decir.assert_called_once_with(descripcion_estilo.describir(
            estilos_aviso.FABRICA[0]))

    def test_p1_probar_arma_el_texto_de_ejemplo_con_el_estilo_elegido(self):
        panel = self._panel([_estilo("Mío", clave="mio")])
        panel.lista.SetSelection(4)
        with mock.patch.object(estilos_ventana.probar_aviso,
                               "probar") as probar:
            panel._probar()
        probar.assert_called_once_with(
            "Así se ve un mensaje con este estilo.",
            estilos_aviso.todos(panel._usuario)[4])

    def test_p1_probar_es_un_boton_con_su_nombre_accesible(self):
        panel = self._panel([])
        accion = next(accion for accion in panel._acciones
                      if accion.clave == "probar")
        self.assertEqual(accion.etiqueta, "Pro&bar")
        boton = next(hijo for hijo in panel.GetChildren()
                     if isinstance(hijo, wx.Button)
                     and hijo.GetLabel() == "Pro&bar")
        self.assertEqual(boton.GetName(), "Probar")

    def test_p1_predeterminado_marca_los_tipos_elegidos(self):
        panel = self._panel([_estilo("Mío", clave="mio")])
        panel.lista.SetSelection(4)
        with mock.patch.object(
                estilos_ventana.estilo_tipos_cuadro, "abrir",
                return_value={"comando", "encuesta"}) as abrir, \
                mock.patch.object(estilos_ventana, "anunciar") as decir:
            panel._predeterminado()
        abrir.assert_called_once_with(panel, set())
        self.assertEqual(
            estilos_aviso.cargar_por_tipo(paths.estilos_avisos()),
            {"mensaje": "clasico", "comando": "mio",
             "disparador": "clasico", "encuesta": "mio", "meta": "clasico"})
        self.assertEqual(self._textos(panel)[4],
                         "Mío, predeterminado de comandos y encuestas")
        decir.assert_called_once_with("Predeterminados guardados")

    def test_p1_un_tipo_desmarcado_vuelve_a_clasico(self):
        estilos_aviso.guardar_por_tipo(
            paths.estilos_avisos(), {"comando": "mio", "disparador": "mio"})
        panel = self._panel([_estilo("Mío", clave="mio")])
        panel.lista.SetSelection(4)
        with mock.patch.object(
                estilos_ventana.estilo_tipos_cuadro, "abrir",
                return_value={"comando"}), \
                mock.patch.object(estilos_ventana, "anunciar"):
            panel._predeterminado()
        self.assertEqual(
            estilos_aviso.cargar_por_tipo(paths.estilos_avisos()),
            {"mensaje": "clasico", "comando": "mio",
             "disparador": "clasico", "encuesta": "clasico",
             "meta": "clasico"})

    def test_p1_el_cuadro_abre_marcado_lo_que_ya_usa_el_estilo(self):
        estilos_aviso.guardar_por_tipo(
            paths.estilos_avisos(), {"encuesta": "mio"})
        panel = self._panel([_estilo("Mío", clave="mio")])
        panel.lista.SetSelection(4)
        with mock.patch.object(
                estilos_ventana.estilo_tipos_cuadro, "abrir",
                return_value=None) as abrir, \
                mock.patch.object(estilos_ventana, "anunciar"):
            panel._predeterminado()
        abrir.assert_called_once_with(panel, {"encuesta"})

    def test_p5_eliminar_un_predeterminado_lo_deja_en_clasico(self):
        estilos_aviso.guardar_por_tipo(
            paths.estilos_avisos(),
            {"comando": "mio", "encuesta": "banda"})
        panel = self._panel([_estilo("Mío", clave="mio")])
        panel.lista.SetSelection(4)
        with mock.patch.object(estilos_ventana.confirmar, "preguntar",
                               return_value=True), \
                mock.patch.object(estilos_ventana, "anunciar"):
            panel._eliminar()
        self.assertEqual(
            estilos_aviso.cargar_por_tipo(paths.estilos_avisos()),
            {"mensaje": "clasico", "comando": "clasico",
             "disparador": "clasico", "encuesta": "banda",
             "meta": "clasico"})

    def test_p8_eliminar_dice_cuantos_lo_usan_y_deja_clasico(self):
        programados.guardar(paths.mensajes_programados(), [
            _mensaje("Uno", "mio"), _mensaje("Dos", "mio"),
            _mensaje("Tres", "banda")])
        panel = self._panel([_estilo("Mío", clave="mio")])
        panel.lista.SetSelection(4)
        with mock.patch.object(estilos_ventana.confirmar, "preguntar",
                               return_value=True) as preguntar, \
                mock.patch.object(estilos_ventana, "anunciar") as decir:
            panel._eliminar()
        pregunta = preguntar.call_args
        self.assertIn("Lo usan 2 mensajes automáticos. Esos mensajes pasan "
                      "a usar Clásico.", pregunta.args[1])
        self.assertFalse(pregunta.kwargs["predeterminado_si"])
        self.assertEqual(self._nombres_en_disco(), [])
        self.assertEqual(
            [m["estilo"] for m in programados.cargar(
                paths.mensajes_programados())],
            ["clasico", "clasico", "banda"])
        decir.assert_called_once_with("Estilo eliminado")

    def test_p8_cancelar_no_elimina_ni_cambia_los_mensajes(self):
        programados.guardar(paths.mensajes_programados(),
                            [_mensaje("Uno", "mio")])
        panel = self._panel([_estilo("Mío", clave="mio")])
        panel.lista.SetSelection(4)
        with mock.patch.object(estilos_ventana.confirmar, "preguntar",
                               return_value=False):
            panel._eliminar()
        self.assertEqual(self._nombres_en_disco(), ["Mío"])
        self.assertEqual(
            [m["estilo"] for m in programados.cargar(
                paths.mensajes_programados())], ["mio"])

    def test_eliminar_un_estilo_sin_uso_no_menciona_mensajes(self):
        panel = self._panel([_estilo("Mío", clave="mio")])
        panel.lista.SetSelection(4)
        with mock.patch.object(estilos_ventana.confirmar, "preguntar",
                               return_value=False) as preguntar, \
                mock.patch.object(estilos_ventana, "anunciar"):
            panel._eliminar()
        self.assertNotIn("Lo usan", preguntar.call_args.args[1])


class TestCuadro(BaseVentana):

    def test_p4_el_cuadro_tiene_todos_los_campos_en_su_rango(self):
        cuadro = self._cuadro(_estilo("Mío"))
        self.assertEqual(
            (cuadro.sp_tamano.GetMin(), cuadro.sp_tamano.GetMax()), (2, 15))
        self.assertAlmostEqual(cuadro.sp_tamano.GetIncrement(), 0.5)
        self.assertEqual(
            (cuadro.sp_ancho.GetMin(), cuadro.sp_ancho.GetMax()), (0, 12))
        self.assertEqual(
            (cuadro.sp_opacidad.GetMin(), cuadro.sp_opacidad.GetMax()),
            (0, 100))
        for control in (cuadro.sp_ms_entrada, cuadro.sp_ms_salida):
            self.assertEqual((control.GetMin(), control.GetMax()), (100, 1000))
            self.assertAlmostEqual(control.GetIncrement(), 50)
        self.assertEqual(cuadro.cho_alineacion.GetStrings(),
                         ["Izquierda", "Centro", "Derecha"])
        self.assertEqual(cuadro.cho_zona.GetCount(),
                         len(estilos_aviso.ZONAS))
        self.assertEqual(cuadro.cho_entrada.GetStrings(),
                         [("Fundido al subir"), "Fundido", "Desde la derecha",
                          "Desde la izquierda", "Desde arriba", "Desde abajo",
                          "Ninguna"])
        self.assertEqual(cuadro.cho_salida.GetCount(),
                         len(animacion.SALIDAS))
        self.assertEqual(cuadro.cho_color_texto.GetCount(),
                         len(estilos_aviso.COLORES))
        self.assertEqual(cuadro.chk_esquinas.GetLabel(),
                         "Es&quinas redondeadas")
        self.assertEqual(cuadro.chk_sombra.GetLabel(), "So&mbra")

    def test_cada_control_tiene_el_nombre_de_su_rotulo(self):
        cuadro = self._cuadro(_estilo("Mío"))
        nombres = {
            "Nombre": cuadro.txt_nombre,
            "Fuente": cuadro.cho_fuente,
            "Tamaño (% del lado menor del vídeo)": cuadro.sp_tamano,
            "Negrita": cuadro.chk_negrita,
            "Color del texto": cuadro.cho_color_texto,
            "Color del contorno": cuadro.cho_color_contorno,
            "Ancho del contorno": cuadro.sp_ancho,
            "Color del fondo": cuadro.cho_color_fondo,
            "Opacidad del fondo": cuadro.sp_opacidad,
            "Alineación": cuadro.cho_alineacion,
            "Zona": cuadro.cho_zona,
            "Animación de entrada": cuadro.cho_entrada,
            "Duración de la entrada": cuadro.sp_ms_entrada,
            "Animación de salida": cuadro.cho_salida,
            "Duración de la salida": cuadro.sp_ms_salida,
            "Esquinas redondeadas": cuadro.chk_esquinas,
            "Sombra": cuadro.chk_sombra,
        }
        for esperado, control in nombres.items():
            with self.subTest(rotulo=esperado):
                self.assertEqual(control.GetName(), esperado)

    def test_p4_aceptar_guarda_cada_campo(self):
        cuadro = self._cuadro(_estilo("Mío"))
        cuadro.txt_nombre.SetValue("Nuevo")
        cuadro.cho_fuente.SetSelection(0)
        fuente = cuadro.cho_fuente.GetString(0)
        cuadro.sp_tamano.SetValue(6.5)
        cuadro.chk_negrita.SetValue(True)
        cuadro.cho_color_texto.SetSelection(
            [valor for _nombre, valor in estilos_aviso.COLORES].index("#E53935"))
        cuadro.cho_color_contorno.SetSelection(
            [valor for _nombre, valor in estilos_aviso.COLORES].index("#1E64C8"))
        cuadro.sp_ancho.SetValue(5)
        cuadro.cho_color_fondo.SetSelection(
            [valor for _nombre, valor in estilos_aviso.COLORES].index("#2E9E44"))
        cuadro.sp_opacidad.SetValue(70)
        cuadro.cho_alineacion.SetSelection(1)
        cuadro.cho_zona.SetSelection(1)
        cuadro.cho_entrada.SetSelection(2)
        cuadro.sp_ms_entrada.SetValue(500)
        cuadro.cho_salida.SetSelection(3)
        cuadro.sp_ms_salida.SetValue(600)
        cuadro.chk_esquinas.SetValue(False)
        cuadro.chk_sombra.SetValue(True)
        datos = cuadro.datos()
        self.assertEqual(datos["nombre"], "Nuevo")
        self.assertEqual(datos["fuente"], fuente)
        self.assertEqual(datos["tamano"], 6.5)
        self.assertTrue(datos["negrita"])
        self.assertEqual(datos["color_texto"], "#E53935")
        self.assertEqual(datos["color_contorno"], "#1E64C8")
        self.assertEqual(datos["ancho_contorno"], 5)
        self.assertEqual(datos["color_fondo"], "#2E9E44")
        self.assertEqual(datos["opacidad_fondo"], 70)
        self.assertEqual(datos["alineacion"], "centro")
        self.assertEqual(datos["zona"], "arriba_izquierda")
        self.assertEqual(datos["entrada"], "derecha")
        self.assertEqual(datos["ms_entrada"], 500)
        self.assertEqual(datos["salida"], "izquierda")
        self.assertEqual(datos["ms_salida"], 600)
        self.assertEqual(datos["esquinas"], "rectas")
        self.assertTrue(datos["sombra"])

    def test_p4_un_color_personalizado_se_conserva(self):
        cuadro = self._cuadro(_estilo("Mío", color_texto="#123456"))
        self.assertEqual(cuadro.cho_color_texto.GetSelection(), 0)
        self.assertIn("Personalizado (#123456)",
                      cuadro.cho_color_texto.GetString(0))
        self.assertEqual(cuadro.datos()["color_texto"], "#123456")

    def test_p4_una_fuente_no_instalada_se_muestra_arriba(self):
        cuadro = self._cuadro(_estilo("Mío", fuente="Fuente Inexistente 967"))
        self.assertEqual(cuadro.cho_fuente.GetSelection(), 0)
        self.assertIn("(no instalada)", cuadro.cho_fuente.GetString(0))
        self.assertEqual(cuadro.datos()["fuente"], "Fuente Inexistente 967")

    def test_p4_agregar_y_editar_abren_el_cuadro(self):
        panel = self._panel([_estilo("Mío")])
        with mock.patch.object(estilo_cuadro, "abrir",
                               return_value=_estilo("Nuevo", clave="nuevo")
                               ) as abrir, \
                mock.patch.object(estilos_ventana, "anunciar"):
            panel._agregar()
        abrir.assert_called_once()
        self.assertEqual(self._nombres_en_disco(), ["Mío", "Nuevo"])
        panel.lista.SetSelection(4)
        editado = _estilo("Mío", clave="mio", tamano=7)
        with mock.patch.object(estilo_cuadro, "abrir",
                               return_value=editado) as abrir, \
                mock.patch.object(estilos_ventana, "anunciar"):
            panel._editar()
        abrir.assert_called_once()
        self.assertEqual(estilos_aviso.cargar_estilos(
            paths.estilos_avisos())[0]["tamano"], 7)

    def test_las_letras_de_acceso_no_se_repiten_en_el_cuadro(self):
        self.assertEqual(letras_repetidas(self._cuadro(_estilo("Mío"))), {})

    def test_al_abrir_el_cuadro_el_foco_queda_en_nombre(self):
        cuadro = self._cuadro()
        cuadro.Show()
        try:
            self.assertIs(wx.Window.FindFocus(), cuadro.txt_nombre)
        finally:
            cuadro.Hide()

    def test_p5_un_error_dice_y_devuelve_el_foco_al_nombre(self):
        cuadro = self._cuadro()
        with mock.patch.object(estilo_cuadro, "anunciar") as decir, \
                mock.patch.object(cuadro, "EndModal") as cerrar, \
                mock.patch.object(cuadro.txt_nombre, "SetFocus") as foco:
            cuadro._aceptar(None)
        cerrar.assert_not_called()
        decir.assert_called_once_with("El estilo necesita un nombre.")
        foco.assert_called_once()

    def test_p5_el_contraste_bajo_pregunta_con_no_predeterminado(self):
        cuadro = self._cuadro(_estilo(
            "Bajo", color_texto="#FFFF00", color_fondo="#FFFFFF",
            opacidad_fondo=100, ancho_contorno=0))
        with mock.patch.object(estilo_cuadro.confirmar, "preguntar",
                               return_value=False) as preguntar, \
                mock.patch.object(cuadro, "EndModal") as cerrar:
            cuadro._aceptar(None)
        cerrar.assert_not_called()
        self.assertFalse(preguntar.call_args.kwargs["predeterminado_si"])
        self.assertIn(estilos_aviso.aviso_contraste(cuadro.datos()),
                      preguntar.call_args.args[1])

    def test_p5_si_acepta_el_contraste_bajo_guarda(self):
        cuadro = self._cuadro(_estilo(
            "Bajo", color_texto="#FFFF00", color_fondo="#FFFFFF",
            opacidad_fondo=100, ancho_contorno=0))
        with mock.patch.object(estilo_cuadro.confirmar, "preguntar",
                               return_value=True), \
                mock.patch.object(cuadro, "EndModal") as cerrar:
            cuadro._aceptar(None)
        cerrar.assert_called_once_with(wx.ID_OK)

    def test_escape_cierra_el_cuadro(self):
        evento = mock.Mock()
        evento.GetKeyCode.return_value = wx.WXK_ESCAPE
        cuadro = self._cuadro()
        with mock.patch.object(cuadro, "EndModal") as cerrar:
            cuadro._al_tecla(evento)
        cerrar.assert_called_once_with(wx.ID_CANCEL)


class TestPaquetes(BaseVentana):

    def test_p7_exportar_e_importar_ida_y_vuelta(self):
        panel = self._panel([_estilo("Mío", clave="mio", tamano=6.5)])
        ruta = Path(self.tmp.name) / "ida.zip"
        with mock.patch.object(panel, "_pedir_ruta", return_value=ruta):
            panel._exportar()
        self.assertEqual([e["nombre"] for e in paquetes.leer(
            ruta, "estilos").elementos], ["Mío"])
        otra = self._panel([])
        with mock.patch.object(otra, "_pedir_ruta", return_value=ruta), \
                mock.patch.object(estilos_ventana, "anunciar") as decir:
            otra._importar()
        importados = estilos_aviso.cargar_estilos(paths.estilos_avisos())
        self.assertEqual([e["nombre"] for e in importados], ["Mío"])
        self.assertEqual(importados[0]["tamano"], 6.5)
        decir.assert_called_once_with("Se importó un estilo.")

    def test_p7_importar_un_nombre_repetido_agrega_copia(self):
        ruta = self._paquete([_estilo("Mío", clave="otro", tamano=7)])
        panel = self._panel([_estilo("Mío", clave="mio")])
        with mock.patch.object(panel, "_pedir_ruta", return_value=ruta), \
                mock.patch.object(estilos_ventana, "anunciar"):
            panel._importar()
        self.assertEqual(self._nombres_en_disco(), ["Mío", "Mío (copia)"])

    def test_p7_un_estilo_importado_recibe_una_clave_distinta(self):
        panel = self._panel([_estilo("Mío", clave="mio")])
        ruta = Path(self.tmp.name) / "misma.zip"
        with mock.patch.object(panel, "_pedir_ruta",
                               return_value=ruta):
            panel._exportar()
        with mock.patch.object(panel, "_pedir_ruta",
                               return_value=ruta), \
                mock.patch.object(estilos_ventana, "anunciar"):
            panel._importar()
        estilos = estilos_aviso.cargar_estilos(paths.estilos_avisos())
        self.assertEqual([e["nombre"] for e in estilos],
                         ["Mío", "Mío (copia)"])
        claves = [e["clave"] for e in estilos]
        self.assertEqual(len(set(claves)), 2)
        self.assertNotIn(estilos[1]["clave"],
                         {e["clave"] for e in estilos_aviso.FABRICA}
                         | {claves[0]})

    def test_p7_un_paquete_de_otro_tipo_se_informa(self):
        ruta = self._paquete([_estilo("Mío")], tipo="avisos")
        panel = self._panel([])
        with mock.patch.object(panel, "_pedir_ruta", return_value=ruta), \
                mock.patch.object(estilos_ventana.confirmar,
                                  "avisar") as avisar:
            panel._importar()
        avisar.assert_called_once()
        self.assertIn("avisos", avisar.call_args.args[1])

    def test_exportar_sin_estilos_propios_no_abre_nada(self):
        panel = self._panel([])
        with mock.patch.object(panel, "_pedir_ruta") as pedir, \
                mock.patch.object(estilos_ventana, "anunciar") as decir:
            panel._exportar()
        pedir.assert_not_called()
        decir.assert_called_once_with("No hay estilos propios para exportar.")


if __name__ == "__main__":
    unittest.main()
