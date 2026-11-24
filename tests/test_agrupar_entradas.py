# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Agrupador de entradas al directo de TikTok (lógica pura, sin wx)."""

import re
import unittest

from guyrapu.capture.agrupar_entradas import AgrupadorEntradas, nombres_del_grupo


class TestAgrupadorEntradas(unittest.TestCase):

    def test_junta_personas_distintas_en_orden_de_llegada(self):
        agrupador = AgrupadorEntradas(ventana=10.0)
        agrupador.sumar("Ana", "1", 100.0)
        agrupador.sumar("Beto", "2", 101.0)
        agrupador.sumar("Caro", "3", 102.0)
        self.assertEqual(
            agrupador.vencido(110.0),
            [("Ana", "1"), ("Beto", "2"), ("Caro", "3")])

    def test_no_repite_a_quien_entra_dos_veces(self):
        agrupador = AgrupadorEntradas(ventana=10.0)
        agrupador.sumar("Ana", "1", 100.0)
        agrupador.sumar("Ana", "1", 101.0)
        agrupador.sumar("Beto", "2", 102.0)
        self.assertEqual(
            agrupador.vencido(110.0),
            [("Ana", "1"), ("Beto", "2")])

    def test_sin_id_la_clave_es_el_nombre(self):
        agrupador = AgrupadorEntradas(ventana=10.0)
        agrupador.sumar("Ana", "", 100.0)
        agrupador.sumar("Ana", "", 101.0)
        self.assertEqual(agrupador.vencido(110.0), [("Ana", "")])

    def test_no_suelta_antes_de_la_ventana(self):
        agrupador = AgrupadorEntradas(ventana=10.0)
        agrupador.sumar("Ana", "1", 100.0)
        self.assertEqual(agrupador.vencido(109.999), [])
        self.assertEqual(agrupador.vencido(109.999), [])

    def test_suelta_todo_al_cumplir_la_ventana_y_la_vacia(self):
        agrupador = AgrupadorEntradas(ventana=10.0)
        agrupador.sumar("Ana", "1", 100.0)
        agrupador.sumar("Beto", "2", 101.0)
        self.assertEqual(
            agrupador.vencido(110.0), [("Ana", "1"), ("Beto", "2")])
        self.assertEqual(agrupador.vencido(110.0), [])

    def test_con_ventana_cero_suelta_al_instante(self):
        agrupador = AgrupadorEntradas(ventana=0)
        agrupador.sumar("Ana", "1", 100.0)
        self.assertEqual(agrupador.vencido(100.0), [("Ana", "1")])

    def test_la_ventana_puede_ser_una_funcion_que_cambia(self):
        segundos = [10]
        agrupador = AgrupadorEntradas(ventana=lambda: segundos[0])
        agrupador.sumar("Ana", "1", 100.0)
        self.assertEqual(agrupador.vencido(104.0), [])
        segundos[0] = 3
        self.assertEqual(agrupador.vencido(104.0), [("Ana", "1")])


