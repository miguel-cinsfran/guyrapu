# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de los avisos que deja el guardado de Preferencias."""

import unittest

from guyrapu.core.avisos_preferencias import avisos_al_guardar

GUARDADO = "Preferencias guardadas."
FALLO = ("Las preferencias se aplicaron, pero no se pudieron guardar "
         "en el disco. Se perderán al cerrar la aplicación.")
MOTOR = "El motor elegido no está disponible, se conserva el anterior."
REGISTRO = ("El cambio del registro detallado se aplica al reiniciar "
            "la aplicación.")
PUERTO = ("El puerto del chat en el vídeo se aplica al desactivarlo y "
          "volver a activarlo desde el panel de transmisión.")


class TestAvisosAlGuardar(unittest.TestCase):

    def test_sin_novedades_avisa_que_se_guardaron(self):
        self.assertEqual(avisos_al_guardar(False, False, False, False),
                         [GUARDADO])

    def test_fallo_de_guardado_reemplaza_el_aviso(self):
        self.assertEqual(avisos_al_guardar(True, False, False, False), [FALLO])

    def test_motor_no_disponible(self):
        self.assertEqual(avisos_al_guardar(False, True, False, False),
                         [GUARDADO, MOTOR])

    def test_registro_detallado_cambiado(self):
        self.assertEqual(avisos_al_guardar(False, False, True, False),
                         [GUARDADO, REGISTRO])

    def test_puerto_cambiado_con_el_panel_activo(self):
        self.assertEqual(avisos_al_guardar(False, False, False, True),
                         [GUARDADO, PUERTO])

    def test_todos_a_la_vez_conservan_el_orden(self):
        self.assertEqual(avisos_al_guardar(True, True, True, True),
                         [FALLO, MOTOR, REGISTRO, PUERTO])


if __name__ == "__main__":
    unittest.main()
