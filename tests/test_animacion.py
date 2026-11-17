# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
import math
import unittest

from guyrapu.interaction import animacion

DURACIONES = (100, 350, 1000)


def _desplazamiento(movimiento):
    return animacion.desplazamiento(
        movimiento, 300, 500, 400, 100, 1920, 1080)


def _instantes(cuadros):
    return [cuadro.ms for cuadro in cuadros]


class TestListas(unittest.TestCase):
    def test_entradas_en_orden(self):
        self.assertEqual(
            [clave for clave, _nombre in animacion.ENTRADAS],
            ["suave", "fundido", "derecha", "izquierda", "arriba", "abajo",
             "ninguna"])
        self.assertEqual(
            [nombre for _clave, nombre in animacion.ENTRADAS],
            ["Fundido al subir", "Fundido", "Desde la derecha",
             "Desde la izquierda", "Desde arriba", "Desde abajo", "Ninguna"])

    def test_salidas_en_orden(self):
        self.assertEqual(
            [clave for clave, _nombre in animacion.SALIDAS],
            ["fundido", "suave", "derecha", "izquierda", "arriba", "abajo",
             "ninguna"])
        self.assertEqual(
            [nombre for _clave, nombre in animacion.SALIDAS],
            ["Fundido", "Fundido al bajar", "Hacia la derecha",
             "Hacia la izquierda", "Hacia arriba", "Hacia abajo", "Ninguna"])


class TestDesplazamiento(unittest.TestCase):
    def test_derecha_apoya_el_borde_izquierdo_en_el_derecho_del_lienzo(self):
        self.assertEqual(_desplazamiento("derecha"), (1620, 0.0))

    def test_izquierda_apoya_el_borde_derecho_en_el_izquierdo_del_lienzo(self):
        self.assertEqual(_desplazamiento("izquierda"), (-700, 0.0))

    def test_arriba_apoya_el_borde_inferior_en_el_superior_del_lienzo(self):
        self.assertEqual(_desplazamiento("arriba"), (0.0, -600))

    def test_abajo_apoya_el_borde_superior_en_el_inferior_del_lienzo(self):
        self.assertEqual(_desplazamiento("abajo"), (0.0, 580))

    def test_suave_baja_el_cuatro_por_ciento_del_lado_menor(self):
        dx, dy = _desplazamiento("suave")
        self.assertEqual(dx, 0.0)
        self.assertAlmostEqual(dy, 43.2)

    def test_fundido_y_ninguna_no_corren(self):
        for movimiento in ("fundido", "ninguna"):
            with self.subTest(movimiento=movimiento):
                self.assertEqual(_desplazamiento(movimiento), (0.0, 0.0))


