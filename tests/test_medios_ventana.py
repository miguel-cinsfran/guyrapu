# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Página de medios y su cuadro: lista, acciones, foco y archivos.

Abre ventanas.
"""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import wx

from guyrapu.core import paths
from guyrapu.interaction import medios, medios_guardados, paquetes
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
                         "No hay medios. Usa Agregar para crear uno.")

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
                mock.patch.object(medios_ventana, "duracion_de",
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
                mock.patch.object(medios_ventana, "duracion_de",
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
            paths.carpeta_medios() / "risa.wav")

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
            "Dura más de 15 segundos: al dispararlo se detiene a los 15")

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
