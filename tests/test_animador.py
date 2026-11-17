# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas del animador de OBS: los cuadros y el proceso que los reproduce."""

import unittest

from guyrapu.obs import animador, obs_cliente


class RelojFalso:
    """Un reloj que avanza al dormir, con un atraso opcional por espera."""

    def __init__(self, atraso=0.0):
        self.ahora = 0.0
        self.atraso = atraso

    def reloj(self):
        return self.ahora

    def dormir(self, segundos):
        self.ahora += segundos + self.atraso


class ClienteFalso:
    """Un cliente de OBS que anota cada pedido y puede fallar a pedido."""

    def __init__(self, reloj=None, falla_conectar=False, falla_pedir=False):
        self.reloj = reloj
        self.falla_conectar = falla_conectar
        self.falla_pedir = falla_pedir
        self.pedidos = []
        self.cerrado = False

    def conectar(self):
        if self.falla_conectar:
            raise obs_cliente.ObsError("sin OBS")

    def pedir(self, tipo, datos=None, parada=None):
        if self.falla_pedir:
            raise obs_cliente.ObsError("OBS falló")
        self.pedidos.append((self.reloj.ahora if self.reloj else None,
                             tipo, datos))
        return {}

    def cerrar(self):
        self.cerrado = True


class ConexionFalsa:
    """El canal con la app: entrega las órdenes y anota las respuestas."""

    def __init__(self, ordenes):
        self.ordenes = list(ordenes)
        self.enviadas = []

    def recv(self):
        if not self.ordenes:
            raise EOFError
        return self.ordenes.pop(0)

    def send(self, respuesta):
        self.enviadas.append(respuesta)


def _orden(cuadros):
    return {
        "tipo": "animar",
        "escena": "Escena",
        "elemento": 7,
        "fuente_filtro": "Texto",
        "filtro": "Corrección",
        "x": 100.0,
        "y": 200.0,
        "cuadros": [list(cuadro) for cuadro in cuadros],
    }


class TestReproducir(unittest.TestCase):

    def test_manda_cada_valor_en_su_instante_y_no_repite(self):
        reloj = RelojFalso()
        cliente = ClienteFalso(reloj)
        orden = _orden([[0, 0, 0, 1.0],
                        [17, 10, 0, 1.0],
                        [34, 10, 0, 0.5]])

        animador.reproducir(cliente, orden, reloj=reloj.reloj,
                            dormir=reloj.dormir)

        self.assertEqual(
            [pedido[1] for pedido in cliente.pedidos],
            ["SetSceneItemTransform", "SetSourceFilterSettings",
             "SetSceneItemTransform", "SetSourceFilterSettings"])
        for instante, esperado in zip(
                [pedido[0] for pedido in cliente.pedidos],
                [0.0, 0.0, 0.017, 0.034]):
            self.assertAlmostEqual(instante, esperado)
        self.assertEqual(cliente.pedidos[0][2], {
            "sceneName": "Escena", "sceneItemId": 7,
            "sceneItemTransform": {"positionX": 100.0, "positionY": 200.0}})
        self.assertEqual(cliente.pedidos[1][2], {
            "sourceName": "Texto", "filterName": "Corrección",
            "filterSettings": {"opacity": 1.0}})
        self.assertEqual(cliente.pedidos[2][2], {
            "sceneName": "Escena", "sceneItemId": 7,
            "sceneItemTransform": {"positionX": 110.0, "positionY": 200.0}})
        self.assertEqual(cliente.pedidos[3][2], {
            "sourceName": "Texto", "filterName": "Corrección",
            "filterSettings": {"opacity": 0.5}})

    def test_salta_los_vencidos_y_manda_el_ultimo(self):
        reloj = RelojFalso(atraso=0.050)
        cliente = ClienteFalso(reloj)
        orden = _orden([[0, 0, 0, 1.0],
                        [17, 17, 0, 1.0],
                        [34, 34, 0, 1.0],
                        [50, 50, 0, 1.0],
                        [67, 67, 0, 1.0],
                        [83, 83, 0, 1.0],
                        [100, 100, 0, 1.0]])

        animador.reproducir(cliente, orden, reloj=reloj.reloj,
                            dormir=reloj.dormir)

        posiciones = [
            pedido[2]["sceneItemTransform"]["positionX"]
            for pedido in cliente.pedidos
            if pedido[1] == "SetSceneItemTransform"]
        self.assertEqual(posiciones, [100.0, 167.0, 200.0])


class TestAtender(unittest.TestCase):

    def test_eco_contesta_sin_hablar_con_obs(self):
        conexion = ConexionFalsa([{"tipo": "eco"}])
        fabricados = []

        def fabricar():
            fabricados.append(True)
            return ClienteFalso()

        animador.atender(conexion, cliente_fn=fabricar)

        self.assertEqual(conexion.enviadas, [{"ok": True}])
        self.assertEqual(fabricados, [])

    def test_si_no_conecta_contesta_error_y_la_siguiente_reintenta(self):
        orden = _orden([[0, 0, 0, 1.0]])
        conexion = ConexionFalsa([orden, orden])
        primero = ClienteFalso(falla_conectar=True)
        segundo = ClienteFalso()
        fabricados = [primero, segundo]

        animador.atender(conexion, cliente_fn=lambda: fabricados.pop(0))

        self.assertEqual([respuesta["ok"] for respuesta in conexion.enviadas],
                         [False, True])
        self.assertTrue(primero.cerrado)
        self.assertEqual([pedido[1] for pedido in segundo.pedidos],
                         ["SetSceneItemTransform", "SetSourceFilterSettings"])

    def test_si_obs_falla_a_mitad_la_siguiente_reintenta(self):
        orden = _orden([[0, 0, 0, 1.0]])
        conexion = ConexionFalsa([orden, orden])
        primero = ClienteFalso(falla_pedir=True)
        segundo = ClienteFalso()
        fabricados = [primero, segundo]

        animador.atender(conexion, cliente_fn=lambda: fabricados.pop(0))

        self.assertEqual([respuesta["ok"] for respuesta in conexion.enviadas],
                         [False, True])
        self.assertTrue(primero.cerrado)
        self.assertEqual([pedido[1] for pedido in segundo.pedidos],
                         ["SetSceneItemTransform", "SetSourceFilterSettings"])


class TestFronteraReal(unittest.TestCase):

    def setUp(self):
        self.animador = animador.Animador()

    def tearDown(self):
        self.animador.cerrar()

    def test_eco_por_el_proceso_real_y_cierre(self):
        self.assertTrue(self.animador.animar({"tipo": "eco"}, 120))
        proceso = self.animador._proceso
        self.assertIsNotNone(proceso)
        self.assertIsNone(proceso.poll())

        self.animador.cerrar()

        self.assertIsNotNone(proceso.poll())

    def test_si_el_proceso_muere_la_orden_siguiente_lo_arranca(self):
        self.assertTrue(self.animador.animar({"tipo": "eco"}, 120))
        primero = self.animador._proceso
        pid = primero.pid
        primero.kill()
        primero.wait(timeout=10)

        self.assertTrue(self.animador.animar({"tipo": "eco"}, 120))
        segundo = self.animador._proceso
        self.assertNotEqual(segundo.pid, pid)
        self.assertIsNone(segundo.poll())


if __name__ == "__main__":
    unittest.main()
