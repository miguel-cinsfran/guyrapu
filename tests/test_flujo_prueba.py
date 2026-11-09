# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas del flujo RTMP de la prueba de conexión, sin red."""

import unittest

from guyrapu.youtube import flujo_prueba


class ServicioFalso:
    def __init__(self, respuesta):
        self.respuesta = respuesta
        self.metodo = ""
        self.parametros = {}

    def liveStreams(self):
        return self

    def insert(self, **kwargs):
        self.metodo = "insert"
        self.parametros = kwargs
        return self

    def delete(self, **kwargs):
        self.metodo = "delete"
        self.parametros = kwargs
        return self

    def execute(self):
        return self.respuesta


class TestCrear(unittest.TestCase):

    def test_devuelve_id_servidor_y_clave(self):
        servicio = ServicioFalso({
            "id": "flujo-nuevo",
            "cdn": {"ingestionInfo": {
                "ingestionAddress": "rtmp://a.rtmp.youtube.com/live2",
                "streamName": "clave-nueva"}}})
        self.assertEqual(
            flujo_prueba.crear(servicio, "Prueba de conexión"),
            ("flujo-nuevo", "rtmp://a.rtmp.youtube.com/live2",
             "clave-nueva"))
        self.assertEqual(servicio.metodo, "insert")
        self.assertIn("cdn", servicio.parametros.get("part", ""))
        cuerpo = servicio.parametros.get("body", {})
        self.assertEqual(cuerpo["snippet"]["title"], "Prueba de conexión")
        self.assertFalse(cuerpo["contentDetails"]["isReusable"])

    def test_sin_datos_devuelve_vacios(self):
        self.assertEqual(flujo_prueba.crear(ServicioFalso({}), "Prueba"),
                         ("", "", ""))


class TestBorrar(unittest.TestCase):

    def test_manda_el_id(self):
        servicio = ServicioFalso({})
        flujo_prueba.borrar(servicio, "flujo-nuevo")
        self.assertEqual(servicio.metodo, "delete")
        self.assertEqual(servicio.parametros.get("id"), "flujo-nuevo")


if __name__ == "__main__":
    unittest.main()
