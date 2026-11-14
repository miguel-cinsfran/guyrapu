# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Ajuste del tono de la voz principal desde el teclado.

Vive fuera de `gui.py` porque esa ventana ya pasa del tope de líneas. Mueve
solo la voz principal, como las teclas F de velocidad y volumen.
"""

from __future__ import annotations

from guyrapu.core import anuncio_ajuste
from guyrapu.core import paths
from guyrapu.core.config import guardar_opcion
from guyrapu.core.idioma import _
from guyrapu.ui.accesibilidad import anunciar
from guyrapu.voice import proveedores

TONO_MINIMO = 0
TONO_MAXIMO = 100


def ajustar_tono(frame, delta: int) -> None:
    """Mueve el tono, lo guarda y lo anuncia; avisa si el motor no lo admite."""
    proveedor = proveedores.obtener(frame._worker.motor_activo())
    if proveedor is not None and not proveedor.capacidades.tono:
        # El nombre visible trae un descriptor tras la coma: el aviso nombra
        # solo el motor.
        nombre = _(proveedor.nombre).split(",", 1)[0].strip()
        anunciar(_("{motor} no permite cambiar el tono.").format(motor=nombre))
        return
    valor = max(TONO_MINIMO, min(TONO_MAXIMO,
                                 frame._worker.get_tono() + delta))
    frame._worker.cambiar_tono(valor)
    guardar_opcion(paths.config_ini(), "voz", "tono", str(valor))
    anunciar(anuncio_ajuste.anuncio_tono(valor))
