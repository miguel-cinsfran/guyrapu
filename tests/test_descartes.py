# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
import unittest

from guyrapu.capture import descartes


class TestAviso(unittest.TestCase):

    def test_no_avisa_antes_del_umbral(self):
        self.assertFalse(descartes.hay_que_avisar(2, False))

    def test_avisa_al_llegar_al_umbral(self):
        self.assertTrue(descartes.hay_que_avisar(3, False))

    def test_no_avisa_dos_veces_en_la_misma_sesion(self):
        self.assertFalse(descartes.hay_que_avisar(10, True))

    def test_acepta_un_umbral_distinto(self):
        self.assertTrue(descartes.hay_que_avisar(2, False, umbral=2))


class TestFrases(unittest.TestCase):

    def test_aviso_explica_donde_estan_y_como_seguir_el_ritmo(self):
        texto = descartes.frase_aviso()
        self.assertEqual(
            texto,
            "La lectura va con retraso y se están descartando mensajes. "
            "Están en la lista del chat. Para seguir el ritmo, sube la "
            "velocidad de la voz con F10.")
        self.assertNotIn("Preferencias", texto)
        self.assertNotIn("nombre", texto)

    def test_estado_vacio_si_no_hubo_descartes(self):
        self.assertEqual(descartes.frase_estado(0), "")

    def test_estado_muestra_el_numero_de_descartes(self):
        self.assertEqual(descartes.frase_estado(12), "Mensajes descartados: 12")


if __name__ == "__main__":
    unittest.main()