class TestCuadros(unittest.TestCase):
    def test_los_instantes_van_a_sesenta_por_segundo(self):
        self.assertEqual(
            _instantes(animacion.cuadros_entrada("fundido", 100, 0, 0)),
            [0, 17, 33, 50, 67, 83, 100])

    def test_el_penultimo_que_cae_en_la_duracion_sobra(self):
        self.assertEqual(
            _instantes(animacion.cuadros_entrada("fundido", 117, 0, 0)),
            [0, 17, 33, 50, 67, 83, 100, 117])

    def test_la_entrada_empieza_en_el_estado_inicial(self):
        dx, dy = _desplazamiento("derecha")
        primero = animacion.cuadros_entrada("derecha", 350, dx, dy)[0]
        self.assertEqual(
            (primero.ms, primero.dx, primero.dy, primero.opacidad),
            (0, dx, dy, 1.0))
        primero = animacion.cuadros_entrada("fundido", 350, 0, 0)[0]
        self.assertEqual(
            (primero.ms, primero.dx, primero.dy, primero.opacidad),
            (0, 0, 0, 0.0))
        dx, dy = _desplazamiento("suave")
        primero = animacion.cuadros_entrada("suave", 350, dx, dy)[0]
        self.assertEqual(
            (primero.ms, primero.dx, primero.dy, primero.opacidad),
            (0, dx, dy, 0.0))

    def test_la_entrada_termina_en_el_estado_final(self):
        for movimiento in ("suave", "fundido", "derecha", "izquierda",
                           "arriba", "abajo"):
            with self.subTest(movimiento=movimiento):
                dx, dy = _desplazamiento(movimiento)
                ultimo = animacion.cuadros_entrada(
                    movimiento, 350, dx, dy)[-1]
                self.assertEqual(ultimo.ms, 350)
                self.assertEqual((ultimo.dx, ultimo.dy), (0, 0))
                self.assertEqual(ultimo.opacidad, 1.0)

    def test_la_salida_empieza_visible(self):
        for movimiento in ("suave", "fundido", "derecha", "izquierda",
                           "arriba", "abajo"):
            with self.subTest(movimiento=movimiento):
                dx, dy = _desplazamiento(movimiento)
                primero = animacion.cuadros_salida(
                    movimiento, 250, dx, dy)[0]
                self.assertEqual(
                    (primero.ms, primero.dx, primero.dy, primero.opacidad),
                    (0, 0, 0, 1.0))

    def test_la_salida_termina_en_el_estado_final(self):
        for movimiento in ("suave", "fundido", "derecha", "izquierda",
                           "arriba", "abajo"):
            with self.subTest(movimiento=movimiento):
                dx, dy = _desplazamiento(movimiento)
                ultimo = animacion.cuadros_salida(
                    movimiento, 250, dx, dy)[-1]
                self.assertEqual(ultimo.ms, 250)
                self.assertEqual((ultimo.dx, ultimo.dy), (dx, dy))
                opacidad = 0.0 if movimiento in ("suave", "fundido") else 1.0
                self.assertEqual(ultimo.opacidad, opacidad)

    def test_ninguna_da_un_solo_cuadro_con_el_estado_final(self):
        for funcion in (animacion.cuadros_entrada, animacion.cuadros_salida):
            with self.subTest(funcion=funcion.__name__):
                cuadros = funcion("ninguna", 350, 0, 0)
                self.assertEqual(len(cuadros), 1)
                self.assertEqual(
                    (cuadros[0].ms, cuadros[0].dx, cuadros[0].dy,
                     cuadros[0].opacidad),
                    (0, 0, 0, 1.0))

    def test_la_entrada_frena_y_la_salida_acelera(self):
        entrada = animacion.cuadros_entrada("derecha", 1000, 1000, 0)
        medio = min(entrada, key=lambda cuadro: abs(cuadro.ms - 500))
        self.assertLess(medio.dx, 500)
        fundido = animacion.cuadros_entrada("fundido", 1000, 0, 0)
        medio = min(fundido, key=lambda cuadro: abs(cuadro.ms - 500))
        self.assertGreater(medio.opacidad, 0.5)

        salida = animacion.cuadros_salida("derecha", 1000, 1000, 0)
        medio = min(salida, key=lambda cuadro: abs(cuadro.ms - 500))
        self.assertLess(medio.dx, 500)
        fundido = animacion.cuadros_salida("fundido", 1000, 0, 0)
        medio = min(fundido, key=lambda cuadro: abs(cuadro.ms - 500))
        self.assertGreater(medio.opacidad, 0.5)


class TestPropiedad(unittest.TestCase):
    def _revisar(self, cuadros, dx_final, dy_final, opacidad_final):
        for anterior, siguiente in zip(cuadros, cuadros[1:]):
            self.assertLess(anterior.ms, siguiente.ms)
            distancia_previa = math.hypot(
                anterior.dx - dx_final, anterior.dy - dy_final)
            distancia = math.hypot(
                siguiente.dx - dx_final, siguiente.dy - dy_final)
            self.assertLessEqual(distancia, distancia_previa + 1e-9)
            self.assertLessEqual(
                abs(siguiente.opacidad - opacidad_final),
                abs(anterior.opacidad - opacidad_final) + 1e-9)

    def test_en_toda_entrada(self):
        for movimiento, _nombre in animacion.ENTRADAS:
            for duracion in DURACIONES:
                with self.subTest(movimiento=movimiento, duracion=duracion):
                    dx, dy = _desplazamiento(movimiento)
                    self._revisar(
                        animacion.cuadros_entrada(
                            movimiento, duracion, dx, dy),
                        0.0, 0.0, 1.0)

    def test_en_toda_salida(self):
        for movimiento, _nombre in animacion.SALIDAS:
            for duracion in DURACIONES:
                with self.subTest(movimiento=movimiento, duracion=duracion):
                    dx, dy = _desplazamiento(movimiento)
                    opacidad = (0.0 if movimiento in ("suave", "fundido")
                                else 1.0)
                    self._revisar(
                        animacion.cuadros_salida(
                            movimiento, duracion, dx, dy),
                        dx, dy, opacidad)


if __name__ == "__main__":
    unittest.main()
