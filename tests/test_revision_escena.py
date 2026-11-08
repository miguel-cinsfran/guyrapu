# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de los avisos de encuadre de una escena de OBS."""

import unittest

from guyrapu.obs import revision_escena

ACOMODAR = ("Para acomodar la escena, usa Aplicar diseño, en la pestaña "
            "Escena del Panel de OBS.")


def elemento(nombre, indice, *, pos=(0, 0), origen=(400, 200),
             escala=(1, 1), recorte=(0, 0, 0, 0), alineacion=5, giro=0,
             bounds_type="OBS_BOUNDS_NONE", bounds=(0, 0), bounds_alin=0,
             clase="image_source", visible=True, crop_to_bounds=False,
             sin_origen=False):
    izquierda, derecha, arriba, abajo = recorte
    datos = {
        "positionX": pos[0], "positionY": pos[1],
        "width": origen[0] * escala[0], "height": origen[1] * escala[1],
        "scaleX": escala[0], "scaleY": escala[1],
        "rotation": giro, "alignment": alineacion,
        "boundsType": bounds_type, "boundsAlignment": bounds_alin,
        "boundsWidth": bounds[0], "boundsHeight": bounds[1],
        "cropLeft": izquierda, "cropRight": derecha,
        "cropTop": arriba, "cropBottom": abajo,
        "cropToBounds": crop_to_bounds,
    }
    if not sin_origen:
        datos["sourceWidth"] = origen[0]
        datos["sourceHeight"] = origen[1]
    return {
        "sourceName": nombre,
        "sceneItemIndex": indice,
        "sceneItemEnabled": visible,
        "inputKind": clase,
        "sceneItemTransform": datos,
    }


def revisar(elementos, ancho=1600, alto=900):
    return revision_escena.revisar(elementos, ancho, alto)


class FueraDelVideoTest(unittest.TestCase):
    def test_p3_aviso_justo_en_el_10_por_ciento(self):
        hallazgos = revisar([elemento(
            "Juego", 0, origen=(1600, 900), pos=(160, 0))])
        self.assertIn(
            "La fuente Juego queda fuera del vídeo el 10 por ciento, "
            "por la derecha.", hallazgos.avisos)

    def test_p3_justo_debajo_del_10_no_avisa(self):
        hallazgos = revisar([elemento(
            "Juego", 0, origen=(1600, 900), pos=(159, 0))])
        self.assertNotIn("queda fuera", " ".join(hallazgos.avisos))
        self.assertNotIn("queda fuera", " ".join(hallazgos.problemas))

    def test_p3_problema_justo_en_el_50_por_ciento(self):
        hallazgos = revisar([elemento(
            "Juego", 0, origen=(1600, 900), pos=(800, 0))])
        self.assertIn(
            "La fuente Juego queda fuera del vídeo el 50 por ciento, "
            "por la derecha.", hallazgos.problemas)
        self.assertNotIn("queda fuera", " ".join(hallazgos.avisos))

    def test_p3_justo_debajo_del_50_es_aviso(self):
        hallazgos = revisar([elemento(
            "Juego", 0, origen=(1600, 900), pos=(700, 0))])
        self.assertIn("queda fuera del vídeo el 44 por ciento",
                      " ".join(hallazgos.avisos))
        self.assertNotIn("queda fuera", " ".join(hallazgos.problemas))

    def test_p3_entera_desde_el_99_5(self):
        hallazgos = revisar([elemento(
            "Juego", 0, origen=(1600, 900), pos=(1592, 0))])
        self.assertIn("La fuente Juego queda entera fuera del vídeo el 100 "
                      "por ciento, por la derecha.",
                      hallazgos.problemas)

    def test_p3_justo_debajo_de_entera_no_dice_entera(self):
        hallazgos = revisar([elemento(
            "Juego", 0, origen=(1600, 900), pos=(1591, 0))])
        texto = " ".join(hallazgos.problemas)
        self.assertIn("La fuente Juego queda fuera del vídeo el 99 por "
                      "ciento, por la derecha.", texto)
        self.assertNotIn("entera", texto)

    def test_p3_nombra_los_lados_por_los_que_sale(self):
        hallazgos = revisar([elemento(
            "Juego", 0, origen=(1600, 900), pos=(-160, -90))])
        self.assertIn("por la izquierda y por arriba",
                      " ".join(hallazgos.avisos))


