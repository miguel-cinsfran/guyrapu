# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas del formato de las transcripciones del carril de la aplicación.

Se arman recorridos a mano, con las mismas claves que deja `recorrido.py`, y
se comprueba que el texto no dependa de horas, hwnd ni pid, que el diff nombre
la línea que cambió y que aprobar deje la nueva como aprobada.
"""

import tempfile
import unittest
from pathlib import Path

from qa.nvda import transcripcion


def datos(nombre="Categorías", pid=10, hwnd=1, hora=1.0, ms=120):
    return {
        "ventana": "preferencias",
        "pid": pid,
        "primero": {},
        "pasos": [
            {
                "tecla": "tab",
                "fase": "ida",
                "habla": [{"tipo": "habla", "texto": "Categorías",
                           "hora": hora}],
                "foco": {
                    "nombre": nombre,
                    "rol_nombre": "LIST",
                    "estados": ["focusable", "focused"],
                    "valor": "General",
                    "atajo": "Alt+C",
                    "hwnd": hwnd,
                    "pid": pid,
                },
                "agotado": False,
                "ms_habla": ms,
            },
        ],
    }


class TestFormato(unittest.TestCase):

    def test_la_linea_lleva_tecla_fase_habla_y_los_datos_del_foco(self):
        texto = transcripcion.texto(datos())
        self.assertIn("tab", texto)
        self.assertIn("ida", texto)
        self.assertIn("Categorías", texto)
        self.assertIn("LIST", texto)
        self.assertIn("focused", texto)
        self.assertIn("General", texto)
        self.assertIn("Alt+C", texto)

    def test_dos_recorridos_iguales_salvo_horas_hwnd_y_pid_dan_el_mismo_texto(
            self):
        uno = datos(pid=10, hwnd=1, hora=1.0, ms=120)
        otro = datos(pid=99, hwnd=77, hora=8.5, ms=950)
        self.assertEqual(transcripcion.texto(uno), transcripcion.texto(otro))
        self.assertNotIn("77", transcripcion.texto(otro))
        self.assertNotIn("99", transcripcion.texto(otro))

    def test_el_nombre_del_foco_repetido_al_final_se_escribe_una_vez(self):
        simple = datos("No hay palabras.")
        simple["pasos"][0]["habla"] = [{"texto": "No hay palabras."}]
        doble = datos("No hay palabras.")
        doble["pasos"][0]["habla"] = [
            {"texto": "No hay palabras. No hay palabras."}]
        self.assertEqual(transcripcion.texto(doble),
                         transcripcion.texto(simple))

    def test_otra_repeticion_que_no_es_el_nombre_del_foco_no_se_toca(self):
        caso = datos("Lista")
        caso["pasos"][0]["habla"] = [
            {"texto": "No hay palabras. No hay palabras."}]
        self.assertIn("dijo='No hay palabras. No hay palabras.'",
                      transcripcion.texto(caso))

    def test_el_nombre_con_la_posicion_repetido_al_final_se_escribe_una_vez(
            self):
        simple = datos("Comandos")
        simple["pasos"][0]["habla"] = [
            {"texto": "Páginas de interacción lista Comandos 2 de 8"}]
        doble = datos("Comandos")
        doble["pasos"][0]["habla"] = [
            {"texto": "Páginas de interacción lista Comandos 2 de 8 "
                      "Comandos 2 de 8"}]
        self.assertEqual(transcripcion.texto(doble),
                         transcripcion.texto(simple))

    def test_dos_entradas_distintas_al_final_no_se_tocan(self):
        caso = datos("Comandos")
        caso["pasos"][0]["habla"] = [
            {"texto": "Comandos 2 de 8 Encuestas 3 de 8"}]
        self.assertIn("dijo='Comandos 2 de 8 Encuestas 3 de 8'",
                      transcripcion.texto(caso))


class TestComparacion(unittest.TestCase):

    def test_un_nombre_distinto_da_un_diff_con_su_linea(self):
        viejo = transcripcion.texto(datos("Categorías"))
        nuevo = transcripcion.texto(datos("Categorías de preferencias"))
        diferencia = transcripcion.diferencia(viejo, nuevo)
        self.assertIn("Categorías de preferencias", diferencia)
        self.assertTrue(any(linea.startswith("+")
                            for linea in diferencia.splitlines()))

    def test_aprobar_deja_la_nueva_como_aprobada(self):
        with tempfile.TemporaryDirectory() as base:
            carpeta = Path(base)
            transcripcion.escribir("preferencias", "vieja\n", carpeta)
            diferencia = transcripcion.comparar("preferencias", "nueva\n",
                                                carpeta=carpeta)
            self.assertIn("nueva", diferencia)
            self.assertEqual(
                transcripcion.leer("preferencias", carpeta), "vieja\n")
            self.assertEqual(
                transcripcion.comparar("preferencias", "nueva\n",
                                       aprobar=True, carpeta=carpeta),
                "")
            self.assertEqual(
                transcripcion.leer("preferencias", carpeta), "nueva\n")


if __name__ == "__main__":
    unittest.main()
