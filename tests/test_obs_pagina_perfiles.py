# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de la pestaña Perfiles del Panel de OBS, con OBS falso."""

import configparser
import dataclasses
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import wx

from tests.ventanas_prueba import app_de_prueba, destruir
from guyrapu.core.idioma import _
from guyrapu.obs import ajustes_perfil, codificadores_obs, obs_cliente
from guyrapu.obs import asistente_perfiles
from guyrapu.obs import perfiles_obs, salidas_audio
from guyrapu.ui import gui
from guyrapu.ui import lista_acciones
from guyrapu.ui import obs_pagina_perfiles as pagina_mod
from guyrapu.ui.obs_pagina_perfiles import PaginaPerfiles


class ClienteFalso:
    def pedir(self, tipo, datos=None, parada=None):
        return {"responseData": {}}


class GestorFalso:
    def __init__(self):
        self._cliente = ClienteFalso()


class OperacionesFalsas:
    """Corre en el acto y anuncia los fallos como `OperacionesObs`."""

    def __init__(self, anunciar):
        self._anunciar = anunciar
        self.fallos = []
        self.cerrando = False
        self.en_vuelo = False

    def en_hilo(self, funcion, al_terminar=None):
        try:
            resultado = funcion()
        except obs_cliente.ObsError as error:
            self.fallos.append(str(error))
            self._anunciar(str(error))
            return
        if al_terminar is not None:
            al_terminar(resultado)


class _DialogoNombreFalso:
    devuelve = ("Copia", False)
    visto = {}

    def __init__(self, padre, existentes=(), con_orientacion=False,
                 titulo="", accion=""):
        type(self).visto = {"existentes": existentes,
                            "con_orientacion": con_orientacion}

    def ShowModal(self):
        return wx.ID_OK

    def Destroy(self):
        pass

    def nombre(self):
        return type(self).devuelve[0]

    def vertical(self):
        return type(self).devuelve[1]


class _DialogoUsosFalso:
    marcados_ = {}
    visto = {}
    resultado = wx.ID_OK

    def __init__(self, padre, nombre, config):
        type(self).visto = {"nombre": nombre, "config": dict(config)}

    def ShowModal(self):
        return type(self).resultado

    def Destroy(self):
        pass

    def marcados(self):
        return dict(type(self).marcados_)


class _DialogoAjustesFalso:
    visto = {}
    devuelve = None
    pasar = False

    def __init__(self, padre, ajustes, nombre, avanzado=False,
                 personalizado=True, salidas=(), codificadores=None):
        type(self).visto = {
            "ajustes": ajustes, "nombre": nombre, "avanzado": avanzado,
            "personalizado": personalizado, "salidas": salidas,
            "codificadores": codificadores}

    def ShowModal(self):
        return wx.ID_OK

    def Destroy(self):
        pass

    def pasar_a_sencillo_pedido(self):
        return type(self).pasar

    def ajustes(self):
        return type(self).devuelve


class _AsistenteFalso:
    resultado = None
    visto = {}

    def __init__(self, ventana, operaciones, cliente, config, al_terminar):
        type(self).visto = {"config": dict(config)}
        self._al_terminar = al_terminar

    def empezar(self):
        self._al_terminar(type(self).resultado)


def de_prueba(**cambios):
    return dataclasses.replace(ajustes_perfil.valores_iniciales(False, "x264"),
                               **cambios)


class BasePagina(unittest.TestCase):

    def setUp(self):
        self.app = app_de_prueba()
        self.anuncios = []
        self._parche = mock.patch.object(
            pagina_mod, "anunciar", lambda texto, *a, **k:
            self.anuncios.append(texto))
        self._parche.start()
        self.addCleanup(self._parche.stop)
        self.operaciones = OperacionesFalsas(
            lambda texto: self.anuncios.append(texto))
        self.marco = wx.Frame(None)
        self.addCleanup(destruir, self.marco)
        self.principal = SimpleNamespace(_config={})
        self.pagina = PaginaPerfiles(self.marco, self.principal, GestorFalso(),
                                     self.operaciones)
        self.addCleanup(destruir, self.pagina)
        self.lista = mock.patch.object(
            perfiles_obs, "listar_perfiles",
            return_value=(["Uno", "Dos"], "Uno"))
        self.lista.start()
        self.addCleanup(self.lista.stop)

    def _fijar(self, perfiles=("Uno", "Dos"), actual="Uno"):
        self.pagina.fijar(list(perfiles), actual)

    def _elegir(self, nombre):
        self.pagina.lista.SetSelection(self.pagina._perfiles.index(nombre))

    def _pulsar(self, boton):
        evento = wx.CommandEvent(wx.EVT_BUTTON.typeId, boton.GetId())
        boton.GetEventHandler().ProcessEvent(evento)

    def _tecla(self, codigo):
        evento = wx.KeyEvent(wx.wxEVT_KEY_DOWN)
        evento.KeyCode = codigo
        self.pagina.lista.GetEventHandler().ProcessEvent(evento)