class TapadaTest(unittest.TestCase):
    def test_p4_aviso_justo_en_el_50_por_ciento(self):
        hallazgos = revisar([
            elemento("Fondo", 0, origen=(400, 200)),
            elemento("Tapa", 1, origen=(400, 100)),
        ], 400, 200)
        self.assertIn("La fuente Fondo está tapada el 50 por ciento por Tapa.",
                      hallazgos.avisos)

    def test_p4_justo_debajo_del_50_no_avisa(self):
        hallazgos = revisar([
            elemento("Fondo", 0, origen=(400, 200)),
            elemento("Tapa", 1, origen=(400, 98)),
        ], 400, 200)
        self.assertNotIn("está tapada", " ".join(hallazgos.avisos))

    def test_p4_problema_justo_en_el_95_por_ciento(self):
        hallazgos = revisar([
            elemento("Fondo", 0, origen=(400, 200)),
            elemento("Tapa", 1, origen=(400, 190)),
        ], 400, 200)
        self.assertIn("La fuente Fondo está tapada el 95 por ciento por Tapa.",
                      hallazgos.problemas)

    def test_p4_justo_debajo_del_95_es_aviso(self):
        hallazgos = revisar([
            elemento("Fondo", 0, origen=(400, 200)),
            elemento("Tapa", 1, origen=(400, 189)),
        ], 400, 200)
        self.assertIn("La fuente Fondo está tapada el 94 por ciento por Tapa.",
                      hallazgos.avisos)
        self.assertNotIn("está tapada", " ".join(hallazgos.problemas))

    def test_p4_una_fuente_entera_fuera_no_se_avisa_tapada(self):
        hallazgos = revisar([
            elemento("Fondo", 0, origen=(400, 200), pos=(2000, 0)),
            elemento("Tapa", 1, origen=(400, 200)),
        ], 400, 200)
        self.assertIn("entera fuera del vídeo", " ".join(hallazgos.problemas))
        self.assertNotIn("está tapada", " ".join(hallazgos.problemas))
        self.assertNotIn("está tapada", " ".join(hallazgos.avisos))


class DeformadaTest(unittest.TestCase):
    def test_p5_aviso_justo_en_el_10_por_ciento(self):
        hallazgos = revisar([elemento(
            "Juego", 0, origen=(400, 400), escala=(1.1, 1))], 1600, 900)
        self.assertIn("La fuente Juego está estirada a lo ancho el 10 por "
                      "ciento.", hallazgos.avisos)

    def test_p5_justo_debajo_del_10_no_avisa(self):
        hallazgos = revisar([elemento(
            "Juego", 0, origen=(400, 400), escala=(1.09, 1))], 1600, 900)
        self.assertNotIn("estirada", " ".join(hallazgos.avisos))

    def test_p5_problema_justo_en_el_50_por_ciento(self):
        hallazgos = revisar([elemento(
            "Juego", 0, origen=(400, 400), escala=(1.5, 1))], 1600, 900)
        self.assertIn("La fuente Juego está estirada a lo ancho el 50 por "
                      "ciento.", hallazgos.problemas)

    def test_p5_justo_debajo_del_50_es_aviso(self):
        hallazgos = revisar([elemento(
            "Juego", 0, origen=(400, 400), escala=(1.49, 1))], 1600, 900)
        self.assertIn("La fuente Juego está estirada a lo ancho el 49 por "
                      "ciento.", hallazgos.avisos)
        self.assertNotIn("estirada", " ".join(hallazgos.problemas))

    def test_p5_a_lo_alto_cuando_la_imagen_se_achica(self):
        hallazgos = revisar([elemento(
            "Juego", 0, origen=(400, 400), escala=(1, 1.5))], 1600, 900)
        self.assertIn("La fuente Juego está estirada a lo alto el 50 por "
                      "ciento.", hallazgos.problemas)


