# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Cómo un medio de la biblioteca entra en una pieza del vídeo."""

import tempfile
import unittest

from guyrapu.core import paths
from guyrapu.interaction import medios_guardados, medio_en_video
from tests.rutas_temporales import redirigir_rutas


def _medio(nombre="fuegos", tipo="video", archivo="fuegos.mp4", duracion=12,
           ganancia_db=-6.0):
    return {"nombre": nombre, "tipo": tipo, "archivo": archivo,
            "duracion": duracion, "ganancia_db": ganancia_db}


class TestMedioEnVideo(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        parche = redirigir_rutas(self.tmp.name)
        parche.__enter__()
        self.addCleanup(parche.__exit__, None, None, None)

    def _guardar(self, *medios):
        medios_guardados.guardar(paths.medios(), list(medios))

    def test_resolver_da_la_ruta_el_tipo_la_duracion_y_la_ganancia(self):
        self._guardar(_medio())
        self.assertEqual(medio_en_video.resolver("fuegos"), {
            "ruta": str(paths.carpeta_medios() / "fuegos.mp4"),
            "tipo": "video", "duracion": 12, "ganancia_db": -6.0,
            "volumen": 100,
        })

    def test_resolver_sin_nombre_o_con_un_medio_que_ya_no_esta_da_none(self):
        self._guardar(_medio())
        self.assertIsNone(medio_en_video.resolver(""))
        self.assertIsNone(medio_en_video.resolver("otro"))

    def test_con_medio_suma_el_medio_y_toma_la_duracion_del_archivo(self):
        medio = _medio(tipo="sonido", archivo="risa.wav", duracion=15)
        datos, segundos = medio_en_video.con_medio(
            {"estilo": "clasico", "nombre": "grito"}, 8, medio)
        self.assertEqual(segundos, 15)
        self.assertEqual(datos, {"estilo": "clasico", "nombre": "grito",
                                 "medio": medio})

    def test_con_medio_no_cambia_los_segundos_para_imagen_ni_sin_duracion(self):
        datos = {"estilo": "clasico"}
        for medio in (_medio(tipo="imagen", archivo="risa.gif", duracion=5),
                      _medio(tipo="sonido", archivo="risa.wav", duracion=0)):
            with self.subTest(tipo=medio["tipo"], duracion=medio["duracion"]):
                nuevos, segundos = medio_en_video.con_medio(datos, 8, medio)
                self.assertEqual(segundos, 8)
                self.assertEqual(nuevos["medio"], medio)

    def test_con_medio_sin_medio_devuelve_los_datos_sin_tocarlos(self):
        datos = {"estilo": "clasico"}
        nuevos, segundos = medio_en_video.con_medio(datos, 8, None)
        self.assertIs(nuevos, datos)
        self.assertEqual(segundos, 8)