class TestPestana(BasePagina):

    def test_la_lista_dice_el_nombre_y_cual_esta_en_uso(self):
        self.pagina.releer()
        self.assertEqual(
            self.pagina.lista.GetStrings(),
            ["Uno (en uso)", "Dos"])

    def test_la_lista_dice_los_usos_asignados(self):
        self.principal._config.update(
            {"perfil_horizontal": "Uno", "perfil_grabar": "Uno"})
        self._fijar()
        self.assertEqual(
            self.pagina.lista.GetStrings(),
            ["Uno (en uso, para transmitir en horizontal, para grabar)",
             "Dos"])

    def test_la_lista_tiene_su_nombre_accesible(self):
        self.assertEqual(self.pagina.lista.GetName(), "Perfiles de OBS")

    def test_estan_los_siete_botones_de_la_pestana(self):
        etiquetas = [boton.GetLabel() for boton in (
            self.pagina.btn_usar, self.pagina.btn_usar_para,
            self.pagina.btn_nuevo, self.pagina.btn_duplicar,
            self.pagina.btn_eliminar, self.pagina.btn_editar,
            self.pagina.btn_preparar)]
        self.assertEqual(etiquetas, [
            "&Usar este perfil", "Usar p&ara…", "&Nuevo…", "&Duplicar…",
            "&Eliminar perfil", "Editar a&justes…", "&Preparar perfiles…"])

    def test_el_boton_usar_para_tiene_su_nombre_accesible(self):
        self.assertEqual(self.pagina.btn_usar_para.GetName(), "Usar para…")

    def test_el_boton_preparar_tiene_su_nombre_accesible(self):
        self.assertEqual(self.pagina.btn_preparar.GetName(),
                         "Preparar perfiles…")

    def test_fijar_vacio_deja_la_linea_de_vacio_elegida(self):
        self.pagina.fijar([], "")
        self.assertEqual(self.pagina.lista.GetCount(), 1)
        self.assertEqual(
            self.pagina.lista.GetString(0),
            _("No hay perfiles en OBS. Usa Nuevo… para crear uno."))
        self.assertEqual(self.pagina.lista.GetSelection(), 0)
        self.assertEqual(self.pagina._elegido(), "")

    def test_el_menu_tiene_las_siete_acciones_en_orden(self):
        self._fijar()
        vistos = []

        def popup(menu):
            vistos.extend(item.GetItemLabel()
                          for item in menu.GetMenuItems())

        evento = wx.KeyEvent(wx.wxEVT_KEY_DOWN)
        evento.KeyCode = wx.WXK_WINDOWS_MENU
        with mock.patch.object(self.pagina.lista, "PopupMenu",
                               side_effect=popup):
            self.pagina.lista.GetEventHandler().ProcessEvent(evento)
        self.assertEqual(vistos, [
            "&Usar este perfil", "Usar p&ara…", "&Nuevo…",
            "&Duplicar…\tCtrl+D", "&Eliminar perfil\tDel",
            "Editar a&justes…\tEnter", "&Preparar perfiles…"])

    def test_ctrl_d_duplica_el_perfil_elegido(self):
        self._fijar()
        self._elegir("Dos")
        evento = mock.Mock()
        evento.GetKeyCode.return_value = ord("D")
        evento.GetModifiers.return_value = wx.MOD_CONTROL
        with mock.patch.object(self.pagina, "duplicar") as duplicar:
            self.pagina._lista_acciones._al_tecla(evento)
        duplicar.assert_called_once_with()