class VacioTest(unittest.TestCase):
    def test_p6_aviso_justo_en_el_15_por_ciento(self):
        hallazgos = revisar([elemento(
            "Juego", 0, origen=(1000, 850))], 1000, 1000)
        self.assertIn("Queda vacío el 15 por ciento del vídeo, sin ninguna "
                      "fuente visible con imagen.", hallazgos.avisos)

    def test_p6_justo_debajo_del_15_no_avisa(self):
        hallazgos = revisar([elemento(
            "Juego", 0, origen=(1000, 851))], 1000, 1000)
        self.assertNotIn("Queda vacío", " ".join(hallazgos.avisos))

    def test_p6_problema_justo_en_el_50_por_ciento(self):
        hallazgos = revisar([elemento(
            "Juego", 0, origen=(1000, 500))], 1000, 1000)
        self.assertIn("Queda vacío el 50 por ciento del vídeo, sin ninguna "
                      "fuente visible con imagen.", hallazgos.problemas)

    def test_p6_justo_debajo_del_50_es_aviso(self):
        hallazgos = revisar([elemento(
            "Juego", 0, origen=(1000, 501))], 1000, 1000)
        self.assertIn("Queda vacío el 50 por ciento del vídeo",
                      " ".join(hallazgos.avisos))
        self.assertNotIn("Queda vacío", " ".join(hallazgos.problemas))

    def test_p6_la_union_no_suma_dos_veces_el_solape(self):
        hallazgos = revisar([
            elemento("Arriba", 0, origen=(1000, 500)),
            elemento("Abajo", 1, origen=(1000, 500), pos=(0, 250)),
        ], 1000, 1000)
        self.assertIn("Queda vacío el 25 por ciento del vídeo",
                      " ".join(hallazgos.avisos))

    def test_p6_no_avisa_si_ninguna_fuente_con_imagen_queda_dentro(self):
        hallazgos = revisar([elemento(
            "Juego", 0, origen=(1000, 500), pos=(1001, 0))], 1000, 1000)
        self.assertNotIn("Queda vacío", " ".join(hallazgos.avisos))
        self.assertNotIn("Queda vacío", " ".join(hallazgos.problemas))


class SinImagenTest(unittest.TestCase):
    def test_p7_cada_tipo_dice_su_motivo(self):
        casos = {
            "window_capture": ("captura de ventana", "la ventana capturada no "
                               "está abierta o está minimizada"),
            "game_capture": ("juego", "el juego no está abierto o OBS todavía "
                             "no lo captura"),
            "monitor_capture": ("pantalla", "OBS no puede capturar esa "
                                "pantalla"),
            "dshow_input": ("cámara", "la cámara no está conectada o la está "
                            "usando otra aplicación"),
        }
        for clase, (nombre, motivo) in casos.items():
            with self.subTest(clase=clase):
                hallazgos = revisar([elemento(
                    nombre, 0, origen=(0, 0), sin_origen=True,
                    clase=clase)], 1000, 1000)
                self.assertIn(
                    f"La fuente {nombre} no muestra imagen: {motivo}.",
                    hallazgos.avisos)

    def test_p7_una_fuente_oculta_no_avisa(self):
        hallazgos = revisar([elemento(
            "Cámara", 0, origen=(0, 0), sin_origen=True,
            clase="dshow_input", visible=False)], 1000, 1000)
        self.assertNotIn("no muestra imagen", " ".join(hallazgos.avisos))

    def test_p7_las_demas_fuentes_sin_imagen_no_avisan(self):
        hallazgos = revisar([elemento(
            "Música", 0, origen=(0, 0), sin_origen=True,
            clase="wasapi_input_capture")], 1000, 1000)
        self.assertNotIn("no muestra imagen", " ".join(hallazgos.avisos))
        self.assertEqual(hallazgos.problemas, ())


class ComoAcomodarTest(unittest.TestCase):
    def test_p8_con_problema_va_al_final_de_los_problemas(self):
        hallazgos = revisar([elemento(
            "Juego", 0, origen=(1600, 900), pos=(800, 0))])
        self.assertTrue(hallazgos.problemas)
        self.assertEqual(hallazgos.problemas[-1], ACOMODAR)
        self.assertNotIn(ACOMODAR, hallazgos.avisos)

    def test_p8_solo_con_avisos_va_al_final_de_los_avisos(self):
        hallazgos = revisar([elemento(
            "Juego", 0, origen=(1600, 900), pos=(160, 0))])
        self.assertTrue(hallazgos.avisos)
        self.assertEqual(hallazgos.avisos[-1], ACOMODAR)
        self.assertNotIn(ACOMODAR, hallazgos.problemas)

    def test_p8_sin_hallazgos_de_encuadre_no_agrega_la_frase(self):
        hallazgos = revisar([elemento("Juego", 0, origen=(1600, 900))])
        self.assertEqual(hallazgos.problemas, ())
        self.assertEqual(hallazgos.avisos, ())

    def test_p8_una_fuente_sin_imagen_sola_no_agrega_la_frase(self):
        hallazgos = revisar([elemento(
            "Cámara", 0, origen=(0, 0), sin_origen=True,
            clase="dshow_input")], 1000, 1000)
        self.assertTrue(hallazgos.avisos)
        self.assertNotIn(ACOMODAR, hallazgos.avisos)


if __name__ == "__main__":
    unittest.main()
