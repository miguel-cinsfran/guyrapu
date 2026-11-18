# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""La elección de estilo de un cuadro: opciones, claves e índices."""

import unittest

from guyrapu.interaction import estilo_elegido
from guyrapu.obs import estilos_aviso


class TestOpciones(unittest.TestCase):

    def test_empiezan_por_el_predeterminado_y_siguen_los_estilos(self):
        self.assertEqual(
            estilo_elegido.opciones([], {"comando": "banda"}, "comando"),
            ["Predeterminado (Banda)", "Clásico", "Banda", "Tarjeta",
             "Alto contraste"])

    def test_sin_predeterminado_dicen_clasico(self):
        self.assertEqual(
            estilo_elegido.opciones([], {}, "mensaje")[0],
            "Predeterminado (Clásico)")


class TestClavesEIndices(unittest.TestCase):

    def setUp(self):
        self.estilos = estilos_aviso.todos([])

    def test_el_indice_cero_da_el_estilo_vacio(self):
        self.assertEqual(estilo_elegido.clave_de(0, self.estilos), "")

    def test_una_clave_da_su_indice_y_vuelve(self):
        self.assertEqual(estilo_elegido.clave_de(2, self.estilos), "banda")
        self.assertEqual(estilo_elegido.indice_de("banda", self.estilos), 2)

    def test_una_clave_que_no_esta_da_el_indice_cero(self):
        self.assertEqual(estilo_elegido.indice_de("", self.estilos), 0)
        self.assertEqual(
            estilo_elegido.indice_de("no_existe", self.estilos), 0)


if __name__ == "__main__":
    unittest.main()
