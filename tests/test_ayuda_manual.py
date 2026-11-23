# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""F1 abre el manual en la sección de la ventana."""

import contextlib
import tempfile
import unittest
from pathlib import Path
from unittest import mock

try:
    import wx
    _HAY_WX = True
except Exception:
    _HAY_WX = False

from guyrapu.core import paths
from guyrapu.ui import ayuda_manual, gui_menu
from guyrapu.ui import gui_elegir_destino as elegir
from tests.ventanas_prueba import app_de_prueba, destruir

RAIZ = Path(__file__).resolve().parent.parent


class TestAnclas(unittest.TestCase):

    def test_p2_las_anclas_van_escritas_en_los_dos_manuales(self):
        for idioma in ("es", "en"):
            manual = (RAIZ / "docs" / idioma / "MANUAL.md").read_text(
                encoding="utf-8")
            lineas = manual.splitlines()
            for ancla in ayuda_manual.ANCLAS.values():
                with self.subTest(idioma=idioma, ancla=ancla):
                    self.assertTrue(
                        any(linea.startswith("#")
                            and f'<a id="{ancla}"></a>' in linea
                            for linea in lineas), ancla)

    def test_p4_cada_ancla_del_registro_existe_en_los_dos_html(self):
        for idioma in ("es", "en"):
            manual = (RAIZ / "docs" / idioma / "MANUAL.html").read_text(
                encoding="utf-8")
            lineas = manual.splitlines()
            for clave, ancla in ayuda_manual.ANCLAS.items():
                with self.subTest(ventana=clave, idioma=idioma):
                    self.assertTrue(
                        any(linea.startswith(("<h2", "<h3"))
                            and f'<a id="{ancla}"></a>' in linea
                            for linea in lineas), ancla)

    def test_p4_todas_las_paginas_de_interaccion_estan_en_el_registro(self):
        from guyrapu.ui import interaccion_ventana
        for clave, _etiqueta in interaccion_ventana.PAGINAS:
            with self.subTest(pagina=clave):
                self.assertIn(clave, ayuda_manual.ANCLAS)
        self.assertIn("ensayo", ayuda_manual.ANCLAS)

    def test_p5_las_ventanas_fuera_de_la_lista_no_tienen_ancla(self):
        for clave in ("encuadre", "mensajes_automaticos"):
            self.assertNotIn(clave, ayuda_manual.ANCLAS)


class TestAbrirDocumento(unittest.TestCase):

    def _instalacion(self, tmp):
        instalacion = Path(tmp) / "app"
        manual = instalacion / "docs" / "es" / "MANUAL.html"
        manual.parent.mkdir(parents=True)
        manual.write_text(
            '<h2 id="panel-obs">Panel de OBS</h2>', encoding="utf-8")
        return instalacion, manual

    def test_la_pagina_de_redireccion_lleva_la_ruta_y_el_ancla(self):
        with tempfile.TemporaryDirectory() as tmp:
            instalacion, manual = self._instalacion(tmp)
            pagina = Path(tmp) / "redirige.html"
            with mock.patch.object(paths, "carpeta_instalacion",
                                   return_value=instalacion), \
                    mock.patch.object(gui_menu, "idioma_actual",
                                      return_value="es"), \
                    mock.patch.object(paths, "pagina_redireccion",
                                      return_value=pagina), \
                    mock.patch.object(gui_menu.confirmar, "avisar") as cuadro, \
                    mock.patch.object(gui_menu.os, "startfile") as abrir:
                gui_menu.abrir_documento_paquete(
                    None, "MANUAL", "Manual de uso", "panel-obs")
            abrir.assert_called_once_with(str(pagina))
            cuadro.assert_not_called()
            texto = pagina.read_text(encoding="utf-8")
            self.assertIn(manual.as_uri(), texto)
            self.assertIn("#panel-obs", texto)

    def test_p5_sin_ancla_abre_el_manual_al_principio(self):
        with tempfile.TemporaryDirectory() as tmp:
            instalacion, manual = self._instalacion(tmp)
            with mock.patch.object(paths, "carpeta_instalacion",
                                   return_value=instalacion), \
                    mock.patch.object(gui_menu, "idioma_actual",
                                      return_value="es"), \
                    mock.patch.object(paths, "pagina_redireccion") as pagina, \
                    mock.patch.object(gui_menu.os, "startfile") as abrir:
                gui_menu.abrir_documento_paquete(
                    None, "MANUAL", "Manual de uso")
            abrir.assert_called_once_with(str(manual))
            pagina.assert_not_called()


