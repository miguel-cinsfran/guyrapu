# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas del botón del directo del panel de transmisión."""

from unittest import mock
import unittest

from guyrapu.obs import transmision_directa
from guyrapu.ui import comando_directo
from guyrapu.ui import directo_panel


class TestDirectoPanel(unittest.TestCase):

    def setUp(self):
        self.ventana = mock.Mock()
        self.boton = mock.Mock()
        self.al_cambiar = mock.Mock()
        self.comando = comando_directo.ComandoDirecto(mock.Mock())
        self.panel = directo_panel.DirectoPanel(
            self.ventana, self.boton, self.comando, self.al_cambiar)

    def test_etiqueta_inicial(self):
        self.boton.SetLabel.assert_called_once_with("Transm&itir en directo")
        self.boton.SetName.assert_called_once_with("Transmitir en directo")

    def test_sincronizar_cambia_el_rotulo_y_avisa(self):
        self.comando.sincronizar(True)
        self.assertTrue(self.panel.transmitiendo)
        self.assertFalse(self.panel.deteniendo)
        self.boton.SetLabel.assert_called_with("&Finalizar directo")
        self.boton.SetName.assert_called_with("Finalizar directo")
        self.al_cambiar.assert_called()

    def test_sincronizar_deteniendo_muestra_la_espera(self):
        self.comando.sincronizar(True, deteniendo=True)
        self.assertTrue(self.panel.transmitiendo)
        self.assertTrue(self.panel.deteniendo)
        self.boton.SetLabel.assert_called_with("Finalizando el directo")
        self.boton.SetName.assert_called_with(
            "Finalizando el directo, esperando a OBS")

    def test_pulsar_llama_al_comando_con_la_ventana(self):
        comando = mock.Mock()
        comando.transmitiendo = False
        comando.deteniendo = False
        panel = directo_panel.DirectoPanel(
            self.ventana, mock.Mock(), comando, None)
        panel._al_pulsar(None)
        comando.pulsar.assert_called_once_with(self.ventana)

    def test_cerrar_deja_de_avisar(self):
        self.boton.SetLabel.reset_mock()
        self.panel.cerrar()
        self.comando.sincronizar(True)
        self.boton.SetLabel.assert_not_called()


class TestPrepararCerrarGestor(unittest.TestCase):

    def _gestor(self):
        gestor = mock.Mock()
        gestor.estado_transmision.return_value = {"outputActive": False}
        gestor.perfil_actual.return_value = "YouTube"
        gestor.preparar_destino.return_value = {}
        gestor.revisar.return_value = mock.sentinel.revision
        return gestor

    def test_cerrar_false_no_cierra_el_gestor(self):
        gestor = self._gestor()
        preparacion = transmision_directa.preparar(
            gestor, "YouTube", lambda *a, **k: False, lambda frase: None,
            cerrar=False)
        gestor.cerrar.assert_not_called()
        self.assertIs(preparacion.revision, mock.sentinel.revision)

    def test_cerrar_por_defecto_sigue_cerrando(self):
        gestor = self._gestor()
        transmision_directa.preparar(
            gestor, "YouTube", lambda *a, **k: False, lambda frase: None)
        gestor.cerrar.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
