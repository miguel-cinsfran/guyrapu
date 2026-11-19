# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Ventana de comandos del chat: lista, acciones, cuadro y cableado.

Abre ventanas.
"""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import wx

from guyrapu.core import paths
from guyrapu.interaction import comandos_guardados, paquetes
from guyrapu.obs import estilos_aviso
from guyrapu.ui import comando_cuadro
from guyrapu.ui import comandos_ventana
from tests.letras_acceso import letras_repetidas
from tests.rutas_temporales import redirigir_rutas
from tests.ventanas_prueba import app_de_prueba, destruir

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "qa"))
from qa import escenarios_comandos  # noqa: E402


def _datos(nombre="discord", **cambios):
    datos = {
        "nombre": nombre, "alias": ["dc"], "respuesta": "Hola",
        "destino": "video", "permiso": "todos", "nombres": [],
        "espera_general": 5.0, "espera_persona": 30.0, "activo": True,
        "estilo": "clasico", "segundos": 8,
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
            comandos_guardados.guardar(paths.comandos(), lista)
        marco = wx.Frame(None)
        self.addCleanup(destruir, marco)
        panel = comandos_ventana.PanelComandos(marco)
        self.addCleanup(destruir, panel)
        return panel

    def _nombres_en_disco(self):
        return [c["nombre"] for c in comandos_guardados.cargar(paths.comandos())]

    def _indice(self, panel, nombre):
        return next(indice for indice, comando in enumerate(panel._comandos)
                    if comando["nombre"] == nombre)

    def _cuadro(self, datos=None, otros=()):
        cuadro = comando_cuadro.DialogoComando(None, datos or {}, otros)
        self.addCleanup(destruir, cuadro)
        return cuadro

    def _paquete(self, elementos):
        ruta = Path(self.tmp.name) / "paquete.zip"
        paquetes.exportar(ruta, "comandos", elementos)
        return ruta


class TestContratos(BaseVentana):

    def test_el_panel_lee_los_comandos_al_abrir(self):
        panel = self._panel([_datos("discord"), _datos(
            "hola", alias=[], destino="chat", permiso="lista",
            nombres=["Ana"])])
        self.assertEqual(panel.lista.GetCount(), 3)
        self.assertEqual(panel.lista.GetString(0),
                         "!commands, en el vídeo, todos")
        self.assertEqual(panel.lista.GetString(1),
                         "!discord, en el vídeo, todos")
        self.assertEqual(
            panel.lista.GetString(2),
            "!hola, en el chat, una lista de nombres: Ana")

    def test_la_lista_de_fabrica_aparece_con_coleccion_nueva_y_archivo_danado(self):
        panel = self._panel([])
        self.assertEqual(panel.lista.GetCount(), 1)
        self.assertEqual(panel.lista.GetString(0),
                         "!commands, en el vídeo, todos")
        paths.comandos().write_text("{roto", encoding="utf-8")
        panel = self._panel()
        self.assertEqual(panel.lista.GetCount(), 1)
        self.assertEqual(panel.lista.GetString(0),
                         "!commands, en el vídeo, todos")

    def test_los_botones_del_panel_estan_encendidos(self):
        panel = self._panel([])
        botones = [hijo for hijo in panel.GetChildren()
                   if isinstance(hijo, wx.Button)]
        self.assertTrue(botones)
        self.assertTrue(all(boton.IsEnabled() for boton in botones))

    def test_sin_comandos_las_acciones_dicen_por_que(self):
        with mock.patch.object(comandos_guardados, "cargar", return_value=[]):
            panel = self._panel()
        with mock.patch("guyrapu.ui.lista_acciones.anunciar") as decir:
            panel._lista.ejecutar("editar")
        decir.assert_called_once_with(
            "No hay comandos. Usa Agregar para crear uno.")

    def test_escape_cierra_el_cuadro(self):
        evento = mock.Mock()
        evento.GetKeyCode.return_value = wx.WXK_ESCAPE
        cuadro = self._cuadro()
        with mock.patch.object(cuadro, "EndModal") as cerrar:
            cuadro._al_tecla(evento)
        cerrar.assert_called_once_with(wx.ID_CANCEL)


class TestCuadro(BaseVentana):

    def test_tiene_todos_los_campos(self):
        cuadro = self._cuadro()
        self.assertEqual(cuadro.cho_destino.GetStrings(),
                         ["En el vídeo", "En el chat",
                          "En el vídeo y en el chat"])
        self.assertEqual(cuadro.cho_permiso.GetStrings(),
                         ["Todos", "Solo moderadores",
                          "Una lista de nombres"])
        self.assertEqual((cuadro.sp_segundos.GetMin(),
                          cuadro.sp_segundos.GetMax()), (3, 60))
        self.assertEqual((cuadro.sp_espera.GetMin(),
                          cuadro.sp_espera.GetMax()), (0, 3600))
        self.assertEqual((cuadro.sp_persona.GetMin(),
                          cuadro.sp_persona.GetMax()), (0, 3600))
        self.assertTrue(cuadro.chk_activo.GetValue())
        self.assertEqual(cuadro.cho_estilo.GetCount(), 5)
        self.assertEqual(cuadro.ayuda.GetLabel(),
                         "Puedes usar {usuario}, {contador} y {texto}.")
        self.assertTrue(cuadro.chk_en_lista.GetValue())
        self.assertEqual(cuadro.chk_en_lista.GetName(),
                         "Mostrar en la lista de comandos")

    def test_el_comando_de_lista_no_tiene_la_casilla_y_acepta_la_variable(self):
        datos = _datos(nombre="commands", respuesta="Comandos: {lista}.",
                       lista=True)
        cuadro = self._cuadro(datos)
        self.assertFalse(cuadro.chk_en_lista.IsShown())
        self.assertEqual(cuadro.ayuda.GetLabel(),
                         "Puedes usar {usuario}, {contador}, {texto} y {lista}.")
        with mock.patch.object(cuadro, "EndModal") as cerrar:
            cuadro._aceptar(None)
        cerrar.assert_called_once_with(wx.ID_OK)
        self.assertTrue(cuadro.datos()["lista"])

    def test_p3_la_eleccion_empieza_por_el_predeterminado(self):
        cuadro = self._cuadro()
        self.assertEqual(cuadro.cho_estilo.GetString(0),
                         "Predeterminado (Clásico)")
        self.assertEqual(cuadro.cho_estilo.GetSelection(), 0)
        self.assertEqual(cuadro.datos()["estilo"], "")

    def test_p3_el_predeterminado_lleva_el_nombre_del_estilo_del_tipo(self):
        estilos_aviso.guardar_por_tipo(
            paths.estilos_avisos(), {"comando": "banda"})
        cuadro = self._cuadro()
        self.assertEqual(cuadro.cho_estilo.GetString(0),
                         "Predeterminado (Banda)")

    def test_p3_elegir_predeterminado_guarda_el_estilo_vacio(self):
        cuadro = self._cuadro(_datos(estilo="banda"))
        self.assertEqual(cuadro.cho_estilo.GetSelection(), 2)
        cuadro.cho_estilo.SetSelection(0)
        self.assertEqual(cuadro.datos()["estilo"], "")

    def test_las_letras_de_acceso_no_se_repiten_en_el_cuadro(self):
        self.assertEqual(letras_repetidas(self._cuadro()), {})

    def test_el_foco_nace_en_palabra(self):
        cuadro = self._cuadro()
        cuadro.Show()
        try:
            self.assertIs(wx.Window.FindFocus(), cuadro.txt_palabra)
        finally:
            cuadro.Hide()

    def test_guarda_cada_campo(self):
        cuadro = self._cuadro()
        cuadro.txt_palabra.SetValue("!sorteo")
        cuadro.txt_alias.SetValue("sorteo, sort")
        cuadro.txt_respuesta.SetValue("Hola {usuario}")
        cuadro.cho_destino.SetSelection(2)
        cuadro.cho_permiso.SetSelection(2)
        cuadro.txt_nombres.SetValue("Ana María, Beto")
        cuadro.sp_espera.SetValue(10)
        cuadro.sp_persona.SetValue(40)
        cuadro._elegir_estilo("banda")
        cuadro.sp_segundos.SetValue(15)
        cuadro.chk_activo.SetValue(False)
        cuadro.chk_en_lista.SetValue(False)
        self.assertEqual(cuadro.datos(), {
            "nombre": "sorteo", "alias": ["sorteo", "sort"],
            "respuesta": "Hola {usuario}", "destino": "ambos",
            "permiso": "lista", "nombres": ["Ana María", "Beto"],
            "espera_general": 10.0, "espera_persona": 40.0,
            "activo": False, "estilo": "banda", "segundos": 15,
            "lista": False, "en_lista": False})
        with mock.patch.object(cuadro, "EndModal") as cerrar:
            cuadro._aceptar(None)
        cerrar.assert_called_once_with(wx.ID_OK)

    def _aceptar_con_error(self, cuadro):
        with mock.patch.object(comando_cuadro, "anunciar") as decir, \
                mock.patch.object(cuadro, "EndModal") as cerrar:
            cuadro._aceptar(None)
        cerrar.assert_not_called()
        return decir

    def test_comandos_ya_es_una_palabra_valida(self):
        cuadro = self._cuadro()
        cuadro.txt_palabra.SetValue("comandos")
        cuadro.txt_respuesta.SetValue("Hola")
        with mock.patch.object(cuadro, "EndModal") as cerrar:
            cuadro._aceptar(None)
        cerrar.assert_called_once_with(wx.ID_OK)

    def test_una_variable_desconocida_manda_el_foco_a_la_respuesta(self):
        cuadro = self._cuadro()
        cuadro.txt_palabra.SetValue("hola")
        cuadro.txt_respuesta.SetValue("Hola {quien}")
        with mock.patch.object(cuadro.txt_respuesta, "SetFocus") as foco:
            decir = self._aceptar_con_error(cuadro)
        foco.assert_called_once()
        self.assertIn("{usuario}", decir.call_args.args[0])

    def test_el_chat_largo_manda_el_foco_a_la_respuesta(self):
        cuadro = self._cuadro()
        cuadro.txt_palabra.SetValue("hola")
        cuadro.txt_respuesta.SetValue("a" * 201)
        cuadro.cho_destino.SetSelection(1)
        with mock.patch.object(cuadro.txt_respuesta, "SetFocus") as foco:
            self._aceptar_con_error(cuadro)
        foco.assert_called_once()

    def test_la_lista_vacia_manda_el_foco_a_los_nombres(self):
        cuadro = self._cuadro()
        cuadro.txt_palabra.SetValue("hola")
        cuadro.txt_respuesta.SetValue("Hola")
        cuadro.cho_permiso.SetSelection(2)
        with mock.patch.object(cuadro.txt_nombres, "SetFocus") as foco:
            self._aceptar_con_error(cuadro)
        foco.assert_called_once()

class TestAcciones(BaseVentana):

    def test_tiene_las_acciones_con_sus_teclas(self):
        panel = self._panel([])
        self.assertEqual([(a.clave, a.tecla) for a in panel._acciones], [
            ("agregar", None), ("editar", "intro"), ("renombrar", "f2"),
            ("duplicar", "ctrl+d"), ("pausar", None), ("escuchar", None),
            ("eliminar", "suprimir"), ("exportar", None), ("importar", None)])
        sin_elemento = {a.clave for a in panel._acciones
                        if not a.necesita_elemento}
        self.assertEqual(sin_elemento, {"agregar", "exportar", "importar"})

    def test_cada_tecla_llega_a_su_accion(self):
        from guyrapu.ui import lista_acciones
        acciones = self._panel([])._acciones
        for codigo, modificadores, esperada in (
                (wx.WXK_RETURN, wx.MOD_NONE, "editar"),
                (wx.WXK_F2, wx.MOD_NONE, "renombrar"),
                (ord("D"), wx.MOD_CONTROL, "duplicar"),
                (wx.WXK_DELETE, wx.MOD_NONE, "eliminar")):
            with self.subTest(esperada=esperada):
                self.assertEqual(
                    lista_acciones.clave_de_tecla(
                        codigo, modificadores, acciones), esperada)

    def test_duplicar_deja_la_copia_debajo(self):
        panel = self._panel([_datos("A"), _datos("B")])
        indice = self._indice(panel, "A")
        panel.lista.SetSelection(indice)
        with mock.patch.object(comandos_ventana, "anunciar") as decir:
            panel._duplicar()
        self.assertEqual(self._nombres_en_disco(),
                         ["commands", "A", "A (copia)", "B"])
        self.assertEqual(panel.lista.GetSelection(), indice + 1)
        decir.assert_called_once_with("Comando duplicado")

    def test_pausar_cambia_el_estado_y_la_fila(self):
        panel = self._panel([_datos("A")])
        indice = self._indice(panel, "A")
        panel.lista.SetSelection(indice)
        with mock.patch.object(comandos_ventana, "anunciar") as decir:
            panel._pausar()
        guardado = comandos_guardados.cargar(paths.comandos())
        self.assertFalse(next(c["activo"] for c in guardado
                              if c["nombre"] == "A"))
        self.assertEqual(panel.lista.GetString(indice),
                         "!A, en el vídeo, todos, pausado")
        decir.assert_called_once_with("Pausado")

    def test_renombrar_repite_la_validacion(self):
        panel = self._panel([_datos("A")])
        panel.lista.SetSelection(self._indice(panel, "A"))
        with mock.patch.object(comando_cuadro, "pedir_palabra",
                               side_effect=["mi comando", "nuevo"]), \
                 mock.patch.object(comandos_ventana, "anunciar") as decir:
            panel._renombrar()
        self.assertEqual(self._nombres_en_disco(), ["commands", "nuevo"])
        self.assertIn("espacios", decir.call_args_list[0].args[0])


    def test_escuchar_cuenta_el_comando(self):
        panel = self._panel([_datos("A", alias=[], respuesta="Hola")])
        panel.lista.SetSelection(self._indice(panel, "A"))
        with mock.patch.object(
                comandos_ventana.estilos_aviso, "buscar",
                return_value={"nombre": "Clásico"}), \
                mock.patch.object(comandos_ventana, "anunciar") as decir:
            panel._escuchar()
        self.assertIn("Comando !A.", decir.call_args.args[0])
        self.assertIn("estilo Clásico", decir.call_args.args[0])

    def test_p4_escuchar_usa_el_predeterminado_del_tipo(self):
        estilos_aviso.guardar_por_tipo(
            paths.estilos_avisos(), {"comando": "banda"})
        panel = self._panel([_datos(
            "A", alias=[], respuesta="Hola", estilo="")])
        panel.lista.SetSelection(self._indice(panel, "A"))
        with mock.patch.object(comandos_ventana, "anunciar") as decir:
            panel._escuchar()
        self.assertIn("estilo Banda", decir.call_args.args[0])

    def test_eliminar_pide_confirmacion_con_no_predeterminado(self):
        panel = self._panel([_datos("A"), _datos("B")])
        panel.lista.SetSelection(self._indice(panel, "A"))
        with mock.patch.object(comandos_ventana.confirmar, "preguntar",
                               return_value=True) as preguntar, \
                 mock.patch.object(comandos_ventana, "anunciar") as decir:
            panel._eliminar()
        self.assertFalse(preguntar.call_args.kwargs["predeterminado_si"])
        self.assertEqual(self._nombres_en_disco(), ["commands", "B"])

        decir.assert_called_once_with("Comando eliminado")

    def test_el_comando_de_lista_no_se_puede_eliminar_ni_duplicar(self):
        panel = self._panel([_datos("A")])
        panel.lista.SetSelection(self._indice(panel, "commands"))
        with mock.patch("guyrapu.ui.lista_acciones.anunciar") as decir:
            self.assertTrue(panel._lista.ejecutar("eliminar"))
            self.assertTrue(panel._lista.ejecutar("duplicar"))
        self.assertEqual(self._nombres_en_disco(), ["commands", "A"])
        self.assertEqual(decir.call_count, 2)
        for llamada in decir.call_args_list:
            self.assertEqual(
                llamada.args[0],
                "La lista de comandos no se puede eliminar ni duplicar.")

    def test_un_paquete_no_trae_otro_comando_de_lista(self):
        ruta = self._paquete([_datos("externo", lista=True)])
        panel = self._panel([_datos("A")])
        with mock.patch.object(panel, "_pedir_ruta", return_value=ruta), \
                mock.patch.object(panel, "_preguntar_reemplazo",
                                  return_value=False), \
                mock.patch.object(comandos_ventana, "anunciar"):
            panel._importar()
        guardados = comandos_guardados.cargar(paths.comandos())
        externo = next(c for c in guardados if c["nombre"] == "externo")
        self.assertFalse(externo["lista"])
        self.assertEqual([c["nombre"] for c in guardados if c.get("lista")],
                         ["commands"])

    def test_exportar_con_la_lista_vacia_no_abre_nada(self):
        with mock.patch.object(comandos_guardados, "cargar", return_value=[]):
            panel = self._panel()
        with mock.patch.object(panel, "_pedir_ruta") as pedir, \
                mock.patch.object(comandos_ventana, "anunciar") as decir:
            panel._exportar()
        pedir.assert_not_called()
        decir.assert_called_once_with("No hay comandos para exportar.")

    def test_exportar_e_importar_pausan_lo_importado(self):
        panel = self._panel([_datos("A")])
        ruta = Path(self.tmp.name) / "salida.zip"
        with mock.patch.object(panel, "_pedir_ruta", return_value=ruta):
            panel._exportar()
        panel = self._panel([_datos("A")])
        with mock.patch.object(panel, "_pedir_ruta", return_value=ruta), \
                mock.patch.object(panel, "_preguntar_reemplazo",
                                  return_value=False), \
                mock.patch.object(comandos_ventana, "anunciar"):
            panel._importar()
        importados = [c for c in comandos_guardados.cargar(paths.comandos())
                      if c["nombre"] == "A (copia)"]
        self.assertEqual([c["activo"] for c in importados], [False])


class TestPanelSuelto(BaseVentana):

    def test_el_panel_funciona_dentro_de_un_frame_cualquiera(self):
        comandos_guardados.guardar(paths.comandos(), [_datos("A")])
        marco = wx.Frame(None)
        self.addCleanup(destruir, marco)
        panel = comandos_ventana.PanelComandos(marco)
        self.assertIs(panel.GetParent(), marco)
        panel.lista.SetSelection(self._indice(panel, "A"))
        with mock.patch.object(comandos_ventana, "anunciar") as decir:
            panel._duplicar()
        self.assertEqual(self._nombres_en_disco(),
                         ["commands", "A", "A (copia)"])
        decir.assert_called_once_with("Comando duplicado")


class TestEscenarioDelBanco(BaseVentana):

    def test_el_escenario_conoce_las_acciones_del_panel(self):
        panel = self._panel([])
        etiquetas = {accion.etiqueta.replace("&", "")
                     for accion in panel._acciones}
        self.assertEqual(set(escenarios_comandos.ACCIONES), etiquetas)


if __name__ == "__main__":
    unittest.main()