@unittest.skipUnless(_HAY_WX, "wxPython no está instalado")
class TestF1EnUnaVentana(unittest.TestCase):
    """El cableado de una ventana real: F1 abre el manual en su sección."""

    def setUp(self):
        self.app = app_de_prueba()
        parche = mock.patch.object(
            elegir.ganchos, "cargar_perfiles", return_value=[])
        parche.start()
        self.addCleanup(parche.stop)

    def _dialogo(self):
        dialogo = elegir.DialogoElegirDestino(None, "YouTube", "")
        self.addCleanup(destruir, dialogo)
        return dialogo

    def _abrir_con(self, dialogo, pagina):
        evento = mock.Mock()
        evento.GetKeyCode.return_value = wx.WXK_F1
        with mock.patch.object(paths, "pagina_redireccion",
                               return_value=pagina), \
                mock.patch.object(gui_menu, "idioma_actual",
                                  return_value="es"), \
                mock.patch.object(gui_menu.confirmar, "avisar") as cuadro, \
                mock.patch.object(gui_menu.os, "startfile") as abrir:
            dialogo._al_tecla(evento)
        return abrir, cuadro

    def test_p1_f1_abre_el_manual_en_la_seccion_de_la_ventana(self):
        with tempfile.TemporaryDirectory() as tmp:
            pagina = Path(tmp) / "redirige.html"
            abrir, cuadro = self._abrir_con(self._dialogo(), pagina)
            abrir.assert_called_once_with(str(pagina))
            cuadro.assert_not_called()
            texto = pagina.read_text(encoding="utf-8")
        self.assertIn("#transmitir", texto)

    def test_p3_el_ancla_sale_del_registro(self):
        with tempfile.TemporaryDirectory() as tmp:
            pagina = Path(tmp) / "redirige.html"
            with mock.patch.dict(
                    ayuda_manual.ANCLAS, {"transmitir": "otra-seccion"}):
                _, cuadro = self._abrir_con(self._dialogo(), pagina)
            cuadro.assert_not_called()
            self.assertIn("#otra-seccion", pagina.read_text(encoding="utf-8"))


