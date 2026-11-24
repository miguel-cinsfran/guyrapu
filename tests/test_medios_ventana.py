# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Página de medios y su cuadro: lista, acciones, foco y archivos.

Abre ventanas.
"""

import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

import wx

from guyrapu.core import paths
from guyrapu.interaction import (
    ajustes_interaccion, medios, medios_guardados, paquetes)
from guyrapu.ui import medio_cuadro, medios_ventana
from tests.letras_acceso import letras_repetidas
from tests.rutas_temporales import redirigir_rutas
from tests.ventanas_prueba import app_de_prueba, destruir


def _datos(**cambios):
    datos = {
        "nombre": "Risa",
        "descripcion": "Una risa",
        "tipo": "sonido",
        "archivo": "risa.wav",
        "duracion": 3,
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
        self.base = Path(self.tmp.name)
        parche = mock.patch.object(medios_ventana.medios_medicion, "medir")
        self.medir = parche.start()
        self.addCleanup(parche.stop)

    def _origen(self, nombre="origen.wav", contenido=b"AAA"):
        ruta = self.base / "origenes" / nombre
        ruta.parent.mkdir(exist_ok=True)
        ruta.write_bytes(contenido)
        return ruta

    def _panel(self, lista=None):
        if lista is not None:
            medios_guardados.guardar(paths.medios(), lista)
            paths.carpeta_medios().mkdir(parents=True, exist_ok=True)
            for medio in lista:
                (paths.carpeta_medios() / medio["archivo"]).write_bytes(b"AAA")
        marco = wx.Frame(None)
        self.addCleanup(destruir, marco)
        panel = medios_ventana.PanelMedios(marco)
        self.addCleanup(destruir, panel)
        return panel

    def _cuadro(self, datos=None, editar=False):
        cuadro = medio_cuadro.DialogoMedio(None, datos or {}, editar)
        self.addCleanup(destruir, cuadro)
        return cuadro

    def _mostrada(self, ventana):
        ventana.Show()
        self.addCleanup(ventana.Hide)

    def _en_disco(self):
        return medios_guardados.cargar(paths.medios())


class TestPagina(BaseVentana):

    def test_la_lista_tiene_su_nombre_y_la_linea_vacia(self):
        panel = self._panel([])
        self.assertEqual(panel.lista.GetName(), "Medios guardados")
        self.assertEqual(panel.lista.GetCount(), 1)
        self.assertEqual(panel.lista.GetString(0),
                         "No hay medios. Aquí aparecen las imágenes, los GIF, "
                         "los vídeos y los sonidos de la carpeta Medios, junto "
                          "a la aplicación. Los comandos y las alertas "
                         "los muestran o los hacen sonar en el vídeo. Copia "
                         "archivos en esa carpeta o usa Agregar.")

    def test_la_fila_dice_nombre_tipo_y_duracion(self):
        panel = self._panel([_datos()])
        self.assertEqual(panel.lista.GetString(0),
                         "Risa, sonido, 3 segundos")

    def test_las_acciones_son_las_de_comandos_sin_renombrar_ni_pausar(self):
        panel = self._panel([])
        self.assertEqual([(accion.clave, accion.tecla)
                          for accion in panel._acciones], [
            ("agregar", None), ("editar", "intro"), ("duplicar", "ctrl+d"),
            ("escuchar", None), ("eliminar", "suprimir"), ("exportar", None),
            ("importar", None)])
        sin_elemento = {accion.clave for accion in panel._acciones
                        if not accion.necesita_elemento}
        self.assertEqual(sin_elemento, {"agregar", "exportar", "importar"})

    def test_agregar_copia_guarda_y_deja_el_foco_en_el_nuevo(self):
        panel = self._panel([])
        self._mostrada(panel.GetParent())
        origen = self._origen()
        capturado = {}

        def abrir_falso(_padre, datos, editar=False, ruta=None):
            capturado["ruta"] = ruta
            return {**datos, "nombre": "Risa", "descripcion": "Una risa"}

        with mock.patch.object(panel, "_elegir_archivo",
                               return_value=str(origen)), \
                mock.patch.object(medios_ventana.medios_medicion, "duracion_de",
                                  return_value=20), \
                mock.patch.object(medios_ventana.medio_cuadro, "abrir",
                                  side_effect=abrir_falso), \
                mock.patch.object(medios_ventana, "anunciar") as decir:
            panel._agregar()
        self.assertEqual(Path(capturado["ruta"]), origen)
        guardados = self._en_disco()
        self.assertEqual(guardados[0]["nombre"], "Risa")
        self.assertEqual(guardados[0]["duracion"], 20)
        self.assertTrue(
            (paths.carpeta_medios() / guardados[0]["archivo"]).is_file())
        self.assertEqual(panel.lista.GetSelection(), 0)
        self.assertIs(wx.Window.FindFocus(), panel.lista)
        decir.assert_called_once_with("Medio agregado")

    def test_agregar_un_sonido_lo_manda_a_medir_y_guarda_su_ganancia(self):
        panel = self._panel([])
        origen = self._origen()

        def abrir_falso(_padre, datos, editar=False, ruta=None):
            return {**datos, "nombre": "Risa"}

        with mock.patch.object(panel, "_elegir_archivo",
                               return_value=str(origen)), \
                mock.patch.object(medios_ventana.medios_medicion, "duracion_de",
                                  return_value=3), \
                mock.patch.object(medios_ventana.medio_cuadro, "abrir",
                                  side_effect=abrir_falso), \
                mock.patch.object(medios_ventana, "anunciar"):
            panel._agregar()
        self.assertEqual(self.medir.call_count, 1)
        ruta, al_terminar = self.medir.call_args.args
        guardados = self._en_disco()
        self.assertEqual(Path(ruta),
                         paths.carpeta_medios() / guardados[0]["archivo"])
        self.assertIsNone(guardados[0]["ganancia_db"])
        al_terminar(-6.5)
        self.assertEqual(self._en_disco()[0]["ganancia_db"], -6.5)

    def test_importar_un_sonido_sin_ganancia_lo_manda_a_medir(self):
        origen = self._origen("risa.wav", b"BBB")
        paquete = self.base / "medios.zip"
        paquetes.exportar(paquete, "medios", [_datos()], (origen,))
        panel = self._panel([])
        with mock.patch.object(panel, "_pedir_ruta",
                               return_value=str(paquete)), \
                mock.patch.object(medios_ventana, "anunciar"):
            panel._importar()
        self.assertEqual(self.medir.call_count, 1)
        ruta, al_terminar = self.medir.call_args.args
        self.assertEqual(
            Path(ruta),
            paths.carpeta_medios() / self._en_disco()[0]["archivo"])
        al_terminar(-6.5)
        self.assertEqual(self._en_disco()[0]["ganancia_db"], -6.5)

    def test_importar_un_sonido_con_ganancia_no_lo_vuelve_a_medir(self):
        origen = self._origen("risa.wav", b"BBB")
        paquete = self.base / "medios.zip"
        paquetes.exportar(paquete, "medios",
                          [_datos(ganancia_db=-6.5)], (origen,))
        panel = self._panel([])
        with mock.patch.object(panel, "_pedir_ruta",
                               return_value=str(paquete)), \
                mock.patch.object(medios_ventana, "anunciar"):
            panel._importar()
        self.medir.assert_not_called()
        self.assertEqual(self._en_disco()[0]["ganancia_db"], -6.5)

    def test_editar_guarda_y_no_cambia_el_archivo(self):
        panel = self._panel([_datos()])
        self._mostrada(panel.GetParent())
        capturado = {}

        def abrir_falso(_padre, datos, editar=False, ruta=None):
            capturado["ruta"] = ruta
            return {**datos, "descripcion": "Otra risa"}

        with mock.patch.object(medios_ventana.medio_cuadro, "abrir",
                               side_effect=abrir_falso), \
                mock.patch.object(medios_ventana, "anunciar") as decir:
            panel._editar()
        self.assertEqual(capturado["ruta"],
                         paths.carpeta_medios() / "risa.wav")
        guardados = self._en_disco()
        self.assertEqual(guardados[0]["archivo"], "risa.wav")
        self.assertEqual(guardados[0]["descripcion"], "Otra risa")
        self.assertIs(wx.Window.FindFocus(), panel.lista)
        decir.assert_called_once_with("Medio guardado")

    def test_escuchar_dice_nombre_y_descripcion_y_reproduce(self):
        panel = self._panel([_datos()])
        panel._escucha = mock.Mock()
        panel._escucha.sonando.return_value = False
        panel._escucha.reproducir.return_value = True
        with mock.patch.object(medios_ventana, "anunciar") as decir:
            panel._escuchar()
        decir.assert_called_once_with("Risa. Una risa")
        panel._escucha.reproducir.assert_called_once_with(
            paths.carpeta_medios() / "risa.wav", 0.0)

    def test_escuchar_suma_la_igualacion_el_volumen_general_y_el_propio(self):
        ajustes_interaccion.guardar_volumen(paths.interaccion(), 50)
        panel = self._panel([_datos(ganancia_db=-6.0, volumen=50)])
        panel._escucha = mock.Mock()
        panel._escucha.sonando.return_value = False
        panel._escucha.reproducir.return_value = True
        with mock.patch.object(medios_ventana, "anunciar"):
            panel._escuchar()
        self.assertAlmostEqual(
            panel._escucha.reproducir.call_args.args[1], -18.0412, places=4)

    def test_escuchar_otra_vez_detiene(self):
        panel = self._panel([_datos()])
        panel._escucha = mock.Mock()
        panel._escucha.sonando.return_value = True
        with mock.patch.object(medios_ventana, "anunciar") as decir:
            panel._escuchar()
        panel._escucha.detener.assert_called_once_with()
        decir.assert_not_called()

    def test_eliminar_pide_confirmacion_con_no_y_deja_el_siguiente(self):
        panel = self._panel([
            _datos(nombre="A", archivo="a.wav"),
            _datos(nombre="B", archivo="b.wav")])
        self._mostrada(panel.GetParent())
        panel.lista.SetSelection(1)
        with mock.patch.object(medios_ventana.confirmar, "preguntar",
                               return_value=True) as preguntar, \
                mock.patch.object(medios_ventana, "anunciar") as decir:
            panel._eliminar()
        self.assertFalse(preguntar.call_args.kwargs["predeterminado_si"])
        self.assertEqual(
            preguntar.call_args.args[1],
            "¿Quieres eliminar el medio «B»? También se elimina su archivo "
            "de la carpeta Medios.")
        self.assertFalse((paths.carpeta_medios() / "b.wav").exists())
        self.assertEqual([medio["nombre"] for medio in self._en_disco()],
                         ["A"])
        self.assertEqual(panel.lista.GetSelection(), 0)
        self.assertIs(wx.Window.FindFocus(), panel.lista)
        decir.assert_called_once_with("Medio eliminado")

    def test_exportar_lleva_los_archivos_dentro_del_paquete(self):
        panel = self._panel([_datos()])
        destino = self.base / "medios.zip"
        with mock.patch.object(panel, "_pedir_ruta", return_value=str(destino)):
            panel._exportar()
        leido = paquetes.leer(destino, "medios",
                              extensiones=medios.EXTENSIONES)
        self.assertEqual(("risa.wav",), leido.archivos)
        self.assertEqual("Risa", leido.elementos[0]["nombre"])

    def test_importar_copia_los_archivos_a_la_carpeta(self):
        origen = self._origen("risa.wav", b"BBB")
        elemento = _datos()
        paquete = self.base / "medios.zip"
        paquetes.exportar(paquete, "medios", [elemento], (origen,))
        panel = self._panel([])
        with mock.patch.object(panel, "_pedir_ruta",
                               return_value=str(paquete)), \
                mock.patch.object(medios_ventana, "anunciar"):
            panel._importar()
        guardados = self._en_disco()
        self.assertEqual(guardados[0]["nombre"], "Risa")
        ruta = paths.carpeta_medios() / guardados[0]["archivo"]
        self.assertEqual(ruta.read_bytes(), b"BBB")
        self.assertEqual(panel.lista.GetSelection(), 0)


class TestCarpeta(BaseVentana):
    """La carpeta es la verdad: se lee al mostrar y al activar la ventana."""

    def _activar(self, panel):
        evento = wx.ActivateEvent(wx.wxEVT_ACTIVATE, True)
        panel.GetTopLevelParent().GetEventHandler().ProcessEvent(evento)

    def _esperar(self, condicion):
        for _ in range(200):
            wx.Yield()
            if condicion():
                return True
            time.sleep(0.01)
        return False

    def _archivo(self, nombre):
        destino = paths.carpeta_medios() / nombre
        destino.write_bytes(b"AAA")
        return destino

    def test_copiar_y_borrar_un_archivo_se_ve_al_activar(self):
        panel = self._panel([])
        self._mostrada(panel.GetParent())
        archivo = self._archivo("risa.wav")
        with mock.patch.object(medios_ventana.medios_medicion, "duracion_de", return_value=0):
            self._activar(panel)
        self.assertEqual(panel.lista.GetCount(), 1)
        self.assertIn("risa", panel.lista.GetString(0))
        guardados = self._en_disco()
        self.assertEqual([medio["nombre"] for medio in guardados], ["risa"])
        self.assertEqual(guardados[0]["archivo"], "risa.wav")
        archivo.unlink()
        self._activar(panel)
        self.assertIn("No hay medios.", panel.lista.GetString(0))
        self.assertEqual(self._en_disco(), [])

    def test_la_activacion_conserva_el_elemento_elegido(self):
        panel = self._panel([_datos(nombre="A", archivo="a.wav"),
                             _datos(nombre="B", archivo="b.wav")])
        panel.lista.SetSelection(1)
        self._archivo("c.wav")
        with mock.patch.object(medios_ventana.medios_medicion, "duracion_de", return_value=0):
            self._activar(panel)
        self.assertEqual(panel.lista.GetSelection(), 1)
        self.assertEqual([panel.lista.GetString(i)
                          for i in range(panel.lista.GetCount())][1],
                         "B, sonido, 3 segundos")

    def test_un_medio_nuevo_se_mide_en_segundo_plano_sin_anunciar(self):
        panel = self._panel([])
        self._archivo("risa.wav")
        inmediato = lambda funcion, *args: funcion(*args)
        with mock.patch.object(medios_ventana.medios_medicion, "duracion_de",
                               return_value=7) as duracion, \
             mock.patch.object(medios_ventana, "anunciar") as decir, \
             mock.patch.object(medios_ventana.wx, "CallAfter",
                               side_effect=inmediato):
            self._activar(panel)
            medida = self._esperar(lambda: self.medir.call_count == 1)
        self.assertTrue(medida)
        self.assertEqual(duracion.call_count, 1)
        self.assertEqual(self.medir.call_args.args[0],
                         paths.carpeta_medios() / "risa.wav")
        self.medir.call_args.args[1](None)
        guardados = self._en_disco()
        self.assertEqual(guardados[0]["duracion"], 7)
        self.assertIsNone(guardados[0]["ganancia_db"])
        decir.assert_not_called()

    def test_el_boton_abrir_carpeta_va_al_final_y_la_abre(self):
        panel = self._panel([])
        self.assertEqual(panel.btn_abrir_carpeta.GetLabel(), "&Abrir carpeta")
        self.assertEqual(panel.btn_abrir_carpeta.GetName(), "Abrir carpeta")
        self.assertIs([hijo for hijo in panel.GetChildren()
                       if isinstance(hijo, wx.Button)][-1],
                      panel.btn_abrir_carpeta)
        with mock.patch.object(medios_ventana.os, "startfile") as abrir:
            evento = wx.CommandEvent(wx.wxEVT_BUTTON,
                                     panel.btn_abrir_carpeta.GetId())
            panel.btn_abrir_carpeta.GetEventHandler().ProcessEvent(evento)
        abrir.assert_called_once_with(str(paths.carpeta_medios()))
        self.assertTrue(paths.carpeta_medios().is_dir())


class TestVolumen(BaseVentana):

    def test_el_control_va_entre_la_lista_y_los_botones_y_nace_en_cien(self):
        panel = self._panel([])
        self.assertIsInstance(panel.sp_volumen, wx.Slider)
        self.assertEqual(panel.sp_volumen.GetName(),
                         "Volumen de los medios en el vídeo")
        self.assertEqual((panel.sp_volumen.GetMin(),
                          panel.sp_volumen.GetMax(),
                          panel.sp_volumen.GetValue()), (0, 100, 100))
        self.assertEqual(panel.sp_volumen.GetLineSize(), 1)
        hijos = panel.GetChildren()
        primer_boton = next(hijo for hijo in hijos
                            if isinstance(hijo, wx.Button))
        self.assertLess(hijos.index(panel.lista),
                        hijos.index(panel.sp_volumen))
        self.assertLess(hijos.index(panel.sp_volumen),
                        hijos.index(primer_boton))
        etiquetas = [hijo.GetLabel() for hijo in hijos
                     if isinstance(hijo, wx.StaticText)]
        self.assertIn("&Volumen de los medios en el vídeo:", etiquetas)
        self.assertEqual(letras_repetidas(panel), {})

    def test_cambiarlo_lo_guarda_y_se_conserva_al_reabrir(self):
        panel = self._panel([])
        panel.sp_volumen.SetValue(40)
        evento = wx.CommandEvent(wx.EVT_SLIDER.typeId,
                                 panel.sp_volumen.GetId())
        panel.sp_volumen.GetEventHandler().ProcessEvent(evento)
        self.assertEqual(
            ajustes_interaccion.cargar_volumen(paths.interaccion()), 40)
        otro = self._panel([])
        self.assertEqual(otro.sp_volumen.GetValue(), 40)


class TestCuadro(BaseVentana):

    def test_tiene_los_campos_y_el_nombre_de_fabrica(self):
        cuadro = self._cuadro(_datos())
        self.assertEqual(cuadro.txt_nombre.GetValue(), "Risa")
        self.assertEqual(cuadro.txt_descripcion.GetValue(), "Una risa")
        self.assertEqual(cuadro.txt_tipo.GetValue(), "sonido")
        self.assertEqual(cuadro.txt_duracion.GetValue(), "3 segundos")
        self.assertTrue(cuadro.txt_tipo.GetWindowStyle() & wx.TE_READONLY)
        self.assertTrue(cuadro.txt_duracion.GetWindowStyle() & wx.TE_READONLY)

    def test_una_imagen_no_lleva_duracion(self):
        cuadro = self._cuadro(_datos(tipo="imagen", archivo="logo.png",
                                     duracion=0))
        self.assertEqual(cuadro.txt_tipo.GetValue(), "imagen")
        self.assertEqual(cuadro.txt_duracion.GetValue(), "No se aplica")
        self.assertIsNone(cuadro.aviso)

    def test_las_letras_de_acceso_no_se_repiten_en_el_cuadro(self):
        self.assertEqual(letras_repetidas(self._cuadro(_datos())), {})

    def test_el_boton_describir_va_despues_de_la_descripcion_y_no_se_apaga(self):
        for editar in (False, True):
            with self.subTest(editar=editar):
                cuadro = self._cuadro(
                    _datos(tipo="imagen", archivo="logo.png", duracion=0),
                    editar=editar)
                self.assertEqual(cuadro.btn_describir.GetLabel(),
                                 "Describir &imagen")
                self.assertEqual(cuadro.btn_describir.GetName(),
                                 "Describir imagen")
                self.assertTrue(cuadro.btn_describir.IsEnabled())
                hermanos = cuadro.txt_descripcion.GetParent().GetChildren()
                posicion = hermanos.index(cuadro.txt_descripcion)
                self.assertIs(hermanos[posicion + 1], cuadro.btn_describir)
                self.assertLess(hermanos.index(cuadro.btn_describir),
                                hermanos.index(cuadro.txt_tipo))

    def test_el_foco_nace_en_nombre(self):
        cuadro = self._cuadro(_datos())
        self._mostrada(cuadro)
        self.assertIs(wx.Window.FindFocus(), cuadro.txt_nombre)

    def test_un_sonido_de_veinte_segundos_muestra_el_aviso(self):
        cuadro = self._cuadro(_datos(duracion=20))
        self.assertIsNotNone(cuadro.aviso)
        self.assertEqual(
            cuadro.aviso.GetLabel(),
            "Dura más de 15 segundos: al activarlo se detiene a los 15 segundos.")

    def test_quince_segundos_no_muestra_el_aviso(self):
        self.assertIsNone(self._cuadro(_datos(duracion=15)).aviso)

    def test_escape_cierra_el_cuadro(self):
        evento = mock.Mock()
        evento.GetKeyCode.return_value = wx.WXK_ESCAPE
        cuadro = self._cuadro(_datos())
        with mock.patch.object(cuadro, "EndModal") as cerrar:
            cuadro._al_tecla(evento)
        cerrar.assert_called_once_with(wx.ID_CANCEL)


if __name__ == "__main__":
    unittest.main()
