# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""La categoría de uso que sale de las fichas reales de Piper, sin red."""

import unittest

from scripts import uso_voces


DANIELA = (
    "# Model card for es_AR-daniela-high\n\n## Dataset\n\n"
    "* URL: https://www.openslr.org/94/\n"
    "* License: Attribution-ShareAlike 4.0 International\n\n"
    "## Training\n\n"
    "Finetuned from U.S. English lessac voice (high quality).\n"
)
MLS = (
    "* License: CC BY 4.0\n\n## Training\n\n"
    "Finetuned from U.S. English Ryan voice (low quality).\n"
)
CLAUDE = (
    "* License: apache-2.0\n\n## Training\n\nSee URL above\n"
)
DAVEFX = (
    "* License: CC BY 4.0\n\n## Training\n\n"
    "Trained from scratch on train-clean-360.\n"
)


class TestUsoVoces(unittest.TestCase):

    def test_investigacion_por_entrenamiento_desde_lessac(self):
        self.assertEqual(uso_voces.uso("daniela", DANIELA),
                         uso_voces.INVESTIGACION)
        self.assertEqual(uso_voces.licencia("daniela", DANIELA),
                         "Attribution-ShareAlike 4.0 International")
        self.assertEqual(uso_voces.uso("lessac", DAVEFX),
                         uso_voces.INVESTIGACION)

    def test_no_comercial_por_base_ryan(self):
        self.assertEqual(uso_voces.uso("mls_10246", MLS),
                         uso_voces.NO_COMERCIAL)
        self.assertEqual(uso_voces.licencia("mls_10246", MLS), "CC BY 4.0")

    def test_sin_confirmar_por_entrenamiento_que_no_dice_la_base(self):
        self.assertEqual(uso_voces.uso("claude", CLAUDE),
                         uso_voces.SIN_CONFIRMAR)
        self.assertEqual(uso_voces.licencia("claude", CLAUDE), "apache-2.0")
        self.assertEqual(uso_voces.uso("amy", "* License: See URL\n"),
                         uso_voces.SIN_CONFIRMAR)
        self.assertEqual(uso_voces.uso("arctic", "* License: See LICENSE file\n"),
                         uso_voces.SIN_CONFIRMAR)
        self.assertEqual(uso_voces.licencia("sin_ficha", None), "Sin indicar")

    def test_libre_por_licencia_y_base_conocidas(self):
        self.assertEqual(uso_voces.uso("davefx", DAVEFX), uso_voces.LIBRE)

    def test_investigacion_manda_sobre_una_licencia_no_comercial(self):
        texto = ("* License: CC BY-NC-SA 4.0\n\n## Training\n\n"
                 "Finetuned from U.S. English lessac voice (high quality).\n")
        self.assertEqual(uso_voces.uso("voz", texto),
                         uso_voces.INVESTIGACION)


if __name__ == "__main__":
    unittest.main()
