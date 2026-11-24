# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Detector del id de plataforma escrito como literal fuera del registro."""

from __future__ import annotations

import ast

from tests.reglas_detectores import Hallazgo

_ARCHIVO_DE_PLATAFORMAS = "guyrapu/core/plataformas.py"
_IDS_DE_PLATAFORMA = ("youtube", "tiktok")


def detectar_ids_de_plataforma(archivo: str,
                               arbol: ast.Module) -> list[Hallazgo]:
    """El id de cada plataforma solo se escribe en su registro."""
    if archivo == _ARCHIVO_DE_PLATAFORMAS:
        return []
    hallazgos = [
        Hallazgo(archivo, nodo.lineno)
        for nodo in ast.walk(arbol)
        if isinstance(nodo, ast.Constant) and nodo.value in _IDS_DE_PLATAFORMA
    ]
    return sorted(hallazgos, key=lambda hallazgo: hallazgo.linea)
