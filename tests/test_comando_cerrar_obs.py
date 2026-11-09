# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas sin ventana de `guyrapu/ui/comando_cerrar_obs.py`."""

import unittest
from unittest import mock

from guyrapu.core.idioma import _
from guyrapu.ui import comando_cerrar_obs


class HiloInmediato:
    """Doble de `diagnostico.crear_hilo` que ejecuta el objetivo al arrancar."""

    def __init__(self, target, nombre, **kwargs):
        self.target = target
        self.nombre = nombre
        self.daemon = kwargs.get("daemon", True)
        self.iniciado = False

    def start(self):
        self.iniciado = True
        self.target()


class HiloSinArrancar(HiloInmediato):
    def start(self):
        self.iniciado = True


class GestorFalso:
    def __init__(self, transmision=False, grabacion=False, fallo=None):
        self.transmision = transmision
        self.grabacion = grabacion
        self.fallo = fallo
        self.llamadas = []
        self.cerrado = False

    def conectar(self):
        self.llamadas.append("conectar")
        if self.fallo is not None:
            raise self.fallo

    def estado_transmision(self):
        self.llamadas.append("estado_transmision")
        if self.fallo is not None:
            raise self.fallo
        return {"outputActive": self.transmision}

    def estado_grabacion(self):
        self.llamadas.append("estado_grabacion")
        if self.fallo is not None:
            raise self.fallo
        return {"outputActive": self.grabacion}

    def cerrar(self):
        self.cerrado = True


class TestComandoCerrarObs(unittest.TestCase):

    def _correr(self, en_ejecucion=True, gestor=None, se_cierra=True,
                hilo=HiloInmediato):
        gestor = gestor or GestorFalso()
        anuncios = mock.Mock()
        sonidos = mock.Mock()
        with mock.patch.object(
                comando_cerrar_obs.obs_activacion, "obs_esta_en_ejecucion",
                return_value=en_ejecucion) as en_marcha, \
                mock.patch.object(comando_cerrar_obs, "GestorPanelObs",
                                  return_value=gestor), \
                mock.patch.object(comando_cerrar_obs.obs_lanzador,
                                  "cerrar_obs",
                                  return_value=se_cierra) as cerrar, \
                mock.patch.object(comando_cerrar_obs.diagnostico,
                                  "crear_hilo", hilo), \
                mock.patch.object(comando_cerrar_obs, "_diferir",
                                  side_effect=lambda funcion: funcion()), \
                mock.patch.object(comando_cerrar_obs.sound_player,
                                  "reproducir", sonidos):
            comando_cerrar_obs.cerrar(anuncios)
        return gestor, anuncios, sonidos, cerrar, en_marcha

    def test_obs_cerrado_anuncia_y_no_pide_el_cierre(self):
        gestor, anuncios, sonidos, cerrar, _en_marcha = self._correr(
            en_ejecucion=False)
        anuncios.assert_called_once_with(_("OBS no está abierto."))
        cerrar.assert_not_called()
        sonidos.assert_not_called()
        self.assertEqual(gestor.llamadas, [])

    def test_transmitiendo_o_grabando_no_cierra_y_avisa_con_error(self):
        for estado in ("transmision", "grabacion"):
            with self.subTest(estado=estado):
                gestor = GestorFalso(**{estado: True})
                _gestor, anuncios, sonidos, cerrar, _en_marcha = self._correr(
                    gestor=gestor)
                cerrar.assert_not_called()
                sonidos.assert_called_once_with("error")
                anuncios.assert_called_once_with(
                    _("OBS está transmitiendo o grabando. "
                      "Detenlo antes de cerrar OBS."))
                self.assertTrue(gestor.cerrado)

    def test_si_la_consulta_falla_cierra_igual(self):
        gestor = GestorFalso(fallo=RuntimeError("OBS no contesta"))
        _gestor, anuncios, sonidos, cerrar, _en_marcha = self._correr(
            gestor=gestor)
        cerrar.assert_called_once_with()
        anuncios.assert_any_call(_("Cerrando OBS…"))
        anuncios.assert_any_call(_("OBS cerrado."))
        sonidos.assert_not_called()
        self.assertTrue(gestor.cerrado)

    def test_cierre_correcto_anuncia_al_empezar_y_al_terminar(self):
        _gestor, anuncios, sonidos, cerrar, _en_marcha = self._correr(
            se_cierra=True)
        cerrar.assert_called_once_with()
        self.assertEqual(
            anuncios.call_args_list,
            [mock.call(_("Cerrando OBS…")), mock.call(_("OBS cerrado."))])
        sonidos.assert_not_called()

    def test_si_no_se_cierra_en_el_plazo_avisa_con_error(self):
        _gestor, anuncios, sonidos, _cerrar, _en_marcha = self._correr(
            se_cierra=False)
        anuncios.assert_any_call(_("Cerrando OBS…"))
        anuncios.assert_any_call(
            _("OBS no se cerró. Ciérralo desde su ventana."))
        sonidos.assert_called_once_with("error")

    def test_anuncia_cerrando_antes_de_pedir_el_cierre(self):
        eventos = []
        with mock.patch.object(
                comando_cerrar_obs.obs_activacion, "obs_esta_en_ejecucion",
                return_value=True), \
                mock.patch.object(comando_cerrar_obs, "GestorPanelObs",
                                  return_value=GestorFalso()), \
                mock.patch.object(
                    comando_cerrar_obs.obs_lanzador, "cerrar_obs",
                    side_effect=lambda: eventos.append("cierre") or True), \
                mock.patch.object(comando_cerrar_obs.diagnostico,
                                  "crear_hilo", HiloInmediato), \
                mock.patch.object(comando_cerrar_obs, "_diferir",
                                  side_effect=lambda funcion: funcion()):
            comando_cerrar_obs.cerrar(eventos.append)
        self.assertEqual(
            eventos, [_("Cerrando OBS…"), "cierre", _("OBS cerrado.")])

    def test_corre_en_su_propio_hilo(self):
        nombres = []

        class HiloAnotado(HiloSinArrancar):
            def __init__(self, target, nombre, **kwargs):
                super().__init__(target, nombre, **kwargs)
                nombres.append(nombre)

        _gestor, _anuncios, _sonidos, _cerrar, en_marcha = self._correr(
            hilo=HiloAnotado)
        en_marcha.assert_not_called()
        self.assertEqual(nombres, ["CerrarObs"])


if __name__ == "__main__":
    unittest.main()
