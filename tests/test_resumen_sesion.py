# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas del archivo con el resumen de participación de un directo."""

import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from guyrapu.core import resumen_sesion
from guyrapu.core.config import TIPO_SUPERCHAT, TIPO_TEXTO
from guyrapu.ui.lista_chat import MensajeChat
from guyrapu.ui.participacion_chat import ORDEN_REGALOS, Participacion

AHORA = datetime(2026, 11, 17, 22, 30)


def _registro(autor, identificador, tipo=TIPO_TEXTO, monto=""):
    return MensajeChat(plataforma="youtube", autor=autor,
                       identificador=identificador, texto="hola",
                       hora="12:00", tipo=tipo, monto=monto, rol="")


def _lineas():
    participacion = Participacion()
    for _ in range(5):
        participacion.sumar(_registro("Carla", "C"))
    participacion.sumar(_registro("Beto", "B", TIPO_SUPERCHAT, "US$50.00"))
    participacion.sumar(_registro("Ana", "A", TIPO_SUPERCHAT,
                                  "100 diamantes"))
    participacion.sumar(_registro("Dani", "D", TIPO_SUPERCHAT,
                                  "200 diamantes"))
    return participacion.lineas(ORDEN_REGALOS)


class TestGuardarResumen(unittest.TestCase):

    def test_escribe_el_archivo_con_fecha_hora_y_contenido(self):
        with tempfile.TemporaryDirectory() as tmp:
            ruta = resumen_sesion.guardar(_lineas(), Path(tmp), ahora=AHORA)
            self.assertEqual(ruta, Path(tmp) / "2026-11-17 22-30.txt")
            self.assertEqual(ruta.read_text(encoding="utf-8"),
                             "Dani: 1 mensaje, 200 diamantes\n"
                             "Ana: 1 mensaje, 100 diamantes\n"
                             "Beto: 1 mensaje, 50,00 US$\n"
                             "Carla: 5 mensajes\n")

    def test_con_el_mismo_nombre_agrega_un_sufijo(self):
        with tempfile.TemporaryDirectory() as tmp:
            resumen_sesion.guardar(_lineas(), Path(tmp), ahora=AHORA)
            segunda = resumen_sesion.guardar(_lineas(), Path(tmp), ahora=AHORA)
            self.assertEqual(segunda,
                             Path(tmp) / "2026-11-17 22-30 (2).txt")

    def test_con_cincuenta_elimina_el_mas_viejo(self):
        with tempfile.TemporaryDirectory() as tmp:
            carpeta = Path(tmp)
            for minuto in range(50):
                momento = datetime(2026, 1, 1, 0, 0) + timedelta(minutes=minuto)
                (carpeta / f"{momento:%Y-%m-%d %H-%M}.txt").write_text(
                    "x", encoding="utf-8")
            resumen_sesion.guardar(_lineas(), carpeta, ahora=AHORA)
            nombres = sorted(ruta.name for ruta in carpeta.glob("*.txt"))
            self.assertEqual(len(nombres), 50)
            self.assertNotIn("2026-01-01 00-00.txt", nombres)
            self.assertIn("2026-11-17 22-30.txt", nombres)

    def test_sin_participacion_no_escribe_nada(self):
        with tempfile.TemporaryDirectory() as tmp:
            vacia = Participacion()
            self.assertIsNone(resumen_sesion.guardar(
                vacia.lineas(ORDEN_REGALOS), Path(tmp), ahora=AHORA))
            self.assertEqual(list(Path(tmp).glob("*.txt")), [])


if __name__ == "__main__":
    unittest.main()
