# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de la página Cuenta de Restream que no se deshabilita.

Abren ventanas. Mientras hay un trabajo de la cuenta en curso, los tres
botones siguen en el recorrido con Tab, llevan el motivo en la etiqueta y,
al activarlos, lo anuncian sin hacer nada más.
"""

import unittest
from unittest import mock

import wx

from guyrapu.capture import redaccion
from guyrapu.ui import restream_pagina_cuenta
from tests.ventanas_prueba import app_de_prueba, destruir


BASES = ("&Conectar", "&Volver a autorizar", "&Desconectar")
MOTIVO = "Esperando a Restream"


def _pulsar(boton):
    boton.GetEventHandler().ProcessEvent(
        wx.CommandEvent(wx.EVT_BUTTON.typeId, boton.GetId()))


class PruebaPaginaCuenta(unittest.TestCase):

    def setUp(self):
        self.app = app_de_prueba()

    def _pagina(self, al_conectar=None, al_reautorizar=None,
                al_desconectar=None):
        marco = wx.Frame(None)
        self.addCleanup(destruir, marco)
        pagina = restream_pagina_cuenta.PaginaCuenta(
            marco, al_conectar or (lambda: None),
            al_reautorizar or (lambda: None),
            al_desconectar or (lambda: None))
        self.addCleanup(destruir, pagina)
        return pagina

    def _botones(self, pagina):
        return (pagina.btn_conectar, pagina.btn_reautorizar,
                pagina.btn_desconectar)

    def test_p1_los_tres_botones_nunca_se_deshabilitan(self):
        pagina = self._pagina()
        for trabajo in (False, True, False):
            pagina.fijar_trabajo_en_curso(trabajo)
            for boton in self._botones(pagina):
                self.assertTrue(boton.IsEnabled())

    def test_p2_mientras_hay_trabajo_las_etiquetas_llevan_el_motivo(self):
        pagina = self._pagina()
        pagina.fijar_trabajo_en_curso(True)
        for boton, base in zip(self._botones(pagina), BASES):
            self.assertEqual(
                redaccion.etiqueta_con_motivo(base, MOTIVO),
                boton.GetLabel())

        pagina.fijar_trabajo_en_curso(False)
        for boton, base in zip(self._botones(pagina), BASES):
            self.assertEqual(base, boton.GetLabel())

    def test_p3_conectar_y_reautorizar_esperan_sin_abrir_el_navegador(self):
        llamadas = []
        pagina = self._pagina(
            al_conectar=lambda: llamadas.append("conectar"),
            al_reautorizar=lambda: llamadas.append("reautorizar"))
        pagina.fijar_trabajo_en_curso(True)

        with mock.patch.object(restream_pagina_cuenta,
                               "anunciar") as anunciar:
            _pulsar(pagina.btn_conectar)
            _pulsar(pagina.btn_reautorizar)

        self.assertEqual([mock.call("Esperando a Restream.")] * 2,
                         anunciar.call_args_list)
        self.assertEqual([], llamadas)

    def test_p3_desconectar_espera_sin_preguntar(self):
        desconectadas = []
        pagina = self._pagina(
            al_desconectar=lambda: desconectadas.append(True))
        pagina.fijar_trabajo_en_curso(True)

        with mock.patch.object(restream_pagina_cuenta.confirmar,
                               "preguntar") as preguntar, \
                mock.patch.object(restream_pagina_cuenta,
                                  "anunciar") as anunciar:
            _pulsar(pagina.btn_desconectar)

        preguntar.assert_not_called()
        anunciar.assert_called_once_with("Esperando a Restream.")
        self.assertEqual([], desconectadas)


if __name__ == "__main__":
    unittest.main()
