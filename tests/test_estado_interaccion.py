# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Qué dice el estado de la interacción del directo al pedirlo."""

import unittest

from guyrapu.interaction import estado_interaccion


class TestTextoEstadoInteraccion(unittest.TestCase):

    def test_orden_p2_y_salta_lo_vacio(self):
        texto = estado_interaccion.texto(
            "Encuesta en curso: ¿A o B?. Opciones: A, B", "", "Meta: M, 1 de 2",
            "En el vídeo: Aviso.", 3)
        self.assertEqual(
            texto,
            "Encuesta en curso: ¿A o B?. Opciones: A, B; Meta: M, 1 de 2; "
            "En el vídeo: Aviso; Esperan 3 preguntas.")

    def test_preguntas_en_singular(self):
        texto = estado_interaccion.texto("", "", "", "", 1)
        self.assertEqual(texto, "Espera 1 pregunta.")

    def test_cero_preguntas_no_agrega_frase(self):
        texto = estado_interaccion.texto("Encuesta en curso: X", "", "", "", 0)
        self.assertEqual(texto, "Encuesta en curso: X.")

    def test_sin_nada_dice_p3(self):
        texto = estado_interaccion.texto("", "", "", "", 0)
        self.assertEqual(texto, "No hay nada de la interacción en curso.")


if __name__ == "__main__":
    unittest.main()
