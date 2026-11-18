# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de los pasos para sincronizar una lista de claves, sin wx."""

import unittest

from guyrapu.core import pasos_lista


def _aplicar(claves, pasos):
    actual = list(claves)
    for paso in pasos:
        if paso[0] == "borrar":
            del actual[paso[1]]
        else:
            actual.insert(paso[1], paso[2])
    return actual


class TestPasos(unittest.TestCase):

    def test_lista_igual_no_da_pasos(self):
        self.assertEqual(pasos_lista.pasos_para_sincronizar(["a", "b"], ["a", "b"]), [])

    def test_aplicar_da_la_lista_deseada(self):
        casos = [
            ([], []),
            ([], ["a"]),
            (["a"], []),
            (["a", "b", "c"], ["a", "b", "c"]),
            (["a", "b", "c"], ["c", "b", "a"]),
            (["a", "b", "c"], ["b"]),
            (["b"], ["a", "b", "c"]),
            (["a", "b"], ["b", "a", "c"]),
            (["a", "b", "c", "d"], ["b", "d", "e"]),
            (["x", "y"], ["y", "x", "z", "w"]),
        ]
        for actuales, deseadas in casos:
            with self.subTest(actuales=actuales, deseadas=deseadas):
                pasos = pasos_lista.pasos_para_sincronizar(actuales, deseadas)
                self.assertEqual(_aplicar(actuales, pasos), deseadas)
                if actuales == deseadas:
                    self.assertEqual(pasos, [])


if __name__ == "__main__":
    unittest.main()
