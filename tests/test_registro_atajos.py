# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Una acción nueva se declara una sola vez y llega a las seis tablas."""

import unittest

from guyrapu.core import registro_atajos


class TestRegistroUnico(unittest.TestCase):

    def test_una_entrada_nueva_llega_a_las_seis_tablas(self):
        editable = registro_atajos.Accion(
            "accion_prueba", "ctrl+shift+y", "Acción de prueba",
            registro_atajos.REPRODUCTOR, True, True)
        fija = registro_atajos.Accion(
            "fija_prueba", "f7", "Fija de prueba",
            registro_atajos.FIJOS_NAVEGACION, False, False)
        registro_atajos.ACCIONES.extend([editable, fija])
        try:
            predeterminados = dict(registro_atajos.predeterminados())
            fijos_defaults = registro_atajos.fijos_defaults()
            fijos = registro_atajos.fijos()
            grupos = dict(registro_atajos.grupos())
            areas = registro_atajos.areas()
            etiquetas = registro_atajos.etiquetas()
            self.assertEqual(predeterminados["accion_prueba"], "ctrl+shift+y")
            self.assertEqual(fijos_defaults["fija_prueba"], "f7")
            self.assertIn("fija_prueba", fijos)
            self.assertIn("accion_prueba", grupos["Reproductor (Ctrl)"])
            self.assertIn("fija_prueba", grupos["Ventana y navegación (fijos)"])
            self.assertEqual(areas["accion_prueba"], "ctrl")
            self.assertIsNone(areas["fija_prueba"])
            self.assertEqual(etiquetas["accion_prueba"], "Acción de prueba")
            self.assertEqual(etiquetas["fija_prueba"], "Fija de prueba")
        finally:
            del registro_atajos.ACCIONES[-2:]
