# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""La frase que describe una tarjeta armada, sin OBS ni ventanas."""

import unittest

from guyrapu.obs import estilos_aviso, revision_tarjeta
from guyrapu.obs.escena_guyrapu import Tarjeta


def _estilo(**cambios):
    base = dict(estilos_aviso.FABRICA[2], zona="abajo_centro")
    base.update(cambios)
    return base


def _tarjeta(x=600, y=700, ancho=400, alto=100, aviso_fuente=""):
    return Tarjeta(x, y, ancho, alto, "", aviso_fuente)


class TestRevisionTarjeta(unittest.TestCase):

    def test_p4_una_tarjeta_centrada_abajo_da_su_zona_y_sus_por_cientos(self):
        frase = revision_tarjeta.revisar(
            _tarjeta(), 1600, 900, _estilo(zona="automatica"))
        self.assertEqual(
            frase,
            "Zona: Abajo al centro. Ocupa el 25 por ciento del ancho y el 11 "
            "por ciento del alto del vídeo.")

    def test_p4_una_tarjeta_que_pasa_del_80_central_da_el_aviso(self):
        frase = revision_tarjeta.revisar(
            _tarjeta(x=100), 1600, 900, _estilo())
        self.assertIn(
            "La tarjeta queda fuera del 80 por ciento central del vídeo.", frase)
        self.assertTrue(frase.endswith(
            "La tarjeta queda fuera del 80 por ciento central del vídeo."))

    def test_p4_la_fuente_y_el_contraste_salen_despues_en_ese_orden(self):
        estilo = _estilo(color_texto="#FFFF00", color_fondo="#FFFFFF",
                         opacidad_fondo=100, ancho_contorno=0)
        aviso_fuente = "La fuente No Existe no está instalada. Se usa Segoe UI."
        frase = revision_tarjeta.revisar(
            _tarjeta(aviso_fuente=aviso_fuente), 1600, 900, estilo)
        contraste = estilos_aviso.aviso_contraste(estilo)
        self.assertTrue(contraste)
        self.assertLess(frase.index("Zona:"), frase.index("Ocupa el"))
        self.assertLess(frase.index("Ocupa el"), frase.index(aviso_fuente))
        self.assertLess(frase.index(aviso_fuente), frase.index(contraste))
        self.assertTrue(frase.endswith(contraste))


if __name__ == "__main__":
    unittest.main()