class TestPrepararPerfiles(BasePagina):

    def _archivo(self):
        base = tempfile.TemporaryDirectory()
        self.addCleanup(base.cleanup)
        ruta = Path(base.name) / "config.ini"
        ruta.write_text(
            "[transmision]\nperfil_horizontal =\nperfil_vertical =\n"
            "perfil_grabar =\n", encoding="utf-8")
        return ruta

    def _leer(self, ruta, clave):
        parser = configparser.ConfigParser(interpolation=None)
        parser.read(ruta, encoding="utf-8")
        return parser.get("transmision", clave)

    def test_los_perfiles_del_asistente_quedan_asignados(self):
        ruta = self._archivo()
        _AsistenteFalso.resultado = asistente_perfiles.ResultadoAsistente((
            asistente_perfiles.PerfilPreparado(
                "Guyrapu horizontal", "perfil_horizontal", de_prueba()),
            asistente_perfiles.PerfilPreparado(
                "Guyrapu grabación", "perfil_grabar", de_prueba()),
        ))
        with mock.patch.object(pagina_mod, "AsistentePerfilesPanel",
                               _AsistenteFalso), \
                mock.patch.object(gui, "RUTA_CONFIG", ruta):
            self.pagina.preparar_perfiles()
        self.assertEqual(self._leer(ruta, "perfil_horizontal"),
                         "Guyrapu horizontal")
        self.assertEqual(self._leer(ruta, "perfil_grabar"),
                         "Guyrapu grabación")
        self.assertEqual(self.principal._config["perfil_horizontal"],
                         "Guyrapu horizontal")
        self.assertEqual(self.principal._config["perfil_grabar"],
                         "Guyrapu grabación")


class TestUsar(BasePagina):

    def test_pasa_al_perfil_elegido_y_lo_anuncia(self):
        self._fijar()
        self._elegir("Dos")
        with mock.patch.object(perfiles_obs, "cambiar_perfil") as cambiar:
            self.pagina.usar()
        cambiar.assert_called_once_with(self.pagina._cliente(), "Dos")
        self.assertIn("Perfil en uso: Dos.", self.anuncios)


class TestUsarPara(BasePagina):

    def _archivo(self, texto):
        base = tempfile.TemporaryDirectory()
        self.addCleanup(base.cleanup)
        ruta = Path(base.name) / "config.ini"
        ruta.write_text(texto, encoding="utf-8")
        return ruta

    def _leer(self, ruta, clave):
        parser = configparser.ConfigParser(interpolation=None)
        parser.read(ruta, encoding="utf-8")
        return parser.get("transmision", clave)

    def test_aceptar_guarda_en_el_archivo_y_en_la_memoria(self):
        ruta = self._archivo("[transmision]\nperfil_grabar =\n")
        self._fijar()
        self._elegir("Dos")
        _DialogoUsosFalso.marcados_ = {"perfil_grabar": True}
        _DialogoUsosFalso.resultado = wx.ID_OK
        with mock.patch.object(pagina_mod, "DialogoUsosPerfil",
                               _DialogoUsosFalso), \
                mock.patch.object(gui, "RUTA_CONFIG", ruta):
            self.pagina.usar_para()
        self.assertEqual(self._leer(ruta, "perfil_grabar"), "Dos")
        self.assertEqual(self.principal._config["perfil_grabar"], "Dos")
        self.assertIn("Dos: para grabar.", self.anuncios)

    def test_cancelar_no_cambia_nada(self):
        ruta = self._archivo("[transmision]\nperfil_grabar = Grabar\n")
        self._fijar()
        self._elegir("Dos")
        _DialogoUsosFalso.marcados_ = {"perfil_grabar": True}
        _DialogoUsosFalso.resultado = wx.ID_CANCEL
        with mock.patch.object(pagina_mod, "DialogoUsosPerfil",
                               _DialogoUsosFalso), \
                mock.patch.object(gui, "RUTA_CONFIG", ruta):
            self.pagina.usar_para()
        self.assertEqual(self._leer(ruta, "perfil_grabar"), "Grabar")
        self.assertNotIn("perfil_grabar", self.principal._config)

    def test_sin_cambios_no_guarda_y_lo_anuncia(self):
        ruta = self._archivo("[transmision]\nperfil_grabar = Dos\n")
        self.principal._config["perfil_grabar"] = "Dos"
        self._fijar()
        self._elegir("Dos")
        _DialogoUsosFalso.marcados_ = {"perfil_grabar": True}
        _DialogoUsosFalso.resultado = wx.ID_OK
        with mock.patch.object(pagina_mod, "DialogoUsosPerfil",
                               _DialogoUsosFalso), \
                mock.patch.object(gui, "RUTA_CONFIG", ruta), \
                mock.patch.object(gui, "guardar_opcion") as guardar:
            self.pagina.usar_para()
        guardar.assert_not_called()
        self.assertIn("Sin cambios.", self.anuncios)


