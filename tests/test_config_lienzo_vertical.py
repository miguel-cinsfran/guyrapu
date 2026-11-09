# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas puras de la configuración del plugin Vertical Canvas.

Sin OBS y sin ventanas: se trabaja sobre el diccionario del config.json y,
para leer y escribir, sobre un archivo temporal.
"""

import json
import tempfile
import unittest
from pathlib import Path

from guyrapu.obs import config_lienzo_vertical


def _config(salidas=None):
    return {
        "canvas": [
            {"canvasName": "Aitum Vertical", "stream_outputs": list(salidas or ())}
        ],
        "otra_clave": {"valor": 1},
    }


class PosicionSalidaTest(unittest.TestCase):

    def test_sin_salidas_no_hay_posicion(self):
        self.assertIsNone(
            config_lienzo_vertical.posicion_salida(_config()))

    def test_encuentra_la_salida_por_su_nombre(self):
        config = _config([
            {"name": "Otra", "stream_server": "a", "stream_key": "b",
             "enabled": False},
            {"name": "Guyrapu", "stream_server": "c", "stream_key": "d",
             "enabled": True},
        ])
        self.assertEqual(
            config_lienzo_vertical.posicion_salida(config), 1)


class ConSalidaTest(unittest.TestCase):

    def test_agrega_al_final_encendida(self):
        config = _config()
        nueva = config_lienzo_vertical.con_salida(
            config, "rtmp://servidor", "clave")
        salidas = nueva["canvas"][0]["stream_outputs"]
        self.assertEqual(
            salidas,
            [{"name": "Guyrapu", "stream_server": "rtmp://servidor",
              "stream_key": "clave", "enabled": True}])

    def test_con_una_salida_ajena_la_agrega_al_final(self):
        ajena = {"name": "Otra", "stream_server": "a", "stream_key": "b",
                 "enabled": False, "extra": "se conserva"}
        config = _config([ajena])
        nueva = config_lienzo_vertical.con_salida(
            config, "rtmp://servidor", "clave")
        salidas = nueva["canvas"][0]["stream_outputs"]
        self.assertEqual(salidas[0], ajena)
        self.assertEqual(salidas[1]["name"], "Guyrapu")
        self.assertTrue(salidas[1]["enabled"])

    def test_actualiza_en_su_lugar_y_conserva_el_resto(self):
        guyrapu = {"name": "Guyrapu", "stream_server": "viejo",
                   "stream_key": "vieja", "enabled": False,
                   "extra": "se conserva"}
        tercera = {"name": "Tercera", "stream_server": "x",
                   "stream_key": "y", "enabled": True}
        config = _config([guyrapu, tercera])
        nueva = config_lienzo_vertical.con_salida(
            config, "rtmp://servidor", "clave")
        salidas = nueva["canvas"][0]["stream_outputs"]
        self.assertEqual(len(salidas), 2)
        self.assertEqual(
            salidas[0],
            {"name": "Guyrapu", "stream_server": "rtmp://servidor",
             "stream_key": "clave", "enabled": True, "extra": "se conserva"})
        self.assertEqual(salidas[1], tercera)

    def test_no_modifica_el_diccionario_original(self):
        config = _config()
        config_lienzo_vertical.con_salida(
            config, "rtmp://servidor", "clave")
        self.assertEqual(config["canvas"][0]["stream_outputs"], [])

    def test_conserva_las_demas_claves_del_archivo(self):
        config = _config()
        config["canvas"][0]["canvasUuid"] = "uuid-vertical"
        nueva = config_lienzo_vertical.con_salida(
            config, "rtmp://servidor", "clave")
        self.assertEqual(nueva["otra_clave"], {"valor": 1})
        self.assertEqual(nueva["canvas"][0]["canvasName"], "Aitum Vertical")
        self.assertEqual(nueva["canvas"][0]["canvasUuid"], "uuid-vertical")


class ArchivoTest(unittest.TestCase):

    def test_leer_un_archivo_que_no_existe_da_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(
                config_lienzo_vertical.leer(Path(tmp) / "config.json"))

    def test_escribe_y_vuelve_a_leer_el_mismo_contenido(self):
        with tempfile.TemporaryDirectory() as tmp:
            ruta = Path(tmp) / "config.json"
            config = config_lienzo_vertical.con_salida(
                _config(), "rtmp://servidor", "clave")
            config_lienzo_vertical.escribir(ruta, config)
            self.assertEqual(config_lienzo_vertical.leer(ruta), config)
            self.assertEqual(
                json.loads(ruta.read_text(encoding="utf-8")), config)


if __name__ == "__main__":
    unittest.main()
