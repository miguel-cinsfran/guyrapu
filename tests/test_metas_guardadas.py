# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas del archivo de las metas del directo."""

import json
import tempfile
import unittest
from pathlib import Path

from guyrapu.interaction import metas, metas_guardadas


def _datos(**cambios):
    datos = {
        "nombre": "100 me gusta", "que_cuenta": "me_gusta", "objetivo": 100,
        "estilo": "", "festejo": "", "activa": True, "en_video": False,
    }
    datos.update(cambios)
    return datos


class TestConversion(unittest.TestCase):

    def test_a_meta_y_de_vuelta_conserva_los_datos(self):
        datos = _datos()
        meta = metas_guardadas.a_meta(datos)
        self.assertIsInstance(meta, metas.Meta)
        self.assertEqual(meta.nombre, "100 me gusta")
        self.assertEqual(metas_guardadas.desde_meta(meta), datos)

    def test_una_meta_con_estilo_festejo_y_apagada(self):
        datos = _datos(estilo="banda", festejo="Gracias", activa=False)
        meta = metas_guardadas.a_meta(datos)
        self.assertEqual(metas_guardadas.desde_meta(meta), datos)

    def test_una_meta_sin_datos_nace_con_los_valores_de_fabrica(self):
        meta = metas_guardadas.a_meta({})
        self.assertEqual(meta.nombre, "")
        self.assertEqual(meta.que_cuenta, "me_gusta")
        self.assertEqual(meta.objetivo, 1)
        self.assertEqual(meta.estilo, "")
        self.assertEqual(meta.festejo, "")
        self.assertTrue(meta.activa)
        self.assertFalse(meta.en_video)

    def test_p1_un_archivo_sin_en_video_lo_lee_falso(self):
        meta = metas_guardadas.a_meta(
            {"nombre": "Viaje", "que_cuenta": "me_gusta", "objetivo": 5})
        self.assertFalse(meta.en_video)

    def test_p1_en_video_se_guarda_y_se_lee(self):
        datos = _datos(en_video=True)
        meta = metas_guardadas.a_meta(datos)
        self.assertTrue(meta.en_video)
        self.assertTrue(metas_guardadas.desde_meta(meta)["en_video"])

    def test_los_tipos_se_fuerzan_y_lo_raro_cae_a_su_defecto(self):
        meta = metas_guardadas.a_meta({
            "nombre": 123, "que_cuenta": "espectadores", "objetivo": "no",
            "estilo": None, "festejo": 7, "activa": "false",
        })
        self.assertEqual(meta.nombre, "123")
        self.assertEqual(meta.que_cuenta, "me_gusta")
        self.assertEqual(meta.objetivo, 1)
        self.assertEqual(meta.estilo, "")
        self.assertEqual(meta.festejo, "7")
        self.assertFalse(meta.activa)

    def test_el_objetivo_de_texto_o_cero_se_corrige(self):
        self.assertEqual(
            metas_guardadas.a_meta({"objetivo": "7"}).objetivo, 7)
        self.assertEqual(metas_guardadas.a_meta({"objetivo": 0}).objetivo, 1)
        self.assertEqual(metas_guardadas.a_meta({"objetivo": -5}).objetivo, 1)


class TestArchivo(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.ruta = Path(self.tmp.name) / "metas.json"

    def test_ida_y_vuelta_por_el_archivo(self):
        meta = metas.Meta(
            "100 me gusta", "me_gusta", 100, estilo="banda",
            festejo="Gracias", activa=False)
        metas_guardadas.guardar(self.ruta, [meta])
        self.assertEqual(metas_guardadas.cargar(self.ruta),
                         [metas_guardadas.desde_meta(meta)])

    def test_guarda_tambien_datos_normalizados(self):
        metas_guardadas.guardar(self.ruta, [_datos()])
        self.assertEqual(metas_guardadas.cargar(self.ruta), [_datos()])

    def test_un_archivo_danado_se_lee_como_lista_vacia(self):
        self.ruta.write_text("{esto no es json", encoding="utf-8")
        self.assertEqual(metas_guardadas.cargar(self.ruta), [])

    def test_un_archivo_ausente_se_lee_como_lista_vacia(self):
        self.assertEqual(metas_guardadas.cargar(self.ruta), [])

    def test_un_json_que_no_es_lista_se_lee_como_lista_vacia(self):
        self.ruta.write_text('{"nombre": "Viaje"}', encoding="utf-8")
        self.assertEqual(metas_guardadas.cargar(self.ruta), [])

    def test_los_datos_extranos_se_descartan_o_se_corrigen(self):
        self.ruta.write_text(json.dumps([
            "no es una meta",
            {"nombre": "Viaje", "que_cuenta": "otro", "objetivo": 0},
        ]), encoding="utf-8")
        self.assertEqual(
            metas_guardadas.cargar(self.ruta),
            [metas_guardadas.desde_meta(metas.Meta("Viaje", "me_gusta", 1))])


if __name__ == "__main__":
    unittest.main()
