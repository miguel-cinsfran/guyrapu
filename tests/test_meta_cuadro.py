# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Cuadro de la meta: campos, nombres accesibles, validación y datos.

Abre ventanas.
"""

import tempfile
import unittest
from unittest import mock

import wx

from guyrapu.core import paths
from guyrapu.core.idioma import _
from guyrapu.interaction import medios_guardados, metas
from guyrapu.obs import estilos_aviso
from guyrapu.ui import meta_cuadro
from tests.letras_acceso import letras_repetidas
from tests.rutas_temporales import redirigir_rutas
from tests.ventanas_prueba import app_de_prueba, destruir

NOMBRES_ACCESIBLES = (
    "Nombre", "Qué cuenta", "Objetivo", "Estilo", "Festejo", "Aceptar",
    "Cancelar")

ETIQUETAS = (
    "&Nombre:", "&Qué cuenta:", "&Objetivo:", "Esti&lo:", "&Festejo:")


class BaseCuadro(unittest.TestCase):

    def setUp(self):
        self.app = app_de_prueba()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        parche = redirigir_rutas(self.tmp.name)
        parche.__enter__()
        self.addCleanup(parche.__exit__, None, None, None)
        medios_guardados.guardar(paths.medios(), [{
            "nombre": "aplauso.gif", "tipo": "imagen",
            "archivo": "aplauso.gif"}])

    def _cuadro(self, datos=None, otros=()):
        cuadro = meta_cuadro.DialogoMeta(None, datos or {}, otros)
        self.addCleanup(destruir, cuadro)
        return cuadro

    def _aceptar_con_error(self, cuadro):
        with mock.patch.object(meta_cuadro, "anunciar") as decir, \
                mock.patch.object(cuadro, "EndModal") as cerrar:
            cuadro._aceptar(None)
        cerrar.assert_not_called()
        return decir


class TestCampos(BaseCuadro):

    def test_los_campos_van_en_el_orden_pedido(self):
        panel = self._cuadro().GetChildren()[0]
        etiquetas = [hijo.GetLabel() for hijo in panel.GetChildren()
                     if isinstance(hijo, wx.StaticText)]
        self.assertEqual(tuple(etiquetas), ETIQUETAS)

    def test_cada_control_tiene_el_nombre_accesible_de_su_rotulo(self):
        cuadro = self._cuadro()
        controles = (
            cuadro.txt_nombre, cuadro.cho_que_cuenta, cuadro.sp_objetivo,
            cuadro.cho_estilo, cuadro.cho_festejo, cuadro.btn_aceptar,
            cuadro.btn_cancelar)
        self.assertEqual(
            tuple(control.GetName() for control in controles),
            NOMBRES_ACCESIBLES)

    def test_que_cuenta_tiene_las_cinco_opciones_visibles(self):
        cuadro = self._cuadro()
        self.assertEqual(
            cuadro.cho_que_cuenta.GetStrings(),
            [_(metas.NOMBRES_QUE_CUENTA[clave])
             for clave in metas.QUE_CUENTA])

    def test_el_objetivo_llega_hasta_un_millon(self):
        cuadro = self._cuadro()
        self.assertEqual(cuadro.sp_objetivo.GetMax(), 1000000)

    def test_el_festejo_trae_la_biblioteca_y_ninguno(self):
        cuadro = self._cuadro()
        self.assertEqual(cuadro.cho_festejo.GetStrings(),
                         ["Ninguno", "aplauso.gif"])

    def test_p3_la_eleccion_empieza_por_el_predeterminado(self):
        cuadro = self._cuadro()
        self.assertEqual(cuadro.cho_estilo.GetString(0),
                         "Predeterminado (Clásico)")
        self.assertEqual(cuadro.cho_estilo.GetSelection(), 0)
        self.assertEqual(cuadro.datos()["estilo"], "")

    def test_p3_el_predeterminado_lleva_el_nombre_del_estilo_del_tipo(self):
        estilos_aviso.guardar_por_tipo(
            paths.estilos_avisos(), {"meta": "banda"})
        cuadro = self._cuadro()
        self.assertEqual(cuadro.cho_estilo.GetString(0),
                         "Predeterminado (Banda)")

    def test_las_letras_de_acceso_no_se_repiten_en_el_cuadro(self):
        self.assertEqual(letras_repetidas(self._cuadro()), {})

    def test_el_foco_nace_en_el_nombre(self):
        cuadro = self._cuadro()
        cuadro.Show()
        try:
            self.assertIs(wx.Window.FindFocus(), cuadro.txt_nombre)
        finally:
            cuadro.Hide()

    def test_el_titulo_dice_si_se_agrega_o_se_edita(self):
        self.assertEqual(self._cuadro().GetTitle(), "Agregar meta")
        self.assertEqual(
            self._cuadro({"nombre": "A", "que_cuenta": "me_gusta",
                          "objetivo": 1}).GetTitle(), "Editar meta")

    def test_escape_cierra_el_cuadro(self):
        evento = mock.Mock()
        evento.GetKeyCode.return_value = wx.WXK_ESCAPE
        cuadro = self._cuadro()
        with mock.patch.object(cuadro, "EndModal") as cerrar:
            cuadro._al_tecla(evento)
        cerrar.assert_called_once_with(wx.ID_CANCEL)


class TestDatos(BaseCuadro):

    def test_guarda_cada_campo(self):
        cuadro = self._cuadro()
        cuadro.txt_nombre.SetValue("Viaje")
        cuadro.cho_que_cuenta.SetSelection(metas.QUE_CUENTA.index("regalos"))
        cuadro.sp_objetivo.SetValue(500)
        cuadro.cho_festejo.SetSelection(1)
        cuadro._elegir_estilo("banda")
        self.assertEqual(cuadro.datos(), {
            "nombre": "Viaje", "que_cuenta": "regalos", "objetivo": 500,
            "estilo": "banda", "festejo": "aplauso.gif", "activa": True})

    def test_se_abre_con_los_datos_de_la_meta(self):
        cuadro = self._cuadro({
            "nombre": "Viaje", "que_cuenta": "regalos", "objetivo": 42,
            "estilo": "banda", "festejo": "aplauso.gif", "activa": True})
        self.assertEqual(cuadro.txt_nombre.GetValue(), "Viaje")
        self.assertEqual(cuadro.cho_que_cuenta.GetSelection(),
                         metas.QUE_CUENTA.index("regalos"))
        self.assertEqual(cuadro.sp_objetivo.GetValue(), 42)
        self.assertEqual(cuadro._meta_de_campos().estilo, "banda")
        self.assertEqual(cuadro._festejo_elegido(), "aplauso.gif")

    def test_aceptar_con_datos_validos_cierra(self):
        cuadro = self._cuadro()
        cuadro.txt_nombre.SetValue("Viaje")
        with mock.patch.object(cuadro, "EndModal") as cerrar:
            cuadro._aceptar(None)
        cerrar.assert_called_once_with(wx.ID_OK)

    def test_conserva_el_estado_de_pausa_al_editar(self):
        cuadro = self._cuadro({
            "nombre": "Viaje", "que_cuenta": "me_gusta", "objetivo": 100,
            "activa": False})
        self.assertFalse(cuadro.datos()["activa"])


class TestValidacion(BaseCuadro):

    def test_p3_un_objetivo_de_cero_manda_el_foco_al_objetivo(self):
        cuadro = self._cuadro()
        cuadro.txt_nombre.SetValue("Viaje")
        cuadro.sp_objetivo.SetValue(0)
        with mock.patch.object(cuadro.sp_objetivo, "SetFocus") as foco:
            decir = self._aceptar_con_error(cuadro)
        foco.assert_called_once()
        self.assertIn("objetivo", decir.call_args.args[0])

    def test_un_nombre_vacio_manda_el_foco_al_nombre(self):
        cuadro = self._cuadro()
        cuadro.sp_objetivo.SetValue(10)
        with mock.patch.object(cuadro.txt_nombre, "SetFocus") as foco:
            decir = self._aceptar_con_error(cuadro)
        foco.assert_called_once()
        self.assertIn("nombre", decir.call_args.args[0])

    def test_un_nombre_repetido_manda_el_foco_al_nombre(self):
        otro = {"nombre": "Viaje", "que_cuenta": "me_gusta", "objetivo": 10}
        cuadro = self._cuadro({}, [otro])
        cuadro.txt_nombre.SetValue("VIAJE")
        with mock.patch.object(cuadro.txt_nombre, "SetFocus") as foco:
            self._aceptar_con_error(cuadro)
        foco.assert_called_once()


if __name__ == "__main__":
    unittest.main()
