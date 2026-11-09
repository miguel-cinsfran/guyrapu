# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de la conversación con el plugin Aitum Vertical Canvas, con un doble.

Sin ventanas y sin OBS real: el cliente falso devuelve las respuestas del
vendor y las de `GetCanvasList` como las devuelve OBS con el plugin
instalado.
"""

import unittest

from guyrapu.obs import lienzo_vertical, obs_cliente


LIENZO_VERTICAL = {
    "canvasName": "Aitum Vertical",
    "canvasUuid": "uuid-vertical",
    "canvasFlags": {"MAIN": False},
    "canvasVideoSettings": {"baseWidth": 1080, "baseHeight": 1920},
}
LIENZO_PRINCIPAL = {
    "canvasName": "Principal",
    "canvasUuid": "uuid-principal",
    "canvasFlags": {"MAIN": True},
    "canvasVideoSettings": {"baseWidth": 1920, "baseHeight": 1080},
}


class ClienteFalso:

    def __init__(self, canvases=None, vendor=True, respuestas=None):
        self.canvases = list(canvases or ())
        self.vendor = vendor
        self.respuestas = respuestas or {}
        self.llamadas = []
        self.vendor_llamadas = []

    def pedir(self, tipo, datos=None, parada=None):
        datos = datos or {}
        self.llamadas.append((tipo, dict(datos), parada))
        if tipo == "CallVendorRequest":
            self.vendor_llamadas.append(
                (datos.get("vendorName"), datos.get("requestType"),
                 dict(datos.get("requestData") or {})))
            if not self.vendor:
                raise obs_cliente.ObsError("vendor no registrado")
            pedido = datos.get("requestType")
            respuesta = self.respuestas.get(pedido, {"success": True})
            if callable(respuesta):
                respuesta = respuesta(datos)
            return {"responseData": {"responseData": dict(respuesta)}}
        if tipo == "GetCanvasList":
            return {"responseData": {"canvases": self.canvases}}
        return {"responseData": {}}


class DetectarTest(unittest.TestCase):

    def test_devuelve_el_lienzo_vertical_con_su_tamano(self):
        cliente = ClienteFalso(
            canvases=[LIENZO_PRINCIPAL, LIENZO_VERTICAL])
        lienzo = lienzo_vertical.detectar(cliente)
        self.assertEqual(lienzo["canvasUuid"], "uuid-vertical")
        self.assertEqual(lienzo["canvasName"], "Aitum Vertical")
        self.assertEqual(lienzo["ancho"], 1080)
        self.assertEqual(lienzo["alto"], 1920)

    def test_consulta_el_vendor_del_plugin(self):
        cliente = ClienteFalso(
            canvases=[LIENZO_PRINCIPAL, LIENZO_VERTICAL])
        lienzo_vertical.detectar(cliente)
        self.assertEqual(cliente.vendor_llamadas[0][0],
                         "aitum-vertical-canvas")
        self.assertEqual(cliente.vendor_llamadas[0][1], "version")

    def test_sin_el_vendor_devuelve_none_sin_lanzar(self):
        cliente = ClienteFalso(vendor=False)
        self.assertIsNone(lienzo_vertical.detectar(cliente))

    def test_sin_lienzo_vertical_devuelve_none(self):
        cliente = ClienteFalso(canvases=[LIENZO_PRINCIPAL])
        self.assertIsNone(lienzo_vertical.detectar(cliente))


class EstadoTest(unittest.TestCase):

    def test_lee_transmision_grabacion_y_bufer(self):
        cliente = ClienteFalso(respuestas={"status": {
            "success": True, "streaming": True, "recording": False,
            "backtrack": True}})
        self.assertEqual(
            lienzo_vertical.estado(cliente),
            {"transmitiendo": True, "grabando": False, "bufer": True})

    def test_pide_el_estado_al_vendor(self):
        cliente = ClienteFalso()
        lienzo_vertical.estado(cliente)
        self.assertEqual(cliente.vendor_llamadas,
                         [("aitum-vertical-canvas", "status", {})])


class AccionesTest(unittest.TestCase):

    def test_arranca_y_detiene(self):
        cliente = ClienteFalso()
        lienzo_vertical.arrancar(cliente)
        lienzo_vertical.detener(cliente)
        self.assertEqual(
            [pedido for _vendor, pedido, _datos in cliente.vendor_llamadas],
            ["start_streaming", "stop_streaming"])

    def test_arranca_y_detiene_la_grabacion(self):
        cliente = ClienteFalso()
        lienzo_vertical.arrancar_grabacion(cliente)
        lienzo_vertical.detener_grabacion(cliente)
        self.assertEqual(
            [pedido for _vendor, pedido, _datos in cliente.vendor_llamadas],
            ["start_recording", "stop_recording"])

    def test_apaga_el_bufer(self):
        cliente = ClienteFalso()
        lienzo_vertical.apagar_bufer(cliente)
        self.assertEqual(
            cliente.vendor_llamadas,
            [("aitum-vertical-canvas", "stop_backtrack", {})])

    def test_cambia_servidor_y_clave_por_posicion(self):
        cliente = ClienteFalso()
        lienzo_vertical.cambiar_servidor(cliente, 2, "rtmp://servidor")
        lienzo_vertical.cambiar_clave(cliente, 2, "clave-secreta")
        self.assertEqual(
            cliente.vendor_llamadas,
            [("aitum-vertical-canvas", "update_stream_server",
              {"stream_server": "rtmp://servidor", "index": 2}),
             ("aitum-vertical-canvas", "update_stream_key",
              {"stream_key": "clave-secreta", "index": 2})])

    def test_lee_y_cambia_la_escena_actual(self):
        cliente = ClienteFalso(respuestas={
            "current_scene": {"success": True, "scene": "Escena vertical"}})
        self.assertEqual(lienzo_vertical.escena_actual(cliente),
                         "Escena vertical")
        lienzo_vertical.cambiar_escena(cliente, "Otra escena")
        self.assertEqual(
            cliente.vendor_llamadas[-1],
            ("aitum-vertical-canvas", "switch_scene",
             {"scene": "Otra escena"}))

    def test_un_success_falso_lanza_obs_error(self):
        acciones = (
            lambda cliente: lienzo_vertical.estado(cliente),
            lambda cliente: lienzo_vertical.arrancar(cliente),
            lambda cliente: lienzo_vertical.detener(cliente),
            lambda cliente: lienzo_vertical.arrancar_grabacion(cliente),
            lambda cliente: lienzo_vertical.detener_grabacion(cliente),
            lambda cliente: lienzo_vertical.apagar_bufer(cliente),
            lambda cliente: lienzo_vertical.cambiar_servidor(
                cliente, 0, "rtmp://servidor"),
            lambda cliente: lienzo_vertical.cambiar_clave(cliente, 0, "clave"),
            lambda cliente: lienzo_vertical.escena_actual(cliente),
            lambda cliente: lienzo_vertical.cambiar_escena(cliente, "Escena"),
        )
        for accion in acciones:
            cliente = ClienteFalso(respuestas={
                "status": {"success": False},
                "start_streaming": {"success": False},
                "stop_streaming": {"success": False},
                "start_recording": {"success": False},
                "stop_recording": {"success": False},
                "stop_backtrack": {"success": False},
                "update_stream_server": {"success": False},
                "update_stream_key": {"success": False},
                "current_scene": {"success": False},
                "switch_scene": {"success": False},
            })
            with self.assertRaises(obs_cliente.ObsError):
                accion(cliente)


if __name__ == "__main__":
    unittest.main()
