# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas puras del motivo de cada opción del buscador de descargas."""

import unittest

from guyrapu.downloads.busqueda_youtube import Resultado
from guyrapu.ui import buscador_acciones

NO_DISPONIBLE = "No disponible para este tipo de resultado"
MEZCLA = "Algún resultado elegido no se puede descargar"
TODAS = ("agregar", "escuchar", "audio", "video", "formato", "app",
         "musica", "copiar", "navegador", "sitios")


def _res(id="v", tipo="video", directo=False, programado=False):
    return Resultado(
        id=id, url=f"https://www.youtube.com/watch?v={id}",
        titulo=f"Título {id}", canal=f"Canal {id}", duracion=60, vistas=10,
        marca_tiempo=1700000000, descripcion=f"Descripción {id}",
        tipo=tipo, en_directo=directo, programado=programado)


class TestMotivoDe(unittest.TestCase):

    def test_un_video_aplica_a_todas(self):
        for opcion in TODAS:
            with self.subTest(opcion=opcion):
                self.assertEqual(
                    buscador_acciones.motivo_de(opcion, [_res()], True, True),
                    "")

    def test_un_canal_no_ofrece_descargas(self):
        for opcion in TODAS:
            with self.subTest(opcion=opcion):
                esperado = ("" if opcion in
                            ("contenido", "copiar", "navegador", "sitios")
                            else NO_DISPONIBLE)
                self.assertEqual(
                    buscador_acciones.motivo_de(
                        opcion, [_res(tipo="canal")], True, True),
                    esperado)

    def test_un_directo_solo_ofrece_lo_de_la_app_la_musica_y_el_enlace(self):
        for opcion in TODAS:
            with self.subTest(opcion=opcion):
                esperado = ("" if opcion in
                            ("app", "musica", "copiar", "navegador", "sitios")
                            else NO_DISPONIBLE)
                self.assertEqual(
                    buscador_acciones.motivo_de(
                        opcion, [_res(directo=True)], True, True),
                    esperado)

    def test_un_programado_solo_ofrece_el_enlace(self):
        for opcion in TODAS:
            with self.subTest(opcion=opcion):
                esperado = ("" if opcion in
                            ("copiar", "navegador", "sitios")
                            else NO_DISPONIBLE)
                self.assertEqual(
                    buscador_acciones.motivo_de(
                        opcion, [_res(programado=True)], True, True),
                    esperado)

    def test_sin_app_ni_musica_sus_opciones_no_estan(self):
        self.assertEqual(
            buscador_acciones.motivo_de("app", [_res()], False, True),
            NO_DISPONIBLE)
        self.assertEqual(
            buscador_acciones.motivo_de("musica", [_res()], True, False),
            NO_DISPONIBLE)

    def test_la_mezcla_descargable_no_deja_motivo_a_las_descargas(self):
        elegidos = [_res("v"), _res("l", tipo="lista")]
        for opcion in ("agregar", "audio", "video"):
            with self.subTest(opcion=opcion):
                self.assertEqual(
                    buscador_acciones.motivo_de(opcion, elegidos, True, True),
                    "")

    def test_la_mezcla_con_algo_que_no_baja_dice_por_que_no(self):
        casos = [
            [_res("v"), _res("c", tipo="canal")],
            [_res("v"), _res("d", directo=True)],
            [_res("v"), _res("p", programado=True)],
        ]
        for elegidos in casos:
            for opcion in ("agregar", "audio", "video"):
                with self.subTest(opcion=opcion, elegidos=elegidos):
                    self.assertEqual(
                        buscador_acciones.motivo_de(
                            opcion, elegidos, True, True),
                        MEZCLA)

    def test_la_mezcla_no_le_pone_motivo_a_las_de_una_fila(self):
        elegidos = [_res("v"), _res("l", tipo="lista")]
        self.assertEqual(
            buscador_acciones.motivo_de("copiar", elegidos, True, True), "")

    def test_sin_resultados_no_hay_motivo(self):
        self.assertEqual(
            buscador_acciones.motivo_de("agregar", [], True, True), "")


if __name__ == "__main__":
    unittest.main()
