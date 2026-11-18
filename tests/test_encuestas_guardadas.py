# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas del archivo de las encuestas guardadas."""

import tempfile
import unittest
from pathlib import Path

from guyrapu.interaction import encuestas_guardadas


def _datos(**cambios):
    datos = {
        "pregunta": "¿Qué pizza?",
        "nombre": "¿Qué pizza?",
        "opciones": ["muzzarella", "napolitana", "calabresa"],
        "segundos": 120,
        "destino": "video",
        "estilo": "clasico",
    }
    datos.update(cambios)
    return datos


class TestConversion(unittest.TestCase):

    def test_normalizar_conserva_los_campos(self):
        datos = _datos()
        self.assertEqual(encuestas_guardadas.normalizar(datos), datos)

    def test_una_encuesta_sin_datos_nace_con_los_valores_de_fabrica(self):
        self.assertEqual(encuestas_guardadas.normalizar({}), {
            "pregunta": "", "nombre": "", "opciones": [], "segundos": 120,
            "destino": "video", "estilo": "clasico"})

    def test_los_tipos_se_fuerzan_y_lo_raro_cae_a_su_defecto(self):
        normalizada = encuestas_guardadas.normalizar({
            "pregunta": "  ¿Qué?  ",
            "opciones": "uno\ndos\n\n",
            "segundos": "300",
            "destino": "otro",
            "estilo": "",
        })
        self.assertEqual(normalizada["pregunta"], "¿Qué?")
        self.assertEqual(normalizada["opciones"], ["uno", "dos"])
        self.assertEqual(normalizada["segundos"], 300)
        self.assertEqual(normalizada["destino"], "video")
        self.assertEqual(normalizada["estilo"], "")

    def test_un_estilo_explicito_no_cambia(self):
        self.assertEqual(
            encuestas_guardadas.normalizar({"estilo": "clasico"})["estilo"],
            "clasico")
        self.assertEqual(
            encuestas_guardadas.normalizar({"estilo": "mio"})["estilo"],
            "mio")

    def test_el_estilo_vacio_se_conserva(self):
        self.assertEqual(
            encuestas_guardadas.normalizar({"estilo": ""})["estilo"], "")

    def test_el_nombre_sigue_a_la_pregunta(self):
        self.assertEqual(
            encuestas_guardadas.normalizar({"pregunta": "¿Qué?"})["nombre"],
            "¿Qué?")
        self.assertEqual(
            encuestas_guardadas.normalizar({"nombre": "¿Qué?"})["pregunta"],
            "¿Qué?")

    def test_las_opciones_de_mas_se_recortan_a_nueve(self):
        # Se normaliza en vez de rechazar: el archivo puede venir de otra
        # versión o estar editado a mano, y la encuesta debe seguir siendo
        # votable con !1..!9. El cuadro sigue validando con validar_encuesta.
        opciones = [f"opción {numero}" for numero in range(1, 13)]
        normalizada = encuestas_guardadas.normalizar(
            _datos(opciones=opciones))
        self.assertEqual(normalizada["opciones"], opciones[:9])


class TestArchivo(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.ruta = Path(self.tmp.name) / "encuestas.json"

    def test_ida_y_vuelta_por_el_archivo(self):
        datos = _datos(segundos=300, destino="ambos", estilo="banda")
        encuestas_guardadas.guardar(self.ruta, [datos])
        self.assertEqual(encuestas_guardadas.cargar(self.ruta), [datos])

    def test_un_archivo_danado_da_lista_vacia_y_se_registra(self):
        self.ruta.write_text("{esto no es json", encoding="utf-8")
        with self.assertLogs(encuestas_guardadas.logger,
                             level="WARNING") as registros:
            self.assertEqual(encuestas_guardadas.cargar(self.ruta), [])
        self.assertTrue(registros.output)

    def test_un_archivo_ausente_se_lee_como_lista_vacia(self):
        self.assertEqual(encuestas_guardadas.cargar(self.ruta), [])

    def test_un_json_que_no_es_lista_se_lee_como_lista_vacia(self):
        self.ruta.write_text('{"pregunta": "¿Qué?"}', encoding="utf-8")
        with self.assertLogs(encuestas_guardadas.logger, level="WARNING"):
            self.assertEqual(encuestas_guardadas.cargar(self.ruta), [])


class TestTextos(unittest.TestCase):

    def test_la_duracion_se_dice_en_segundos_o_minutos(self):
        self.assertEqual(encuestas_guardadas.duracion(30), "30 segundos")
        self.assertEqual(encuestas_guardadas.duracion(60), "1 minuto")
        self.assertEqual(encuestas_guardadas.duracion(120), "2 minutos")
        self.assertEqual(encuestas_guardadas.duracion(1800), "30 minutos")

    def test_la_fila_dice_pregunta_opciones_y_duracion(self):
        self.assertEqual(encuestas_guardadas.fila(_datos()),
                         "¿Qué pizza?, 3 opciones, 2 minutos")

    def test_escuchar_dice_la_pregunta_y_las_opciones(self):
        self.assertEqual(
            encuestas_guardadas.escuchar(_datos()),
            "Encuesta: ¿Qué pizza?. Opciones: muzzarella, napolitana, "
            "calabresa.")


if __name__ == "__main__":
    unittest.main()