class TestPrimeraEntradaAlMomento(unittest.TestCase):

    def test_la_primera_sale_ya_y_las_demas_se_juntan_al_vencer(self):
        agrupador = AgrupadorEntradas(ventana=10.0, primera_al_momento=True)
        self.assertTrue(agrupador.sumar("Ana", "1", 100.0))
        self.assertFalse(agrupador.sumar("Beto", "2", 101.0))
        self.assertFalse(agrupador.sumar("Caro", "3", 102.0))
        self.assertEqual(agrupador.vencido(110.0),
                         [("Beto", "2"), ("Caro", "3")])

    def test_quien_salio_al_momento_no_sale_dos_veces_en_la_misma_espera(self):
        agrupador = AgrupadorEntradas(ventana=10.0, primera_al_momento=True)
        self.assertTrue(agrupador.sumar("Ana", "1", 100.0))
        self.assertFalse(agrupador.sumar("Ana", "1", 101.0))
        self.assertFalse(agrupador.sumar("Beto", "2", 102.0))
        self.assertEqual(agrupador.vencido(110.0), [("Beto", "2")])
        self.assertTrue(agrupador.sumar("Ana", "1", 111.0))

    def test_si_no_entra_nadie_mas_no_sale_nada_al_vencer(self):
        agrupador = AgrupadorEntradas(ventana=10.0, primera_al_momento=True)
        self.assertTrue(agrupador.sumar("Ana", "1", 100.0))
        self.assertEqual(agrupador.vencido(110.0), [])
        self.assertTrue(agrupador.sumar("Beto", "2", 111.0))
        self.assertEqual(agrupador.vencido(121.0), [])

    def test_sin_la_bandera_el_grupo_sale_como_hoy(self):
        agrupador = AgrupadorEntradas(ventana=10.0, primera_al_momento=False)
        self.assertFalse(agrupador.sumar("Ana", "1", 100.0))
        self.assertFalse(agrupador.sumar("Beto", "2", 101.0))
        self.assertEqual(agrupador.vencido(110.0),
                         [("Ana", "1"), ("Beto", "2")])

    def test_la_bandera_puede_cambiar_sin_reconectar(self):
        bandera = [True]
        agrupador = AgrupadorEntradas(
            ventana=10.0, primera_al_momento=lambda: bandera[0])
        self.assertTrue(agrupador.sumar("Ana", "1", 100.0))
        self.assertFalse(agrupador.sumar("Beto", "2", 101.0))
        bandera[0] = False
        self.assertEqual(agrupador.vencido(110.0), [("Beto", "2")])
        self.assertFalse(agrupador.sumar("Caro", "3", 111.0))
        self.assertEqual(agrupador.vencido(121.0), [("Caro", "3")])

    def test_con_la_bandera_nadie_se_repite_ni_se_pierde(self):
        for total in range(1, 12):
            with self.subTest(total=total):
                agrupador = AgrupadorEntradas(
                    ventana=10.0, primera_al_momento=True)
                salieron = []
                ahora = 100.0
                for indice in range(total):
                    persona = f"P{indice}"
                    if agrupador.sumar(persona, str(indice), ahora):
                        salieron.append(persona)
                    ahora += 0.5
                salieron.extend(nombre for nombre, _canal
                                in agrupador.vencido(110.0))
                self.assertEqual(sorted(salieron),
                                 sorted(f"P{indice}" for indice in range(total)))
                self.assertEqual(len(salieron), len(set(salieron)))


class TestNombresDelGrupo(unittest.TestCase):

    def test_un_nombre(self):
        self.assertEqual(nombres_del_grupo(["Ana"]), "Ana")

    def test_dos_nombres(self):
        self.assertEqual(nombres_del_grupo(["Ana", "Beto"]), "Ana y Beto")

    def test_tres_nombres(self):
        self.assertEqual(
            nombres_del_grupo(["Ana", "Beto", "Caro"]),
            "Ana, Beto y Caro")

    def test_cuatro_nombres_resumen_uno_mas(self):
        self.assertEqual(
            nombres_del_grupo(["Ana", "Beto", "Caro", "Dani"]),
            "Ana, Beto, Caro y 1 más")

    def test_siete_nombres_resumen_cuatro_mas(self):
        self.assertEqual(
            nombres_del_grupo(
                ["Ana", "Beto", "Caro", "Dani", "Eva", "Flor", "Gabi"]),
            "Ana, Beto, Caro y 4 más")

    def test_propiedad_hasta_veinte_nombres(self):
        for total in range(1, 21):
            nombres = [f"Persona{n}" for n in range(total)]
            with self.subTest(total=total):
                texto = nombres_del_grupo(nombres)
                visibles = [nombre for nombre in nombres
                            if nombre in texto]
                self.assertLessEqual(len(visibles), 3)
                if total <= 3:
                    self.assertEqual(len(visibles), total)
                    self.assertNotIn("más", texto)
                    continue
                coincidencia = re.search(r"y (\d+) más$", texto)
                self.assertIsNotNone(coincidencia, texto)
                self.assertEqual(
                    len(visibles) + int(coincidencia.group(1)), total)


if __name__ == "__main__":
    unittest.main()
