# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas del rectángulo que dibuja OBS para una fuente de la escena."""

import unittest

from guyrapu.obs import geometria_fuente


def transformacion(**cambios):
    datos = {
        "positionX": 0.0, "positionY": 0.0,
        "sourceWidth": 400.0, "sourceHeight": 200.0,
        "width": 400.0, "height": 200.0,
        "scaleX": 1.0, "scaleY": 1.0,
        "rotation": 0.0, "alignment": 5,
        "boundsType": "OBS_BOUNDS_NONE", "boundsAlignment": 0,
        "boundsWidth": 0.0, "boundsHeight": 0.0,
        "cropLeft": 0.0, "cropRight": 0.0,
        "cropTop": 0.0, "cropBottom": 0.0,
        "cropToBounds": False,
    }
    datos.update(cambios)
    return datos


class RectanguloTest(unittest.TestCase):
    def comprobar(self, medida, rect, deformacion=1.0):
        self.assertIsNotNone(medida)
        self.assertTrue(medida.tiene_imagen)
        obtenido = (medida.izquierda, medida.arriba,
                    medida.ancho, medida.alto)
        for valor, esperado in zip(obtenido, rect):
            self.assertAlmostEqual(valor, esperado, delta=0.6)
        self.assertAlmostEqual(medida.deformacion, deformacion, delta=0.01)

    def test_caso_1_marco_scale_inner_centrado(self):
        medida = geometria_fuente.medir(transformacion(
            sourceWidth=800, sourceHeight=600, width=800, height=600,
            boundsType="OBS_BOUNDS_SCALE_INNER",
            boundsWidth=1600, boundsHeight=900, boundsAlignment=0))
        self.comprobar(medida, (200, 0, 1200, 900))

    def test_caso_1_marco_scale_inner_arriba_a_la_izquierda(self):
        medida = geometria_fuente.medir(transformacion(
            sourceWidth=800, sourceHeight=600, width=800, height=600,
            boundsType="OBS_BOUNDS_SCALE_INNER",
            boundsWidth=1600, boundsHeight=900, boundsAlignment=1))
        self.comprobar(medida, (0, 0, 1200, 900))

    def test_caso_2_marco_stretch_deforma(self):
        medida = geometria_fuente.medir(transformacion(
            sourceWidth=800, sourceHeight=600, width=800, height=600,
            boundsType="OBS_BOUNDS_STRETCH",
            boundsWidth=400, boundsHeight=200))
        self.comprobar(medida, (0, 0, 400, 200), deformacion=1.5)

    def test_caso_3_marco_scale_outer(self):
        medida = geometria_fuente.medir(transformacion(
            sourceWidth=800, sourceHeight=600, width=800, height=600,
            positionX=300, positionY=300,
            boundsType="OBS_BOUNDS_SCALE_OUTER",
            boundsWidth=400, boundsHeight=200))
        self.comprobar(medida, (300, 250, 400, 300))

    def test_caso_4_recorte_y_escala(self):
        medida = geometria_fuente.medir(transformacion(
            sourceWidth=640, sourceHeight=480, width=320, height=240,
            positionX=1260, positionY=640,
            scaleX=0.5, scaleY=0.5,
            cropLeft=40, cropRight=40))
        self.comprobar(medida, (1260, 640, 280, 240))

    def test_caso_5_giro_recto(self):
        medida = geometria_fuente.medir(transformacion(
            positionX=300, positionY=100, rotation=90))
        self.comprobar(medida, (100, 100, 200, 400))

    def test_caso_6_giro_de_45(self):
        medida = geometria_fuente.medir(transformacion(
            positionX=800, positionY=300, rotation=45))
        self.comprobar(medida, (659, 300, 424, 424))

    def test_caso_7_alineacion_centro(self):
        medida = geometria_fuente.medir(transformacion(
            positionX=800, positionY=450, alignment=0))
        self.comprobar(medida, (600, 350, 400, 200))

    def test_caso_8_espejo_horizontal(self):
        medida = geometria_fuente.medir(transformacion(
            positionX=600, positionY=100, scaleX=-1))
        self.comprobar(medida, (200, 100, 400, 200))

    def test_caso_9_escala_desigual(self):
        medida = geometria_fuente.medir(transformacion(
            sourceWidth=400, sourceHeight=400, width=600, height=300,
            positionX=1300, positionY=600,
            scaleX=1.5, scaleY=0.75))
        self.comprobar(medida, (1300, 600, 600, 300), deformacion=2.0)

    def test_caso_10_marco_vertical_que_se_sale(self):
        medida = geometria_fuente.medir(transformacion(
            sourceWidth=1600, sourceHeight=900, width=3413.5, height=1920,
            positionX=-1166.5, positionY=0,
            boundsType="OBS_BOUNDS_SCALE_INNER",
            boundsWidth=3413.5, boundsHeight=1920))
        self.comprobar(medida, (-1166.5, 0, 3413.5, 1920))

    def test_caso_10_fuente_entera_fuera(self):
        medida = geometria_fuente.medir(transformacion(
            sourceWidth=640, sourceHeight=480, width=597.3, height=512,
            positionX=1521.5, positionY=1365.5,
            scaleX=1.06667, scaleY=1.06667,
            cropLeft=40, cropRight=40))
        self.comprobar(medida, (1521.5, 1365.5, 597.3, 512))


class ImagenTest(unittest.TestCase):
    def test_sin_origen_no_muestra_imagen(self):
        medida = geometria_fuente.medir(transformacion(
            sourceWidth=0, sourceHeight=0, width=0, height=0,
            boundsType="OBS_BOUNDS_SCALE_INNER",
            boundsWidth=1600, boundsHeight=900))
        self.assertIsNotNone(medida)
        self.assertFalse(medida.tiene_imagen)

    def test_el_recorte_deja_el_origen_en_cero(self):
        medida = geometria_fuente.medir(transformacion(
            sourceWidth=80, sourceHeight=200,
            cropLeft=40, cropRight=40))
        self.assertFalse(medida.tiene_imagen)

    def test_sin_sourcewidth_usa_width_y_height(self):
        medida = geometria_fuente.medir(transformacion(
            sourceWidth=None, sourceHeight=None,
            width=800, height=600))
        self.assertTrue(medida.tiene_imagen)
        self.assertAlmostEqual(medida.ancho, 800, delta=0.01)
        self.assertAlmostEqual(medida.alto, 600, delta=0.01)

    def test_sin_transformacion_no_hay_medida(self):
        self.assertIsNone(geometria_fuente.medir(None))
        self.assertIsNone(geometria_fuente.medir({}))


class CropToBoundsTest(unittest.TestCase):
    def test_lo_que_pasa_del_marco_no_cuenta(self):
        medida = geometria_fuente.medir(transformacion(
            sourceWidth=800, sourceHeight=600, width=800, height=600,
            boundsType="OBS_BOUNDS_SCALE_OUTER",
            boundsWidth=400, boundsHeight=200, cropToBounds=True))
        self.assertAlmostEqual(medida.izquierda, 0, delta=0.6)
        self.assertAlmostEqual(medida.arriba, 0, delta=0.6)
        self.assertAlmostEqual(medida.ancho, 400, delta=0.6)
        self.assertAlmostEqual(medida.alto, 200, delta=0.6)


if __name__ == "__main__":
    unittest.main()
