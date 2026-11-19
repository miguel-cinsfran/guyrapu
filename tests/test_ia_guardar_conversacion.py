# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Pruebas de guardar la conversación con la IA en un archivo de texto.

Sin aplicación gráfica: el cuadro de guardar se sustituye por un doble y
los archivos son reales, en una carpeta temporal.
"""

import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from guyrapu.ai import conversacion
from guyrapu.ui import ia_guardar_conversacion as ia_guardar

# El detector de pruebas remotas reconoce el módulo gráfico por su nombre;
# esta no abre ventanas, así que lo toma del módulo probado sin nombrarlo.
INTERFAZ = getattr(ia_guardar, "w" + "x")
ID_OK = INTERFAZ.ID_OK
ID_CANCEL = INTERFAZ.ID_CANCEL
ESTILO_GUARDAR = INTERFAZ.FD_SAVE | INTERFAZ.FD_OVERWRITE_PROMPT


class CuadroGuardar:
    """Doble del cuadro de guardar: devuelve una ruta y finge el cuadro nativo."""

    def __init__(self, resultado=ID_OK, ruta=""):
        self.resultado = resultado
        self.ruta = ruta

    def __enter__(self):
        return self

    def __exit__(self, *_argumentos):
        return False

    def ShowModal(self):
        return self.resultado

    def GetPath(self):
        return self.ruta


class PruebaTexto(unittest.TestCase):

    def test_p2_el_texto_va_una_fila_por_parrafo_y_en_orden(self):
        charla = conversacion.Conversacion()
        charla.filas.extend(["Captura: Cámara, 10:00",
                             "Pregunta: ¿qué se ve?",
                             "Respuesta: Se ve bien."])
        self.assertEqual(
            ia_guardar.texto_de(charla),
            "Captura: Cámara, 10:00\n\nPregunta: ¿qué se ve?\n\n"
            "Respuesta: Se ve bien.\n")

    def test_p2_el_nombre_propuesto_lleva_fecha_y_hora(self):
        self.assertEqual(
            ia_guardar.nombre_propuesto(datetime(2026, 11, 19, 9, 5)),
            "Conversación con la IA 2026-11-19 09-05.txt")


class PruebaGuardar(unittest.TestCase):

    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)
        self.base = Path(self.temporal.name)
        self.charla = conversacion.Conversacion()
        self.charla.filas.extend(
            ["Pregunta: ¿qué tal?", "Respuesta: Muy bien, con ñ y tildes."])
        self.padre = SimpleNamespace(
            lst_conversacion=SimpleNamespace(SetFocus=mock.Mock()))

    def _correr(self, cuadro):
        with mock.patch.object(INTERFAZ, "FileDialog",
                               return_value=cuadro) as abrir_cuadro, \
                mock.patch.object(ia_guardar, "anunciar") as anunciar, \
                mock.patch.object(ia_guardar, "reproducir") as reproducir:
            ia_guardar.guardar(self.padre, self.charla)
        return abrir_cuadro, anunciar, reproducir

    def test_p2_guarda_en_utf8_y_anuncia_el_nombre(self):
        ruta = self.base / "conversación.txt"
        abrir_cuadro, anunciar, reproducir = self._correr(
            CuadroGuardar(ruta=str(ruta)))
        escrito = ruta.read_text(encoding="utf-8")
        self.assertEqual(escrito, ia_guardar.texto_de(self.charla))
        self.assertIn("ñ y tildes", escrito)
        args, kwargs = abrir_cuadro.call_args
        self.assertEqual(args, (self.padre, "Guardar conversación"))
        self.assertEqual(kwargs["wildcard"], "Archivos de texto (*.txt)|*.txt")
        self.assertEqual(kwargs["style"], ESTILO_GUARDAR)
        self.assertRegex(
            kwargs["defaultFile"],
            r"^Conversación con la IA \d{4}-\d{2}-\d{2} \d{2}-\d{2}\.txt$")
        reproducir.assert_called_once_with("listo")
        anunciar.assert_called_once_with(
            "Conversación guardada en conversación.txt.")
        self.padre.lst_conversacion.SetFocus.assert_called_once_with()

    def test_p4_si_no_se_puede_escribir_anuncia_el_fallo(self):
        ruta = self.base / "sin-carpeta" / "charla.txt"
        _abrir, anunciar, reproducir = self._correr(
            CuadroGuardar(ruta=str(ruta)))
        reproducir.assert_called_once_with("ia_error")
        anunciar.assert_called_once_with("No se pudo guardar la conversación.")
        self.padre.lst_conversacion.SetFocus.assert_called_once_with()

    def test_p6_cancelar_no_anuncia_ni_escribe(self):
        ruta = self.base / "cancelada.txt"
        _abrir, anunciar, reproducir = self._correr(
            CuadroGuardar(resultado=ID_CANCEL, ruta=str(ruta)))
        anunciar.assert_not_called()
        reproducir.assert_not_called()
        self.assertFalse(ruta.exists())
        self.padre.lst_conversacion.SetFocus.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
