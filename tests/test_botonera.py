# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Las páginas de Interacción y Perfiles de OBS usan la botonera común."""

import ast
import unittest
from pathlib import Path

PAGINAS = (
    "comandos_ventana.py", "disparadores_ventana.py", "encuestas_ventana.py",
    "estilos_ventana.py", "medios_ventana.py",
    "mensajes_automaticos_ventana.py", "metas_ventana.py",
    "palabras_bloqueadas_ventana.py", "preguntas_ventana.py",
    "obs_pagina_perfiles.py",
)


def _usa_botonera(ruta):
    arbol = ast.parse(ruta.read_text(encoding="utf-8"))
    for nodo in ast.walk(arbol):
        if not isinstance(nodo, ast.ImportFrom):
            continue
        if nodo.module == "guyrapu.ui.botonera":
            return True
        if nodo.module == "guyrapu.ui" and any(
                nombre.name == "botonera" for nombre in nodo.names):
            return True
    return False


class TestBotonera(unittest.TestCase):

    def test_las_diez_paginas_usan_la_botonera(self):
        raiz = Path(__file__).resolve().parent.parent
        for nombre in PAGINAS:
            self.assertTrue(
                _usa_botonera(raiz / "guyrapu" / "ui" / nombre),
                f"{nombre} no usa la botonera")


if __name__ == "__main__":
    unittest.main()