class TestNuevo(BasePagina):

    def _parches_ajustes(self):
        return (
            mock.patch.object(perfiles_obs, "leer_para_editar",
                              return_value=(de_prueba(), False, True)),
            mock.patch.object(salidas_audio, "salidas",
                              return_value=(("default", "Por defecto"),)),
            mock.patch.object(codificadores_obs, "codificadores_disponibles",
                              return_value=("x264",)),
        )

    def test_pide_orientacion_y_crea_con_ella(self):
        _DialogoNombreFalso.devuelve = ("Nuevo", True)
        with mock.patch.object(pagina_mod, "DialogoNombrePerfil",
                               _DialogoNombreFalso), \
                mock.patch.object(self.pagina, "_leer_para_editar",
                                  return_value=("Nuevo",)), \
                mock.patch.object(self.pagina, "_abrir_ajustes"), \
                mock.patch.object(perfiles_obs, "crear_perfil") as crear:
            self.pagina.nuevo()
        self.assertTrue(_DialogoNombreFalso.visto["con_orientacion"])
        crear.assert_called_once_with(self.pagina._cliente(), "Nuevo",
                                      vertical=True)
        self.assertIn("Perfil creado: Nuevo.", self.anuncios)

    def test_al_crear_abre_los_ajustes_y_deja_el_foco_en_el_nuevo(self):
        _DialogoNombreFalso.devuelve = ("Nuevo", True)
        _DialogoAjustesFalso.visto = {}
        _DialogoAjustesFalso.pasar = False
        _DialogoAjustesFalso.devuelve = de_prueba()
        for parche in self._parches_ajustes():
            parche.start()
            self.addCleanup(parche.stop)
        with mock.patch.object(pagina_mod, "DialogoNombrePerfil",
                               _DialogoNombreFalso), \
                mock.patch.object(pagina_mod, "DialogoAjustesPerfil",
                                  _DialogoAjustesFalso), \
                mock.patch.object(_DialogoAjustesFalso, "ShowModal",
                                  return_value=wx.ID_CANCEL), \
                mock.patch.object(perfiles_obs, "crear_perfil"), \
                mock.patch.object(perfiles_obs, "listar_perfiles",
                                  return_value=(["Uno", "Dos", "Nuevo"],
                                                "Uno")):
            self._pulsar(self.pagina.btn_nuevo)
        self.assertEqual(_DialogoAjustesFalso.visto.get("nombre"), "Nuevo")
        self.assertEqual(self.pagina._elegido(), "Nuevo")


class TestDuplicar(BasePagina):

    def test_duplica_el_elegido_con_el_nombre_pedido(self):
        _DialogoNombreFalso.devuelve = ("Copia", False)
        self._fijar()
        self._elegir("Dos")
        with mock.patch.object(pagina_mod, "DialogoNombrePerfil",
                               _DialogoNombreFalso), \
                mock.patch.object(perfiles_obs, "duplicar_perfil") as duplicar:
            self.pagina.duplicar()
        duplicar.assert_called_once_with(self.pagina._cliente(), "Dos",
                                         "Copia")
        self.assertIn("Perfil duplicado: Copia.", self.anuncios)


class TestEliminar(BasePagina):

    def test_no_elimina_el_que_esta_en_uso_y_dice_por_que(self):
        self._fijar()
        self._elegir("Uno")
        with mock.patch.object(pagina_mod.confirmar, "preguntar") as preguntar:
            self.pagina.eliminar()
        preguntar.assert_not_called()
        self.assertIn(_(perfiles_obs.MENSAJE_EN_USO), self.anuncios)

    def test_no_elimina_el_unico_y_dice_por_que(self):
        self._fijar(("Uno",), "Dos")
        self._elegir("Uno")
        self.pagina.eliminar()
        self.assertIn(_(perfiles_obs.MENSAJE_UNICO), self.anuncios)

    def test_pide_confirmacion_y_elimina(self):
        self._fijar(("Uno", "Dos", "Tres"))
        self._elegir("Dos")
        with mock.patch.object(pagina_mod.confirmar, "preguntar",
                               return_value=True) as preguntar, \
                mock.patch.object(perfiles_obs, "eliminar_perfil") as eliminar:
            self.pagina.eliminar()
        preguntar.assert_called_once()
        eliminar.assert_called_once_with(self.pagina._cliente(), "Dos")
        self.assertIn("Perfil eliminado: Dos.", self.anuncios)

    def test_suprimir_elimina_el_perfil_elegido(self):
        self._fijar(("Uno", "Dos", "Tres"))
        self._elegir("Dos")
        with mock.patch.object(pagina_mod.confirmar, "preguntar",
                               return_value=True), \
                mock.patch.object(perfiles_obs, "eliminar_perfil") as eliminar:
            self._tecla(wx.WXK_DELETE)
        eliminar.assert_called_once_with(self.pagina._cliente(), "Dos")

    def test_eliminar_con_la_lista_vacia_anuncia_el_vacio_y_no_pregunta(self):
        self.pagina.fijar([], "")
        with mock.patch.object(pagina_mod.confirmar, "preguntar") as preguntar, \
                mock.patch.object(lista_acciones, "anunciar",
                                  self.anuncios.append):
            self._pulsar(self.pagina.btn_eliminar)
        preguntar.assert_not_called()
        self.assertIn(
            _("No hay perfiles en OBS. Usa Nuevo… para crear uno."),
            self.anuncios)

    def test_un_perfil_asignado_avisa_antes_y_deja_el_uso_vacio(self):
        base = tempfile.TemporaryDirectory()
        self.addCleanup(base.cleanup)
        ruta = Path(base.name) / "config.ini"
        ruta.write_text("[transmision]\nperfil_horizontal = Dos\n",
                        encoding="utf-8")
        self.principal._config["perfil_horizontal"] = "Dos"
        self._fijar(("Uno", "Dos", "Tres"))
        self._elegir("Dos")
        with mock.patch.object(pagina_mod.confirmar, "preguntar",
                               return_value=True) as preguntar, \
                mock.patch.object(perfiles_obs, "eliminar_perfil"), \
                mock.patch.object(gui, "RUTA_CONFIG", ruta):
            self.pagina.eliminar()
        self.assertIn("Se usa para transmitir en horizontal",
                      preguntar.call_args[0][1])
        parser = configparser.ConfigParser(interpolation=None)
        parser.read(ruta, encoding="utf-8")
        self.assertEqual(parser.get("transmision", "perfil_horizontal"), "")
        self.assertEqual(self.principal._config["perfil_horizontal"], "")


