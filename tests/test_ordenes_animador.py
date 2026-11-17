# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Las órdenes que el animador ejecuta para una tarjeta del vídeo."""

import unittest

from guyrapu.obs import escena_guyrapu, estilos_aviso, ordenes_animador

ANCHO = 1920
ALTO = 1080
ELEMENTO = 7


def _estilo(**cambios):
    base = dict(estilos_aviso.FABRICA[0], ms_entrada=350, ms_salida=250)
    base.update(cambios)
    return base


class TestOcultarAntes(unittest.TestCase):

    def test_deja_el_elemento_fuera_del_lienzo_y_sin_opacidad(self):
        orden = ordenes_animador.ocultar_antes(ELEMENTO, ANCHO)
        self.assertEqual(orden["escena"], escena_guyrapu.ESCENA)
        self.assertEqual(orden["elemento"], ELEMENTO)
        self.assertEqual(orden["fuente_filtro"], escena_guyrapu.TARJETA)
        self.assertEqual(orden["filtro"], escena_guyrapu.OPACIDAD)
        self.assertEqual((orden["x"], orden["y"]), (0, 0))
        self.assertEqual(orden["cuadros"], [[0, ANCHO * 10, 0.0, 0.0]])


class TestEntrada(unittest.TestCase):

    def _orden(self, movimiento):
        return ordenes_animador.entrada(
            ELEMENTO, _estilo(entrada=movimiento), ANCHO, ALTO)

    def test_lleva_la_escena_el_elemento_y_el_filtro(self):
        orden = self._orden("fundido")
        self.assertEqual(orden["escena"], escena_guyrapu.ESCENA)
        self.assertEqual(orden["elemento"], ELEMENTO)
        self.assertEqual(orden["fuente_filtro"], escena_guyrapu.TARJETA)
        self.assertEqual(orden["filtro"], escena_guyrapu.OPACIDAD)
        self.assertEqual((orden["x"], orden["y"]), (0, 0))

    def test_el_desplazamiento_de_cada_movimiento_sale_del_lienzo(self):
        esperados = {
            "derecha": 1920.0,
            "izquierda": -1920.0,
            "arriba": -1080.0,
            "abajo": 1080.0,
            "suave": 43.2,
            "fundido": 0.0,
        }
        for movimiento, desplazamiento in esperados.items():
            with self.subTest(movimiento=movimiento):
                orden = self._orden(movimiento)
                cuadro = orden["cuadros"][0]
                if movimiento == "arriba":
                    self.assertEqual((cuadro[1], cuadro[2]),
                                     (0.0, desplazamiento))
                elif movimiento == "abajo":
                    self.assertEqual((cuadro[1], cuadro[2]),
                                     (0.0, desplazamiento))
                elif movimiento == "suave":
                    self.assertEqual(cuadro[1], 0.0)
                    self.assertAlmostEqual(cuadro[2], desplazamiento)
                else:
                    self.assertEqual(cuadro[1], desplazamiento)

    def test_usa_el_movimiento_y_los_milisegundos_del_estilo(self):
        orden = self._orden("derecha")
        self.assertEqual(orden["cuadros"][0][0], 0)
        self.assertEqual(orden["cuadros"][-1][0], 350)
        self.assertEqual(orden["cuadros"][-1][1:], [0.0, 0.0, 1.0])


class TestSalida(unittest.TestCase):

    def _orden(self, movimiento):
        return ordenes_animador.salida(
            ELEMENTO, _estilo(salida=movimiento), ANCHO, ALTO)

    def test_empieza_visible_y_termina_corrida(self):
        orden = self._orden("derecha")
        self.assertEqual(orden["cuadros"][0],
                         [0, 0.0, 0.0, 1.0])
        self.assertEqual(orden["cuadros"][-1],
                         [250, 1920.0, 0.0, 1.0])

    def test_el_desplazamiento_de_cada_movimiento_sale_del_lienzo(self):
        esperados = {
            "derecha": (1920.0, 0.0),
            "izquierda": (-1920.0, 0.0),
            "arriba": (0.0, -1080.0),
            "abajo": (0.0, 1080.0),
            "suave": (0.0, 43.2),
            "fundido": (0.0, 0.0),
        }
        for movimiento, (dx, dy) in esperados.items():
            with self.subTest(movimiento=movimiento):
                ultimo = self._orden(movimiento)["cuadros"][-1]
                self.assertEqual(ultimo[0], 250)
                self.assertAlmostEqual(ultimo[1], dx)
                self.assertAlmostEqual(ultimo[2], dy)

    def test_los_que_desvanecen_terminan_sin_opacidad(self):
        for movimiento in ("fundido", "suave"):
            with self.subTest(movimiento=movimiento):
                self.assertEqual(self._orden(movimiento)["cuadros"][-1][3],
                                 0.0)

    def test_ninguna_da_un_solo_cuadro_sin_moverse(self):
        orden = self._orden("ninguna")
        self.assertEqual(orden["cuadros"], [[0, 0.0, 0.0, 1.0]])


if __name__ == "__main__":
    unittest.main()
