# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pseudotraducción de la página Música de Preferencias.

Abre ventanas.
Construye el diálogo de Preferencias con la pseudotraducción y exige que
la página no deje ningún texto visible sin envolver.
"""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import wx

from guyrapu.music import atenuacion
from guyrapu.ui import gui_preferencias, preferencias_transmision
from guyrapu.voice import motores
from tests.pseudo_prueba import con_pseudo, textos_sin_marcar
from tests.rutas_temporales import redirigir_rutas
from tests.ventanas_prueba import (app_de_prueba, armar_preferencias, destruir,
                                   pagina_por_titulo)


# Textos que arma otro módulo y aparecen en la parte recorrida: no se
# tocan acá. La salida predeterminada (`guyrapu/ui/opciones_musica.py`)
# ya pasa por gettext y sale marcada, así que no deja pendientes.
PENDIENTES_OTROS_MODULOS = ()


class TestPseudoMusica(unittest.TestCase):
    def setUp(self):
        self.app = app_de_prueba()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        parche = redirigir_rutas(Path(self.tmp.name))
        parche.__enter__()
        self.addCleanup(parche.__exit__, None, None, None)

    def _dialogo(self):
        with mock.patch.object(motores, "listar_voces",
                               return_value=["Voz de prueba"]):
            dialogo = armar_preferencias({}, "Música")
        self.addCleanup(destruir, dialogo)
        return dialogo

    def test_no_queda_ningun_texto_visible_sin_envolver(self):
        with con_pseudo():
            dialogo = self._dialogo()
            pagina = pagina_por_titulo(dialogo, "Música")
            sin_marcar = textos_sin_marcar(
                pagina, propios=PENDIENTES_OTROS_MODULOS)

        self.assertEqual([], sin_marcar)

    def test_el_volumen_es_deslizador_y_el_fundido_sigue_siendo_contador(self):
        dialogo = self._dialogo()
        pagina = dialogo.pagina_musica
        self.assertIsInstance(pagina.sp_musica_volumen, wx.Slider)
        self.assertIsInstance(pagina.sp_musica_cruce, wx.SpinCtrl)
        pagina.sp_musica_volumen.SetValue(75)
        with mock.patch.object(gui_preferencias._snd, "reproducir"), \
                mock.patch.object(preferencias_transmision, "anunciar"), \
                mock.patch.object(dialogo, "EndModal"):
            dialogo._on_guardar(None)
        self.assertEqual(dialogo._config["musica_volumen"], 75)

    def test_el_fundido_esta_a_cuatro_pixeles_de_su_rotulo(self):
        dialogo = self._dialogo()
        panel = dialogo.pagina_musica.sp_musica_cruce.GetParent()
        panel.Layout()
        etiqueta = [h for h in panel.GetChildren()
                    if isinstance(h, wx.StaticText)
                    and h.GetLabel() == "&Fundido entre canciones, en segundos:"][0]
        self.assertEqual(
            dialogo.sp_musica_cruce.GetPosition().y - (
                etiqueta.GetPosition().y + etiqueta.GetSize().GetHeight()), 4)

    def test_las_casillas_de_atenuacion_salen_del_registro_y_se_guardan(self):
        dialogo = self._dialogo()
        pagina = dialogo.pagina_musica
        self.assertEqual(pagina.sp_musica_volumen_atenuado.GetValue(),
                         atenuacion.VOLUMEN_FABRICA)
        for fuente in atenuacion.FUENTES:
            casilla = getattr(pagina, f"chk_musica_atenuar_{fuente.id}")
            self.assertIsInstance(casilla, wx.CheckBox)
            self.assertEqual(casilla.GetValue(), fuente.fabrica)
            casilla.SetValue(not fuente.fabrica)
        pagina.sp_musica_volumen_atenuado.SetValue(45)
        with mock.patch.object(gui_preferencias._snd, "reproducir"), \
                mock.patch.object(preferencias_transmision, "anunciar"), \
                mock.patch.object(dialogo, "EndModal"):
            dialogo._on_guardar(None)
        for fuente in atenuacion.FUENTES:
            self.assertEqual(
                dialogo._config[f"musica_atenuar_{fuente.id}"],
                not fuente.fabrica)
        self.assertEqual(dialogo._config["musica_volumen_atenuado"], 45)


    def test_el_grupo_de_pedidos_tiene_los_controles_y_valores_de_fabrica(self):
        pagina = self._dialogo().pagina_musica
        where = pagina.cho_musica_pedidos_donde
        self.assertIsInstance(where, wx.Choice)
        self.assertEqual(
            [where.GetString(i) for i in range(where.GetCount())],
            ["Al final de la cola", "Antes que el resto de la cola",
             "Al momento, cortando el tema actual"])
        self.assertEqual(where.GetValue(), "continuacion")
        self.assertEqual(where.GetName(), "Reproducir pedidos")
        for atributo, minimo, maximo, defecto, nombre in (
                ("sp_musica_pedidos_duracion", 1, 60, 10,
                 "Duración máxima de un pedido, en minutos"),
                ("sp_musica_pedidos_persona", 1, 10, 2,
                 "Pedidos pendientes por persona"),
                ("sp_musica_pedidos_total", 1, 50, 10,
                 "Pedidos pendientes en total")):
            with self.subTest(atributo=atributo):
                control = getattr(pagina, atributo)
                self.assertIsInstance(control, wx.SpinCtrl)
                self.assertEqual(
                    (control.GetMin(), control.GetMax(), control.GetValue()),
                    (minimo, maximo, defecto))
                self.assertEqual(control.GetName(), nombre)
        for atributo in ("chk_musica_pedidos_responder",
                         "chk_musica_pedidos_bloquear"):
            casilla = getattr(pagina, atributo)
            self.assertIsInstance(casilla, wx.CheckBox)
            self.assertTrue(casilla.GetValue())

    def test_cada_contador_de_pedidos_sigue_a_su_propio_rotulo(self):
        pagina = self._dialogo().pagina_musica
        for atributo, rotulo in (
                ("sp_musica_pedidos_duracion",
                 "Duración máxima de un pedido (minutos):"),
                ("sp_musica_pedidos_persona",
                 "Pedidos pendientes por persona:"),
                ("sp_musica_pedidos_total",
                 "Pedidos pendientes en total:")):
            with self.subTest(atributo=atributo):
                control = getattr(pagina, atributo)
                hijos = list(control.GetParent().GetChildren())
                anterior = hijos[hijos.index(control) - 1]
                self.assertIsInstance(anterior, wx.StaticText)
                self.assertEqual(anterior.GetLabel().replace("&", ""), rotulo)

    def test_el_grupo_de_pedidos_se_guarda_en_la_seccion_musica(self):
        dialogo = self._dialogo()
        pagina = dialogo.pagina_musica
        pagina.cho_musica_pedidos_donde.SetValue("ahora")
        pagina.sp_musica_pedidos_duracion.SetValue(3)
        pagina.sp_musica_pedidos_persona.SetValue(4)
        pagina.sp_musica_pedidos_total.SetValue(12)
        pagina.chk_musica_pedidos_responder.SetValue(False)
        pagina.chk_musica_pedidos_bloquear.SetValue(False)
        with mock.patch.object(gui_preferencias._snd, "reproducir"), \
                mock.patch.object(preferencias_transmision, "anunciar"), \
                mock.patch.object(dialogo, "EndModal"):
            dialogo._on_guardar(None)
        escritos = {clave: valor for _seccion, clave, valor
                    in dialogo._pendientes if _seccion == "musica"}
        self.assertEqual(escritos["pedidos_donde"], "ahora")
        self.assertEqual(escritos["pedidos_duracion"], "3")
        self.assertEqual(escritos["pedidos_persona"], "4")
        self.assertEqual(escritos["pedidos_total"], "12")
        self.assertEqual(escritos["pedidos_responder"], "false")
        self.assertEqual(escritos["pedidos_bloquear"], "false")
        self.assertEqual(dialogo._config["musica_pedidos_donde"], "ahora")
        self.assertEqual(dialogo._config["musica_pedidos_duracion"], 3)


if __name__ == "__main__":
    unittest.main()
