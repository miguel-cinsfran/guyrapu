# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de la página Lectura y de su guardado.

Abren ventanas. La
primera mata la mutación que devuelve siempre el mismo formato desde
`PaginaLectura.cambios()`; la segunda comprueba el cableado hasta el
archivo, que guardar escribe en `[lectura] formato_prefijo` lo elegido.
"""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from guyrapu.core import config
from guyrapu.translation import idiomas
from guyrapu.ui import gui, gui_preferencias
from guyrapu.ui import preferencias_transmision
from guyrapu.ui.preferencias_lectura import PaginaLectura
from guyrapu.voice import motores
from tests.pseudo_prueba import con_pseudo, textos_sin_marcar
from tests.rutas_temporales import redirigir_rutas
from tests.ventanas_prueba import app_de_prueba, armar_preferencias, destruir


# Valores literales, no leídos de la página: así protegen el orden en vez
# de repetirlo. Van en el mismo orden que las opciones del control.
FORMATOS_ESPERADOS = (
    "nombre_mensaje",
    "mensaje_nombre",
    "solo_mensaje",
    "solo_nombre",
)


class TestCambiosDeLectura(unittest.TestCase):
    def setUp(self):
        self.app = app_de_prueba()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.ruta = Path(self.tmp.name)
        (self.ruta / "config.ini").write_text(config._CONFIG_FALLBACK,
                                              encoding="utf-8")
        parche = redirigir_rutas(self.ruta)
        parche.__enter__()
        self.addCleanup(parche.__exit__, None, None, None)

    def _dialogo(self, configuracion=None):
        with mock.patch.object(motores, "listar_voces",
                               return_value=["Voz de prueba"]):
            dialogo = armar_preferencias(configuracion or {}, "Lectura")
        self.addCleanup(destruir, dialogo)
        return dialogo

    def test_cambios_devuelve_el_formato_elegido(self):
        dialogo = self._dialogo()
        pagina = dialogo.pagina_lectura
        self.assertIsInstance(pagina, PaginaLectura)
        self.assertEqual(pagina.rb_formato.GetCount(), 4)
        for indice, esperado in enumerate(FORMATOS_ESPERADOS):
            with self.subTest(formato=esperado):
                dialogo.rb_formato.SetSelection(indice)
                self.assertEqual(pagina.cambios(),
                                 [("lectura", "formato_prefijo", esperado)])

    def test_entre_traducir_chat_y_que_se_traduce_hay_12_pixeles(self):
        dialogo = self._dialogo()
        panel = dialogo.pagina_lectura.rb_formato.GetParent()
        panel.Layout()
        casilla = dialogo.chk_traducir
        etiqueta = [h for h in panel.GetChildren()
                    if isinstance(h, gui.wx.StaticText)
                    and h.GetLabel() == "Tra&ducir:"][0]
        separacion = etiqueta.GetPosition().y - (
            casilla.GetPosition().y + casilla.GetSize().GetHeight())
        self.assertEqual(separacion, 12)

    def test_la_casilla_de_atajos_nombra_los_atajos_del_chat(self):
        dialogo = self._dialogo()
        self.assertEqual(
            dialogo.pagina_lectura.chk_lectura_atajos_globales.GetLabel(),
            "Usar atajos del chat en cual&quier aplicación")

    def test_guardar_escribe_el_formato_elegido(self):
        dialogo = self._dialogo()
        dialogo.rb_formato.SetSelection(1)
        with mock.patch.object(gui_preferencias._snd, "reproducir"), \
                mock.patch.object(preferencias_transmision, "anunciar"), \
                mock.patch.object(dialogo, "EndModal"):
            dialogo._on_guardar(None)
        self.assertEqual(dialogo._config.get("formato_prefijo"),
                         "mensaje_nombre")
        parser = config._mk_parser()
        parser.read(self.ruta / "config.ini", encoding="utf-8")
        self.assertEqual(parser.get("lectura", "formato_prefijo"),
                         "mensaje_nombre")

    def test_no_queda_ningun_texto_visible_sin_envolver(self):
        with con_pseudo():
            dialogo = self._dialogo()
            pagina = dialogo.rb_formato.GetParent()
            nombres_idiomas = tuple(nombre for codigo, nombre
                                    in idiomas.opciones()
                                    if codigo != "interfaz")
            sin_marcar = textos_sin_marcar(
                pagina, propios=("YouTube", "TikTok") + nombres_idiomas)

        self.assertEqual([], sin_marcar)


class TestDisenoFormato(unittest.TestCase):
    """El grupo de formato lleva su título en el recuadro, sin etiqueta suelta.

    Abren ventanas.
    """

    def setUp(self):
        self.app = app_de_prueba()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.ruta = Path(self.tmp.name)
        (self.ruta / "config.ini").write_text(config._CONFIG_FALLBACK,
                                              encoding="utf-8")
        parche = redirigir_rutas(self.ruta)
        parche.__enter__()
        self.addCleanup(parche.__exit__, None, None, None)

    def _dialogo(self, configuracion=None):
        with mock.patch.object(motores, "listar_voces",
                               return_value=["Voz de prueba"]):
            dialogo = armar_preferencias(configuracion or {}, "Lectura")
        self.addCleanup(destruir, dialogo)
        return dialogo

    def test_el_grupo_lleva_el_titulo_y_no_hay_etiqueta_suelta(self):
        dialogo = self._dialogo()
        self.assertEqual(dialogo.rb_formato.GetLabel(),
                         "Formato de lectura")
        textos = []
        pendientes = [dialogo.rb_formato.GetParent()]
        while pendientes:
            actual = pendientes.pop()
            if isinstance(actual, gui.wx.StaticText):
                textos.append(actual.GetLabel())
            pendientes.extend(actual.GetChildren())
        self.assertNotIn("Formato de lectura:", textos)


if __name__ == "__main__":
    unittest.main()
