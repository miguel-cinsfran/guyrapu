# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Cómo se cuenta lo que respondió a un envío de prueba."""

import unittest

from guyrapu.interaction import informe_ensayo


class TestRespondio(unittest.TestCase):

    def test_nombra_cada_respuesta_en_el_orden_de_la_interfaz(self):
        informe = informe_ensayo.InformeEnsayo()
        informe.meta("Suscriptores", 3, 10)
        informe.pregunta()
        informe.voto("Flores")
        informe.alerta("Regalo grande")
        informe.comando("hola")
        self.assertTrue(informe.respondio)
        self.assertEqual(
            informe.texto(),
            "Respondió el comando hola. Respondió la alerta Regalo grande. "
            "Voto contado en la encuesta Flores. "
            "Pregunta agregada a la página Preguntas. "
            "La meta Suscriptores avanzó a 3 de 10.")

    def test_varias_alertas_se_nombran_todas(self):
        informe = informe_ensayo.InformeEnsayo()
        informe.alerta("Regalo grande")
        informe.alerta("Nuevo seguidor")
        self.assertEqual(
            informe.texto(),
            "Respondió la alerta Regalo grande. "
            "Respondió la alerta Nuevo seguidor.")


class TestNoRespondio(unittest.TestCase):

    def test_cada_motivo_con_su_texto(self):
        casos = (
            ("ningún comando ni alerta usa ese mensaje.",
             "Nada respondió: ningún comando ni alerta usa ese mensaje."),
            ("el comando hola está en espera, faltan 4 segundos.",
             "Nada respondió: el comando hola está en espera, "
             "faltan 4 segundos."),
            ("el comando hola es solo para solo moderadores.",
             "Nada respondió: el comando hola es solo para solo moderadores."),
            ("el comando hola está en pausa.",
             "Nada respondió: el comando hola está en pausa."),
            ("los comandos están en pausa.",
             "Nada respondió: los comandos están en pausa."),
            ("ninguna alerta usa ese evento.",
             "Nada respondió: ninguna alerta usa ese evento."),
            ("la alerta Regalo grande está en espera, faltan 3 segundos.",
             "Nada respondió: la alerta Regalo grande está en espera, "
             "faltan 3 segundos."),
        )
        for motivo, esperado in casos:
            with self.subTest(motivo=motivo):
                informe = informe_ensayo.InformeEnsayo()
                informe.motivo(motivo)
                self.assertFalse(informe.respondio)
                self.assertEqual(informe.texto(), esperado)

    def test_el_general_lo_pone_quien_cierra_el_informe(self):
        informe = informe_ensayo.InformeEnsayo()
        informe.motivo("")
        self.assertEqual(
            informe.texto("ningún comando ni alerta usa ese mensaje."),
            "Nada respondió: ningún comando ni alerta usa ese mensaje.")


class TestFila(unittest.TestCase):

    def test_la_fila_lleva_hora_lo_enviado_y_resultado(self):
        self.assertEqual(
            informe_ensayo.fila("12:30:05", "hola", "Respondió el comando hola."),
            "12:30:05 hola: Respondió el comando hola.")


if __name__ == "__main__":
    unittest.main()