@unittest.skipUnless(_HAY_WX, "wxPython no está instalado")
class TestCadaVentana(unittest.TestCase):
    """Cada ventana del registro toma F1 con su clave."""

    def setUp(self):
        self.app = app_de_prueba()
        from guyrapu.core import idioma
        idioma.instalar("es")
        self.addCleanup(idioma._reiniciar)

    def _f1(self, ventana):
        evento = wx.KeyEvent(wx.EVT_CHAR_HOOK.typeId)
        evento.SetKeyCode(wx.WXK_F1)
        ventana.GetEventHandler().ProcessEvent(evento)

    def _panel_obs(self, pila):
        from guyrapu.ui import obs_ventana
        from tests.test_gui_transmision import GestorFalso, PrincipalFalsa
        pila.enter_context(mock.patch.object(
            obs_ventana.OperacionesObs, "en_hilo",
            lambda self, *args, **kwargs: None))
        pila.enter_context(mock.patch.object(
            obs_ventana.obs_lanzador, "asegurar_obs",
            lambda *args, **kwargs: False))
        pila.enter_context(mock.patch.object(
            obs_ventana.wx, "CallAfter", lambda *args, **kwargs: None))
        pila.enter_context(mock.patch.object(obs_ventana, "anunciar",
                                             mock.Mock()))
        ventana = obs_ventana.VentanaObs(
            None, PrincipalFalsa(), gestor=GestorFalso())
        self.addCleanup(destruir, ventana)
        return ventana

    def _restream(self, pila):
        from guyrapu.ui import restream_ventana

        class CuentaFalsa:
            def conectada(self):
                return False

        temporal = tempfile.TemporaryDirectory()
        self.addCleanup(temporal.cleanup)
        pila.enter_context(mock.patch.object(
            restream_ventana.wx, "CallAfter", lambda *args, **kwargs: None))
        ventana = restream_ventana.VentanaRestream(
            None, CuentaFalsa(), lambda: [("1", "Canal")],
            Path(temporal.name) / "perfiles.json", id_canal=lambda: "")
        self.addCleanup(destruir, ventana)
        return ventana

    def _musica(self, pila):
        from guyrapu.ui import musica_ventana
        from tests.test_musica_ventana import ControlFalso
        pila.enter_context(mock.patch.object(
            musica_ventana.wx, "CallAfter", lambda *args, **kwargs: None))
        pila.enter_context(mock.patch.object(musica_ventana, "anunciar",
                                             mock.Mock()))
        ventana = musica_ventana.VentanaMusica(None, ControlFalso())
        self.addCleanup(destruir, ventana)
        return ventana

    def _descargas(self, pila):
        from guyrapu.downloads import descargas
        from guyrapu.ui import (descargas_acciones, descargas_buscador,
                                descargas_listas, gui_descargas)
        pila.enter_context(mock.patch.object(
            descargas_listas.historial_descargas, "cargar",
            return_value=[]))
        pila.enter_context(mock.patch.object(
            descargas_listas.historial_descargas, "guardar"))
        pila.enter_context(mock.patch.object(
            descargas_acciones.historial_descargas, "guardar"))
        pila.enter_context(mock.patch.object(
            descargas_buscador.busquedas_recientes, "cargar",
            return_value=[]))
        pila.enter_context(mock.patch.object(
            descargas_buscador.busquedas_recientes, "guardar"))
        pila.enter_context(mock.patch.object(
            gui_descargas.wx, "CallAfter", lambda *args, **kwargs: None))
        descargas.reiniciar_gestor()
        self.addCleanup(descargas.reiniciar_gestor)
        self.addCleanup(setattr, gui_descargas, "_dialogo_activo", None)
        ventana = gui_descargas.GestorDescargasDialog(None)
        self.addCleanup(destruir, ventana)
        return ventana

    def _historial(self, pila):
        from guyrapu.ui import gui_historial
        temporal = tempfile.TemporaryDirectory()
        self.addCleanup(temporal.cleanup)
        ruta = Path(temporal.name) / "historial.json"
        ruta.write_text("[]", encoding="utf-8")
        pila.enter_context(mock.patch.object(
            gui_historial.wx, "CallAfter", lambda *args, **kwargs: None))
        ventana = gui_historial.HistorialDialog(None, ruta, mock.Mock())
        self.addCleanup(destruir, ventana)
        return ventana

    def _ia(self, pila):
        from guyrapu.ui import ia_ventana
        pila.enter_context(mock.patch.object(
            ia_ventana.diagnostico, "crear_hilo", mock.Mock()))
        pila.enter_context(mock.patch.object(
            ia_ventana.wx, "CallAfter", lambda *args, **kwargs: None))
        ventana = ia_ventana.VentanaIA(None)
        self.addCleanup(destruir, ventana)
        return ventana

    def _preferencias(self, pila):
        from guyrapu.ai import catalogo
        from guyrapu.core import config
        from guyrapu.ui import (gui_preferencias, preferencias_ia,
                                preferencias_ia_clave)
        from guyrapu.voice import motores
        from tests.rutas_temporales import redirigir_rutas
        temporal = tempfile.TemporaryDirectory()
        self.addCleanup(temporal.cleanup)
        ruta = Path(temporal.name)
        (ruta / "config.ini").write_text(config._CONFIG_FALLBACK,
                                         encoding="utf-8")
        pila.enter_context(redirigir_rutas(ruta))
        pila.enter_context(mock.patch.object(
            motores, "listar_voces", return_value=[]))
        pila.enter_context(mock.patch.object(
            preferencias_ia_clave.claves, "leer", return_value=""))
        pila.enter_context(mock.patch.object(
            preferencias_ia.catalogo, "cargar",
            return_value={"version": catalogo.VERSION, "fecha": None,
                          "proveedores": {}}))
        ventana = gui_preferencias.PreferenciasDialog(None, {})
        self.addCleanup(destruir, ventana)
        return ventana

    def _transmitir(self, pila):
        pila.enter_context(mock.patch.object(
            elegir.ganchos, "cargar_perfiles", return_value=[]))
        ventana = elegir.DialogoElegirDestino(None, "YouTube", "")
        self.addCleanup(destruir, ventana)
        return ventana

    def _microfono(self, pila):
        from guyrapu.ui import gui_microfono
        padre = wx.Frame(None)
        padre._config = {"obs_microfono": "Mic/Aux"}
        self.addCleanup(destruir, padre)
        ventana = gui_microfono.MicrofonoObsDialog(
            padre, ("Mic/Aux", "Audio USB"), "Mic/Aux",
            (("Predeterminado", "default"), ("Micrófono (USB)", "{usb}")),
            "{usb}")
        self.addCleanup(destruir, ventana)
        return ventana

    def _voces(self, pila):
        from guyrapu.ui import voces_ventana
        from tests.test_voces_ventana import (
            _Instalados, _catalogo, HiloInmediato)
        pila.enter_context(mock.patch.object(
            voces_ventana.paquetes_instalacion, "instalados",
            _Instalados([])))
        pila.enter_context(mock.patch.object(
            voces_ventana.red, "pedir_texto", return_value=_catalogo()))
        pila.enter_context(mock.patch.object(
            voces_ventana.diagnostico, "crear_hilo", HiloInmediato))
        pila.enter_context(mock.patch.object(
            voces_ventana.wx, "CallAfter",
            lambda funcion, *args, **kwargs: funcion(*args, **kwargs)))
        pila.enter_context(mock.patch.object(
            voces_ventana.voces_disponibles, "idioma_actual",
            return_value="es"))
        pila.enter_context(mock.patch.object(
            voces_ventana.confirmar, "avisar", mock.Mock()))
        pila.enter_context(mock.patch.object(
            voces_ventana._snd, "reproducir", mock.Mock()))
        pila.enter_context(mock.patch.object(voces_ventana, "anunciar",
                                             mock.Mock()))
        ventana = voces_ventana.VentanaVoces(None)
        self.addCleanup(destruir, ventana)
        return ventana

    def _acciones_chat(self):
        from guyrapu.ui import chat_acciones
        from guyrapu.ui.chat_vivo import ControladorChat
        padre = wx.Frame(None)
        self.addCleanup(destruir, padre)
        lista = wx.ListBox(padre)
        chat = ControladorChat(
            lista, 500, activo=lambda: True,
            autor_oculto=lambda autor: False,
            formatear=lambda *args: "", al_superchat=lambda monto: None)
        return padre, chat_acciones.AccionesChat(
            lista, chat, mock.Mock(), {}, lambda: None, padre)

    def _chat_buscar(self, pila):
        from guyrapu.ui import chat_buscar
        padre, acciones = self._acciones_chat()
        ventana = chat_buscar.CuadroBuscarChat(padre, acciones)
        self.addCleanup(destruir, ventana)
        return ventana

    def _participacion(self, pila):
        from guyrapu.ui import chat_participacion
        padre, acciones = self._acciones_chat()
        ventana = chat_participacion.VentanaParticipacion(padre, acciones)
        self.addCleanup(destruir, ventana)
        return ventana

    def test_cada_ventana_abre_su_seccion(self):
        fabricas = [
            ("panel_obs", self._panel_obs),
            ("restream", self._restream),
            ("musica", self._musica),
            ("descargas", self._descargas),
            ("ia", self._ia),
            ("preferencias", self._preferencias),
            ("transmitir", self._transmitir),
            ("microfono", self._microfono),
            ("voces", self._voces),
            ("chat", self._chat_buscar),
            ("chat", self._participacion),
        ]
        for clave, fabrica in fabricas:
            with self.subTest(ventana=clave):
                with mock.patch.object(ayuda_manual, "abrir") as abrir:
                    with contextlib.ExitStack() as pila:
                        ventana = fabrica(pila)
                        self._f1(ventana)
                abrir.assert_called_once_with(ventana, clave)
