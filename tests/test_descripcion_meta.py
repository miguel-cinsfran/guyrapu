# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de la fila de la lista y de la frase de Escuchar de una meta."""

import unittest

from guyrapu.interaction import descripcion_meta, metas


def _meta(**cambios):
    datos = {"nombre": "Viaje", "que_cuenta": "me_gusta", "objetivo": 100}
    datos.update(cambios)
    return metas.Meta(**datos)


class TestFila(unittest.TestCase):

    def test_dice_el_nombre_lo_que_cuenta_y_el_objetivo(self):
        self.assertEqual(
            descripcion_meta.fila(_meta()),
            "Viaje, Me gusta, objetivo 100")

    def test_marca_las_pausadas(self):
        self.assertEqual(
            descripcion_meta.fila(_meta(activa=False)),
            "Viaje, Me gusta, objetivo 100, en pausa")

    def test_que_cuenta_usa_el_nombre_visible_de_cada_clave(self):
        for clave, nombre in metas.NOMBRES_QUE_CUENTA.items():
            with self.subTest(clave=clave):
                self.assertEqual(
                    descripcion_meta.fila(
                        _meta(que_cuenta=clave, objetivo=5)),
                    f"Viaje, {nombre}, objetivo 5")


class TestEscuchar(unittest.TestCase):

    def test_cuenta_la_meta_con_su_estilo(self):
        self.assertEqual(
            descripcion_meta.escuchar(_meta(), "Clásico"),
            "Viaje: Me gusta, objetivo 100, estilo Clásico.")

    def test_agrega_el_festejo_si_lo_tiene(self):
        self.assertEqual(
            descripcion_meta.escuchar(
                _meta(festejo="aplauso.gif"), "Banda"),
            "Viaje: Me gusta, objetivo 100, estilo Banda. "
            "Festejo: aplauso.gif.")

    def test_marca_las_pausadas_al_final(self):
        self.assertEqual(
            descripcion_meta.escuchar(
                _meta(festejo="aplauso.gif", activa=False), "Clásico"),
            "Viaje: Me gusta, objetivo 100, estilo Clásico. "
            "Festejo: aplauso.gif. En pausa.")


if __name__ == "__main__":
    unittest.main()
