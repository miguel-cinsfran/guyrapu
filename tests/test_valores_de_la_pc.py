# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de los valores que cambian por PC y del marcador que los sustituye.

Las distribuciones y las voces se cambian a mano para comprobar que lo que se
escribe no dependa del teclado ni de las voces instaladas en la PC que corre.
"""

import unittest
from pathlib import Path
from unittest import mock

from guyrapu.core import tecla_fisica
from guyrapu.voice import motores
from qa import valores_de_la_pc
from qa.nvda import transcripcion
from tests.test_qa_nvda_transcripcion import datos


def distribucion(c0c, c0d):
    def texto_tecla(exploracion, api=None):
        return {0x0c: c0c, 0x0d: c0d}.get(exploracion, "")
    return texto_tecla


def caso_de_tecla(caracter, nombre="Filtro siguiente del chat"):
    caso = datos(nombre)
    caso["pasos"][0]["habla"] = [{"texto":
        f"{nombre}: Ctrl+Mayús+{caracter} (fija)"}]
    caso["pasos"][0]["foco"].update({
        "atajo": f"Ctrl+Mayús+{caracter}", "rol_nombre": "BUTTON"})
    return caso


def caso_de_voz(voz):
    caso = datos()
    caso["pasos"][0]["habla"] = [{"texto": f"Voz principal: {voz} contraído"}]
    return caso


class TestCarpetaApp(unittest.TestCase):

    def _caso(self, ruta):
        caso = datos()
        caso["pasos"][0]["habla"] = [{"texto": f"Carpeta de descargas {ruta}"}]
        caso["pasos"][0]["foco"]["valor"] = ruta
        return caso

    def test_la_carpeta_de_la_app_en_dicho_y_valor_va_con_marcador(self):
        carpeta = Path(r"C:\Users\Miguelito\Documents\guyrapu")
        ruta = str(carpeta).upper() + r"\Descargas"
        with mock.patch.object(valores_de_la_pc, "CARPETA_APP", carpeta,
                               create=True):
            texto = transcripcion.texto(self._caso(ruta))
        self.assertIn(r"<carpeta de la app>\\Descargas", texto)
        self.assertNotIn(r"C:\\USERS\\MIGUELITO", texto)

    def test_una_ruta_que_no_es_la_carpeta_de_la_app_queda_igual(self):
        carpeta = Path(r"C:\Users\Miguelito\Documents\guyrapu")
        ruta = r"C:\Users\Otro\Descargas"
        with mock.patch.object(valores_de_la_pc, "CARPETA_APP", carpeta,
                               create=True):
            texto = transcripcion.texto(self._caso(ruta))
        self.assertIn(r"C:\\Users\\Otro\\Descargas", texto)
        self.assertNotIn("<carpeta de la app>", texto)


class TestValoresDeLaPC(unittest.TestCase):

    def test_la_misma_tecla_fisica_con_otra_distribucion_da_la_misma_linea(
            self):
        with mock.patch.object(tecla_fisica, "texto_tecla",
                               distribucion("¿", "¡")):
            casa = transcripcion.texto(caso_de_tecla("¡"))
        with mock.patch.object(tecla_fisica, "texto_tecla",
                               distribucion("-", "¿")):
            oficina = transcripcion.texto(caso_de_tecla("¿"))
        self.assertEqual(casa, oficina)
        self.assertIn("Ctrl+Mayús+<tecla sc0d>", casa)

    def test_la_tecla_sc0c_con_apostrofo_o_guion_da_la_misma_linea(self):
        with mock.patch.object(tecla_fisica, "texto_tecla",
                               distribucion("'", "-")):
            espana = transcripcion.texto(
                caso_de_tecla("'", "Filtro anterior del chat"))
        with mock.patch.object(tecla_fisica, "texto_tecla",
                               distribucion("-", "-")):
            estados_unidos = transcripcion.texto(
                caso_de_tecla("-", "Filtro anterior del chat"))
        self.assertEqual(espana, estados_unidos)
        self.assertIn("Ctrl+Mayús+<tecla sc0c> (fija)", espana)
        self.assertIn("atajo='Ctrl+Mayús+<tecla sc0c>'", espana)

    def test_varias_lineas_listan_las_voces_una_sola_vez(self):
        llamadas = []

        def listar(motor, fabrica_contexto=None):
            llamadas.append(motor)
            return []

        caso = datos()
        caso["pasos"] = [dict(caso["pasos"][0]) for _ in range(3)]
        with mock.patch.object(motores, "listar_voces", listar):
            texto = transcripcion.texto(caso)
        self.assertEqual(len(texto.splitlines()), 3)
        self.assertEqual(llamadas, ["sapi", "onecore"])

    def test_el_caracter_fuera_de_una_combinacion_no_cambia(self):
        caso = datos()
        caso["pasos"][0]["habla"] = [{"texto": "¿Guardar los cambios?"}]
        with mock.patch.object(tecla_fisica, "texto_tecla",
                               distribucion("-", "¿")):
            texto = transcripcion.texto(caso)
        self.assertIn("¿Guardar los cambios?", texto)
        self.assertNotIn("<tecla", texto)

    def test_dos_listas_de_voces_distintas_dan_la_misma_linea(self):
        with mock.patch.object(motores, "listar_voces",
                               return_value=["Microsoft Helena Desktop"]):
            casa = transcripcion.texto(caso_de_voz("Microsoft Helena Desktop"))
        with mock.patch.object(motores, "listar_voces",
                               return_value=["Helena"]):
            oficina = transcripcion.texto(caso_de_voz("Helena"))
        self.assertEqual(casa, oficina)
        self.assertIn("<voz de Windows>", casa)

    def test_un_nombre_de_voz_dentro_de_otro_no_deja_media_voz(self):
        voces = ["Microsoft Helena",
                 "Microsoft Helena Desktop - Spanish (Spain)"]
        con = caso_de_voz("Microsoft Helena Desktop - Spanish (Spain)")
        with mock.patch.object(motores, "listar_voces", return_value=voces):
            texto = transcripcion.texto(con)
        self.assertIn("dijo='Voz principal: <voz de Windows> contraído'",
                      texto)

    def test_si_listar_voces_falla_la_linea_sigue_y_se_anota(self):
        with mock.patch.object(motores, "listar_voces",
                               side_effect=RuntimeError("sin prism")), \
                self.assertLogs("qa.valores_de_la_pc", "WARNING") as registro:
            texto = transcripcion.texto(datos())
        self.assertIn("Categorías", texto)
        self.assertTrue(any("sin prism" in linea
                            for linea in registro.output))

    def test_sumar_una_entrada_a_la_tabla_agrega_su_marcador(self):
        caso = datos()
        caso["pasos"][0]["habla"] = [{"texto": "Habla de Miguelito"}]
        entrada = valores_de_la_pc.Entrada(
            lambda: [("Miguelito", "<persona>")],
            valores_de_la_pc.aplicar_texto)
        with mock.patch.object(valores_de_la_pc, "ENTRADAS",
                               valores_de_la_pc.ENTRADAS + (entrada,)):
            texto = transcripcion.texto(caso)
        self.assertIn("<persona>", texto)


if __name__ == "__main__":
    unittest.main()
