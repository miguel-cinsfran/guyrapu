# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de las salidas de audio que ofrece OBS para el monitoreo."""

import unittest

from guyrapu.core.idioma import _
from guyrapu.obs import salidas_audio

POR_DEFECTO = (_("Por defecto"), "default")


class ClienteFalso:
    """Responde como el WebSocket con lo que se le da."""

    def __init__(self, entradas, items=()):
        self.entradas = entradas
        self.items = items
        self.llamadas = []

    def pedir(self, tipo, datos=None, parada=None):
        self.llamadas.append((tipo, dict(datos or {})))
        if tipo == "GetInputList":
            return {"responseData": {"inputs": list(self.entradas)}}
        if tipo == "GetInputPropertiesListPropertyItems":
            return {"responseData": {"propertyItems": list(self.items)}}
        return {"responseData": {}}

    def tipos(self):
        return [tipo for tipo, _datos in self.llamadas]


class TestConEntradaDeSalida(unittest.TestCase):

    def test_devuelve_la_respuesta_medida_en_la_oficina(self):
        cliente = ClienteFalso(
            [{"inputName": "Audio del escritorio",
              "inputKind": "wasapi_output_capture"}],
            [{"itemName": "Por defecto", "itemValue": "default"},
             {"itemName": "Altavoces (High Definition Audio Device)",
              "itemValue": "{0.0.0.00000000}.{f29b}"}])
        self.assertEqual(salidas_audio.salidas(cliente), (
            POR_DEFECTO,
            ("Altavoces (High Definition Audio Device)",
             "{0.0.0.00000000}.{f29b}"),
        ))

    def test_pide_el_dispositivo_de_esa_entrada(self):
        cliente = ClienteFalso(
            [{"inputName": "Mic/Aux", "inputKind": "wasapi_input_capture"},
             {"inputName": "Audio del escritorio",
              "inputKind": "wasapi_output_capture"}],
            [{"itemName": "Por defecto", "itemValue": "default"}])
        salidas_audio.salidas(cliente)
        pedidos = [datos for tipo, datos in cliente.llamadas
                   if tipo == "GetInputPropertiesListPropertyItems"]
        self.assertEqual(pedidos, [{
            "inputName": "Audio del escritorio",
            "propertyName": "device_id",
        }])


class TestSinEntradaDeSalida(unittest.TestCase):

    def test_sin_entrada_da_solo_por_defecto(self):
        cliente = ClienteFalso(
            [{"inputName": "Mic/Aux", "inputKind": "wasapi_input_capture"}])
        self.assertEqual(salidas_audio.salidas(cliente), (POR_DEFECTO,))

    def test_sin_entrada_no_pide_propiedades(self):
        cliente = ClienteFalso([])
        salidas_audio.salidas(cliente)
        self.assertNotIn("GetInputPropertiesListPropertyItems",
                         cliente.tipos())

    def test_una_respuesta_vacia_tambien_da_por_defecto(self):
        cliente = ClienteFalso(
            [{"inputName": "Audio del escritorio",
              "inputKind": "wasapi_output_capture"}], [])
        self.assertEqual(salidas_audio.salidas(cliente), (POR_DEFECTO,))


if __name__ == "__main__":
    unittest.main()
