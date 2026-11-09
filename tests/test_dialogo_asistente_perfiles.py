# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de los cuadros del asistente de perfiles. Abren ventanas con wx."""

import unittest
from unittest import mock

import wx

from tests.ventanas_prueba import app_de_prueba, destruir
from guyrapu.core.idioma import _
from guyrapu.obs import ajustes_perfil, asistente_perfiles
from guyrapu.ui import dialogo_asistente_perfiles as modulo


def _perfil(nombre, uso):
    return asistente_perfiles.PerfilPreparado(
        nombre, uso, ajustes_perfil.valores_iniciales(uso == "perfil_vertical",
                                                      "x264"))


class TestDialogoAsistentePerfiles(unittest.TestCase):

    def setUp(self):
        self.app = app_de_prueba()
        self.dialogo = modulo.DialogoAsistentePerfiles(None)
        self.addCleanup(destruir, self.dialogo)

    def test_las_casillas_nacen_como_se_pide(self):
        self.assertTrue(self.dialogo.casillas["perfil_horizontal"].GetValue())
        self.assertTrue(self.dialogo.casillas["perfil_vertical"].GetValue())
        self.assertFalse(self.dialogo.casillas["perfil_grabar"].GetValue())
        self.assertTrue(self.dialogo.chk_probar.GetValue())

    def test_las_casillas_tienen_su_nombre_accesible_sin_la_letra(self):
        self.assertEqual(
            self.dialogo.casillas["perfil_horizontal"].GetName(),
            "Transmitir en horizontal (YouTube)")
        self.assertEqual(
            self.dialogo.casillas["perfil_vertical"].GetName(),
            "Transmitir en vertical (TikTok)")
        self.assertEqual(self.dialogo.casillas["perfil_grabar"].GetName(),
                         "Grabar")
        self.assertEqual(self.dialogo.chk_probar.GetName(),
                         "Probar cada perfil con el equipo")

    def test_preparar_sin_ningun_uso_lo_dice_y_no_entrega_eleccion(self):
        for casilla in self.dialogo.casillas.values():
            casilla.SetValue(False)
        with mock.patch.object(modulo, "anunciar") as anunciar:
            self.dialogo._al_preparar(None)
        anunciar.assert_called_once_with(_(modulo.SIN_USO))
        self.assertEqual(self.dialogo.usos(), [])

    def test_la_eleccion_devuelve_los_usos_y_la_prueba(self):
        self.dialogo.casillas["perfil_grabar"].SetValue(True)
        self.dialogo.chk_probar.SetValue(False)
        self.assertEqual(
            self.dialogo.eleccion(),
            (["perfil_horizontal", "perfil_vertical", "perfil_grabar"],
             False))


class TestDialogoResumen(unittest.TestCase):

    def setUp(self):
        self.app = app_de_prueba()

    def test_muestra_una_linea_por_perfil_y_recibe_el_foco(self):
        resultado = asistente_perfiles.ResultadoAsistente((
            _perfil("Guyrapu horizontal", "perfil_horizontal"),
            _perfil("Guyrapu grabación", "perfil_grabar"),
        ))
        texto = "\n".join(asistente_perfiles.lineas_resumen(resultado))
        dialogo = modulo.DialogoResumenAsistente(None, texto)
        self.addCleanup(destruir, dialogo)
        self.assertEqual(dialogo.txt_resumen.GetValue().count("\n"), 1)
        self.assertIn("Guyrapu horizontal", dialogo.txt_resumen.GetValue())
        self.assertEqual(dialogo.btn_cerrar.GetLabel(), _("&Cerrar"))
        self.assertEqual(dialogo.btn_cerrar.GetName(), "Cerrar")
        self.assertIs(wx.Window.FindFocus(), dialogo.txt_resumen)


class _OperacionesQueEjecuta:
    """Corre el trabajo en el acto y no avisa el final."""

    def en_hilo(self, funcion, al_terminar=None):
        funcion()


class _ProgresoFalso:
    def __init__(self, _ventana, _titulo, _texto, _parada):
        pass

    def ShowModal(self):
        return wx.ID_OK

    def Destroy(self):
        pass

    def estado(self, _texto):
        pass


class TestAnteriores(unittest.TestCase):

    def setUp(self):
        self.app = app_de_prueba()

    def test_preparar_recibe_el_perfil_que_tenia_cada_uso(self):
        capturado = {}

        def preparar_falso(cliente, usos, **opciones):
            capturado.update(opciones)
            return asistente_perfiles.ResultadoAsistente(())

        config = {"perfil_horizontal": "YouTube", "perfil_vertical": "TikTok",
                  "perfil_grabar": ""}
        panel = modulo.AsistentePerfilesPanel(
            None, _OperacionesQueEjecuta(), lambda: object(), config,
            lambda _resultado: None)
        with mock.patch.object(modulo.asistente_perfiles, "preparar",
                               preparar_falso), \
                mock.patch.object(modulo, "VentanaEspera",
                                  _ProgresoFalso):
            panel._correr(["perfil_horizontal"], True)
        self.assertEqual(
            capturado["anteriores"],
            {"perfil_horizontal": "YouTube", "perfil_vertical": "TikTok",
             "perfil_grabar": ""})

    def test_un_fallo_despues_de_abrir_la_ventana_queda_escrito(self):
        panel = modulo.AsistentePerfilesPanel(
            None, _OperacionesQueEjecuta(), lambda: object(), {},
            lambda _resultado: None)
        progreso = mock.Mock()
        panel._terminado(progreso, RuntimeError("sin OBS"))
        progreso.terminar.assert_called_once_with("sin OBS", error=True)

    def test_una_cancelacion_queda_escrita_en_la_ventana(self):
        resultado = asistente_perfiles.ResultadoAsistente((), cancelada=True)
        progreso = mock.Mock()
        with mock.patch.object(modulo, "anunciar") as anunciar:
            modulo.AsistentePerfilesPanel(
                None, _OperacionesQueEjecuta(), lambda: object(), {},
                lambda _resultado: None)._terminado(progreso, resultado)
        progreso.terminar.assert_called_once_with(
            _(modulo.MENSAJE_CANCELADO), error=False)
        anunciar.assert_not_called()


if __name__ == "__main__":
    unittest.main()
