# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Los ajustes generales de la interacción y cómo se combinan con los medios.

Puro y sin wx. Única razón para cambiar: qué ajustes generales guarda la
interacción y cómo se pasan a lo que sale en el vídeo.
"""

from __future__ import annotations

import math

from guyrapu.core import archivos

VOLUMEN_POR_DEFECTO = 100


def _volumen(valor) -> int:
    if isinstance(valor, bool):
        return VOLUMEN_POR_DEFECTO
    try:
        numero = int(float(valor))
    except (TypeError, ValueError, OverflowError):
        return VOLUMEN_POR_DEFECTO
    if 0 <= numero <= 100:
        return numero
    return VOLUMEN_POR_DEFECTO


def cargar_volumen(ruta) -> int:
    """El volumen de los medios guardado, o 100 si falta, está roto o no vale."""
    datos = archivos.leer_json(ruta, {})
    if not isinstance(datos, dict):
        return VOLUMEN_POR_DEFECTO
    return _volumen(datos.get("volumen_medios"))


def guardar_volumen(ruta, volumen) -> None:
    """Guarda el volumen con un temporal para conservar el anterior."""
    archivos.escribir_json_atomico(
        ruta, {"volumen_medios": _volumen(volumen)}, indent=2)


def ganancia_total(ganancia_db, volumen):
    """La ganancia del medio más la del volumen general, en dB."""
    if volumen <= 0:
        return -100.0
    ganancia = 0.0 if ganancia_db is None else float(ganancia_db)
    return ganancia + 20 * math.log10(volumen / 100)
