# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pseudotraducción de la página Inteligencia artificial de Preferencias.

Abre ventanas.
Construye el diálogo de Preferencias con la pseudotraducción y exige que
la página no deje ningún texto visible sin envolver.
"""

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import wx

from guyrapu.ai import catalogo
from guyrapu.ai import opciones_ia
from guyrapu.ai import protocolos
from guyrapu.ui import confirmar, gui, gui_preferencias
from guyrapu.ui import preferencias_ia
from guyrapu.ui import preferencias_ia_clave
from guyrapu.voice import motores
from tests.pseudo_prueba import con_pseudo, textos_sin_marcar
from tests.rutas_temporales import redirigir_rutas
from tests.ventanas_prueba import app_de_prueba, destruir


class TestPseudoIA(unittest.TestCase):
    def setUp(self):
        self.app = app_de_prueba()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        parche = redirigir_rutas(Path(self.tmp.name))
        parche.__enter__()
        self.addCleanup(parche.__exit__, None, None, None)
        # Nunca el Administrador de credenciales real.
        sin_clave = mock.patch.object(
            preferencias_ia_clave.claves, "leer", return_value="")
        sin_clave.start()
        self.addCleanup(sin_clave.stop)
        # Catálogo vacío: la lista muestra el aviso de lista vacía.
        catalogo_vacio = mock.patch.object(
            preferencias_ia.catalogo, "cargar",
            return_value={"version": catalogo.VERSION, "fecha": None,
                          "proveedores": {}})
        catalogo_vacio.start()
        self.addCleanup(catalogo_vacio.stop)

    def _dialogo(self):
        with mock.patch.object(motores, "listar_voces",
                               return_value=["Voz de prueba"]):
            dialogo = gui_preferencias.PreferenciasDialog(None, {})
        self.addCleanup(destruir, dialogo)
        return dialogo

    def test_no_queda_ningun_texto_visible_sin_envolver(self):
        with con_pseudo():
            dialogo = self._dialogo()
            pagina = next(p for p in dialogo._paginas()
                          if p.GetName() == "PagIA")
            sin_marcar = textos_sin_marcar(pagina)

        self.assertEqual([], sin_marcar)

    def test_nombres_de_proveedores_marcados(self):
        with con_pseudo():
            dialogo = self._dialogo()
            nombres = dialogo.pagina_ia.cho_ia_proveedor.GetStrings()

        self.assertEqual(len(nombres), 7)
        for nombre in nombres:
            self.assertTrue(nombre.startswith("[¡"), nombre)

    def test_restaurar_marca_la_instruccion(self):
        with con_pseudo():
            dialogo = self._dialogo()
            dialogo.pagina_ia._on_ia_restaurar(mock.Mock())
            valor = dialogo.pagina_ia.txt_ia_pregunta.GetValue()
        self.assertTrue(valor.startswith("[¡"), valor)


class TestDisenoIA(unittest.TestCase):
    """Guardar y Probar comparten fila; Actualizar va junto al Modelo.

    Abren ventanas.
    """

    def setUp(self):
        self.app = app_de_prueba()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        parche = redirigir_rutas(Path(self.tmp.name))
        parche.__enter__()
        self.addCleanup(parche.__exit__, None, None, None)
        sin_clave = mock.patch.object(
            preferencias_ia_clave.claves, "leer", return_value="")
        sin_clave.start()
        self.addCleanup(sin_clave.stop)
        catalogo_vacio = mock.patch.object(
            preferencias_ia.catalogo, "cargar",
            return_value={"version": catalogo.VERSION, "fecha": None,
                          "proveedores": {}})
        catalogo_vacio.start()
        self.addCleanup(catalogo_vacio.stop)

    def _dialogo(self):
        with mock.patch.object(motores, "listar_voces",
                               return_value=["Voz de prueba"]):
            dialogo = gui_preferencias.PreferenciasDialog(None, {})
        self.addCleanup(destruir, dialogo)
        return dialogo

    def test_guardar_y_probar_comparten_una_fila_partible(self):
        dialogo = self._dialogo()
        guardar = dialogo.pagina_ia.ia_clave.btn_guardar
        probar = dialogo.pagina_ia.btn_ia_probar_clave
        fila = guardar.GetContainingSizer()
        self.assertIsNotNone(fila)
        self.assertIs(probar.GetContainingSizer(), fila)
        self.assertIsInstance(fila, gui.wx.WrapSizer)
        self.assertEqual([elemento.GetWindow()
                          for elemento in fila.GetChildren()],
                         [guardar, probar])

    def test_actualizar_comparte_la_fila_con_el_modelo(self):
        dialogo = self._dialogo()
        modelo = dialogo.pagina_ia.cho_ia_modelo
        actualizar = dialogo.pagina_ia.btn_ia_actualizar
        fila = modelo.GetContainingSizer()
        self.assertIsNotNone(fila)
        self.assertIs(actualizar.GetContainingSizer(), fila)
        ventanas = [elemento.GetWindow()
                     for elemento in fila.GetChildren()]
        self.assertLess(ventanas.index(modelo),
                        ventanas.index(actualizar))


class TestClaveConFormatoAjeno(unittest.TestCase):
    """Guardar y Probar con una clave de comienzo, largo o carácter ajenos.

    Abre ventanas.
    """

    CLAVE_AJENA = "xx" + "a" * 30
    CLAVE_CON_ESPACIO = "AIzaSyAbc def1234567890"

    def setUp(self):
        self.app = app_de_prueba()
        self.al_cambiar = mock.Mock()
        self.proveedor = SimpleNamespace(
            id="gemini", nombre="Gemini", prefijo_clave=("AIza", "AQ."))
        parche = mock.patch.object(
            preferencias_ia_clave.claves, "leer", return_value="")
        parche.start()
        self.addCleanup(parche.stop)
        marco = wx.Frame(None)
        self.addCleanup(destruir, marco)
        panel = wx.Panel(marco)
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.seccion = preferencias_ia_clave.SeccionClaveIA(
            lambda: self.proveedor, self.al_cambiar)
        self.seccion.construir(panel, sizer)
        panel.SetSizer(sizer)

    def _parches(self, respuesta):
        preguntar = mock.patch.object(
            preferencias_ia_clave.confirmar, "preguntar",
            return_value=respuesta)
        guardar = mock.patch.object(
            preferencias_ia_clave.claves, "guardar")
        avisar = mock.patch.object(preferencias_ia_clave, "avisar")
        anunciar = mock.patch.object(preferencias_ia_clave, "anunciar")
        sonar = mock.patch.object(preferencias_ia_clave._snd, "reproducir")
        foco = mock.patch.object(self.seccion.txt_clave, "SetFocus")
        return preguntar, guardar, avisar, anunciar, sonar, foco

    def _guardar(self, clave, respuesta):
        self.seccion.txt_clave.SetValue(clave)
        parches = self._parches(respuesta)
        with parches[0] as preguntar, parches[1] as guardar, \
                parches[2] as avisar, parches[3] as anunciar, \
                parches[4] as sonar, parches[5] as foco:
            self.seccion._on_guardar(None)
        return preguntar, guardar, avisar, anunciar, sonar, foco

    def _probar(self, clave, respuesta):
        self.seccion.txt_clave.SetValue(clave)
        parches = self._parches(respuesta)
        with parches[0] as preguntar, parches[1] as _guardar, \
                parches[2] as _avisar, parches[3] as anunciar, \
                parches[4] as sonar, parches[5] as foco:
            resultado = self.seccion.revisar_para_probar(clave)
        return resultado, preguntar, anunciar, sonar, foco

    def test_usar_de_todos_modos_guarda_y_anuncia(self):
        _p, guardar, _a, anunciar, sonar, _f = self._guardar(
            self.CLAVE_AJENA, True)
        guardar.assert_called_once_with("gemini", self.CLAVE_AJENA)
        anunciar.assert_called_once_with(opciones_ia.TEXTO_CLAVE_GUARDADA)
        self.al_cambiar.assert_called_once_with()
        sonar.assert_called_once_with("ia_error")

    def test_corregir_no_guarda_y_devuelve_el_foco_intacto(self):
        _p, guardar, _a, _an, _s, foco = self._guardar(
            self.CLAVE_AJENA, False)
        guardar.assert_not_called()
        foco.assert_called_once_with()
        self.al_cambiar.assert_not_called()
        self.assertEqual(self.seccion.txt_clave.GetValue(), self.CLAVE_AJENA)

    def test_la_advertencia_trae_el_problema_el_titulo_y_corregir(self):
        preguntar, _g, _a, _an, _s, _f = self._guardar(
            self.CLAVE_AJENA, False)
        problema = opciones_ia.problema_de_clave(
            self.proveedor, self.CLAVE_AJENA)
        argumentos = preguntar.call_args
        self.assertIn(problema, argumentos.args[1])
        self.assertIn("Si el proveedor cambió el formato de sus claves, "
                      "puedes usarla de todos modos.", argumentos.args[1])
        self.assertEqual(argumentos.args[2], "Clave de Gemini")
        self.assertEqual(argumentos.args[3], "&Usar de todos modos")
        self.assertEqual(argumentos.args[4], "&Corregir")
        self.assertIs(argumentos.kwargs["icono"], confirmar.ICON_WARNING)
        self.assertIs(argumentos.kwargs["predeterminado_si"], False)

    def test_probar_afirmativo_sigue_y_negativo_no_prueba(self):
        resultado, preguntar, _an, sonar, foco = self._probar(
            self.CLAVE_AJENA, False)
        self.assertFalse(resultado)
        preguntar.assert_called_once()
        sonar.assert_called_once_with("ia_error")
        foco.assert_called_once_with()
        resultado, preguntar, _an, _s, foco = self._probar(
            self.CLAVE_AJENA, True)
        self.assertTrue(resultado)
        preguntar.assert_called_once()
        foco.assert_not_called()

    def test_guardar_con_espacio_en_el_medio_no_abre_cuadro(self):
        for clave, esperado in (("", opciones_ia.TEXTO_FALTA_CLAVE),
                                (self.CLAVE_CON_ESPACIO,
                                 opciones_ia.TEXTO_CLAVE_CARACTERES)):
            with self.subTest(clave=clave):
                preguntar, guardar, avisar, _an, _s, _f = self._guardar(
                    clave, False)
                preguntar.assert_not_called()
                guardar.assert_not_called()
                avisar.assert_called_once_with(
                    esperado, "ia_error", error=True)

    def test_probar_con_espacio_en_el_medio_no_abre_cuadro(self):
        resultado, preguntar, anunciar, _s, _f = self._probar(
            self.CLAVE_CON_ESPACIO, True)
        self.assertFalse(resultado)
        preguntar.assert_not_called()
        anunciar.assert_called_once_with(opciones_ia.TEXTO_CLAVE_CARACTERES)


class TestModeloElegidoDeLaPagina(unittest.TestCase):
    """La actualización recibe el id que está elegido en la página.

    Abre ventanas.
    """

    def setUp(self):
        self.app = app_de_prueba()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        parche = redirigir_rutas(Path(self.tmp.name))
        parche.__enter__()
        self.addCleanup(parche.__exit__, None, None, None)
        sin_clave = mock.patch.object(
            preferencias_ia_clave.claves, "leer", return_value="")
        sin_clave.start()
        self.addCleanup(sin_clave.stop)
        con_modelos = mock.patch.object(
            preferencias_ia.catalogo, "cargar",
            return_value=self._catalogo())
        con_modelos.start()
        self.addCleanup(con_modelos.stop)

    @staticmethod
    def _catalogo():
        base = "https://generativelanguage.googleapis.com/v1beta"
        return {
            "version": catalogo.VERSION,
            "fecha": "2026-10-21",
            "proveedores": {
                "google": {
                    "nombre": "Google",
                    "modelos": [
                        {"id": "gemini-uno", "nombre": "Gemini Uno",
                         "protocolo": protocolos.GEMINI, "base": base},
                        {"id": "gemini-dos", "nombre": "Gemini Dos",
                         "protocolo": protocolos.GEMINI, "base": base},
                    ],
                },
            },
        }

    def test_recibe_el_id_de_la_lista_y_el_texto_de_otro(self):
        with mock.patch.object(motores, "listar_voces",
                               return_value=["Voz de prueba"]):
            dialogo = gui_preferencias.PreferenciasDialog(None, {})
        self.addCleanup(destruir, dialogo)
        pagina = dialogo.pagina_ia
        self.assertEqual(["gemini-uno", "gemini-dos"],
                         pagina._ia_modelos_ids)
        pagina.cho_ia_modelo.SetSelection(1)
        elegido = pagina.ia_lista._modelo_elegido()
        pagina.txt_ia_otro.ChangeValue("modelo-escrito")
        escrito = pagina.ia_lista._modelo_elegido()
        self.assertEqual("gemini-dos", elegido)
        self.assertEqual("modelo-escrito", escrito)


if __name__ == "__main__":
    unittest.main()