class TestEditar(BasePagina):

    def _parches(self, avanzado=False, personalizado=True):
        return (
            mock.patch.object(perfiles_obs, "leer_para_editar",
                              return_value=(de_prueba(), avanzado,
                                            personalizado)),
            mock.patch.object(salidas_audio, "salidas",
                              return_value=(("default", "Por defecto"),)),
            mock.patch.object(codificadores_obs, "codificadores_disponibles",
                              return_value=("x264",)),
        )

    def test_lee_los_ajustes_y_guarda_los_del_cuadro(self):
        self._fijar()
        self._elegir("Dos")
        nuevos = de_prueba(bitrate_video=9999)
        _DialogoAjustesFalso.devuelve = nuevos
        _DialogoAjustesFalso.pasar = False
        parches = self._parches(avanzado=True, personalizado=False)
        for parche in parches:
            parche.start()
            self.addCleanup(parche.stop)
        with mock.patch.object(pagina_mod, "DialogoAjustesPerfil",
                               _DialogoAjustesFalso), \
                mock.patch.object(perfiles_obs, "guardar_ajustes") as guardar:
            self.pagina.editar()
        self.assertTrue(_DialogoAjustesFalso.visto["avanzado"])
        self.assertFalse(_DialogoAjustesFalso.visto["personalizado"])
        guardar.assert_called_once_with(self.pagina._cliente(), nuevos, "Dos")
        self.assertIn("Ajustes guardados en el perfil Dos.", self.anuncios)

    def test_pasar_a_sencillo_se_pide_desde_el_cuadro(self):
        self._fijar()
        self._elegir("Dos")
        _DialogoAjustesFalso.devuelve = de_prueba()
        _DialogoAjustesFalso.pasar = True
        parches = self._parches(avanzado=True)
        for parche in parches:
            parche.start()
            self.addCleanup(parche.stop)
        with mock.patch.object(pagina_mod, "DialogoAjustesPerfil",
                               _DialogoAjustesFalso), \
                mock.patch.object(perfiles_obs, "pasar_a_sencillo") as pasar:
            self.pagina.editar()
        pasar.assert_called_once_with(self.pagina._cliente(), "Dos")
        self.assertIn("Perfil Dos en modo Sencillo.", self.anuncios)


class TestError(BasePagina):

    def test_un_error_se_anuncia_y_no_se_anuncia_el_resultado(self):
        self._fijar()
        self._elegir("Dos")
        with mock.patch.object(
                perfiles_obs, "cambiar_perfil",
                side_effect=obs_cliente.ObsError(
                    _(perfiles_obs.MENSAJE_SALIDA_ACTIVA))) as cambiar:
            self.pagina.usar()
        cambiar.assert_called_once()
        self.assertEqual(self.operaciones.fallos,
                         [_(perfiles_obs.MENSAJE_SALIDA_ACTIVA)])
        self.assertEqual(self.anuncios,
                         [_(perfiles_obs.MENSAJE_SALIDA_ACTIVA)])


if __name__ == "__main__":
    unittest.main()
