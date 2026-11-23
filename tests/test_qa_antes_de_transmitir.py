# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de qa/antes_de_transmitir.py, sin red ni ventanas."""

import importlib.util
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

_RAIZ = Path(__file__).resolve().parent.parent
if str(_RAIZ / "qa") not in sys.path:
    sys.path.insert(0, str(_RAIZ / "qa"))
_espec = importlib.util.spec_from_file_location(
    "antes_de_transmitir_qa", _RAIZ / "qa" / "antes_de_transmitir.py")
antes_de_transmitir = importlib.util.module_from_spec(_espec)
_espec.loader.exec_module(antes_de_transmitir)


class _Anotador:
    def __init__(self):
        self.pasos = []

    def __call__(self, nombre, bien, detalle=""):
        self.pasos.append((nombre, bien, detalle))


class _Cuadro:
    """Cuadro nativo falso con los textos que expone Windows."""

    def __init__(self, *textos):
        self.textos = textos

    def descendants(self):
        return [SimpleNamespace(
            element_info=SimpleNamespace(control_type="Text", name=texto))
            for texto in self.textos]


class TestEsperarDirecto(unittest.TestCase):

    def setUp(self):
        self.anotar = _Anotador()
        self.principal = object()
        self.dialogo = object()
        self.busca = mock.Mock(return_value=None)
        self.nativo = mock.Mock(return_value=None)
        self.pulsa = mock.Mock(return_value=True)
        for nombre, doble in (("_hijo", self.busca),
                              ("dialogo_nativo", self.nativo),
                              ("pulsar_boton_nativo", self.pulsa)):
            parche = mock.patch.object(antes_de_transmitir, nombre, doble)
            parche.start()
            self.addCleanup(parche.stop)

    def test_sin_pregunta_entrega_el_dialogo_y_no_anota(self):
        self.busca.return_value = self.dialogo
        resultado = antes_de_transmitir.esperar_directo(
            self.principal, "Directo de YouTube", 120, self.anotar)
        self.assertIs(resultado, self.dialogo)
        self.assertEqual(self.anotar.pasos, [])
        self.nativo.assert_not_called()

    def test_con_pregunta_pulsa_dejar_y_luego_entrega_el_dialogo(self):
        cuadro = _Cuadro("La cortina de NVDA deja la escena en negro")
        self.busca.side_effect = [None, self.dialogo]
        self.nativo.return_value = cuadro
        resultado = antes_de_transmitir.esperar_directo(
            self.principal, "Directo de YouTube", 120, self.anotar)
        self.assertIs(resultado, self.dialogo)
        self.assertEqual(self.pulsa.call_args_list,
                         [mock.call(cuadro, "Dejar como está")])
        self.assertEqual(self.nativo.call_args_list,
                         [mock.call("Antes de transmitir", segundos=0.5)])
        self.assertEqual(self.anotar.pasos, [
            ("pregunta antes de transmitir", True,
             "La cortina de NVDA deja la escena en negro")])

    def test_sin_boton_dejar_falla_en_el_paso_sin_agotar_el_plazo(self):
        cuadro = _Cuadro("¿Finalizar el directo?")
        self.nativo.return_value = cuadro
        self.pulsa.return_value = False
        with self.assertRaises(RuntimeError) as salida:
            antes_de_transmitir.esperar_directo(
                self.principal, "Directo de YouTube", 120, self.anotar)
        motivo = str(salida.exception)
        self.assertIn("Dejar como está", motivo)
        self.assertEqual(self.busca.call_count, 1)
        self.assertEqual(self.pulsa.call_args_list,
                         [mock.call(cuadro, "Dejar como está")])
        self.assertEqual(len(self.anotar.pasos), 1)
        nombre, bien, detalle = self.anotar.pasos[0]
        self.assertEqual(nombre, "pregunta antes de transmitir")
        self.assertFalse(bien)
        self.assertEqual(detalle, motivo)

    def test_la_demo_en_ingles_pulsa_leave_as_it_is(self):
        cuadro = _Cuadro("NVDA curtain leaves the scene black")
        self.busca.side_effect = [None, self.dialogo]
        self.nativo.return_value = cuadro
        resultado = antes_de_transmitir.esperar_directo(
            self.principal, "YouTube live stream", 120, self.anotar,
            pregunta="Before broadcasting", dejar="Leave as it is")
        self.assertIs(resultado, self.dialogo)
        self.assertEqual(self.pulsa.call_args_list,
                         [mock.call(cuadro, "Leave as it is")])
        self.assertEqual(self.nativo.call_args_list,
                         [mock.call("Before broadcasting", segundos=0.5)])
        self.assertEqual(self.anotar.pasos, [
            ("pregunta antes de transmitir", True,
             "NVDA curtain leaves the scene black")])


if __name__ == "__main__":
    unittest.main()
