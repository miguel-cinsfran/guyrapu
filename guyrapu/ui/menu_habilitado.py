# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Cómo se prende y apaga un elemento de menú.

A diferencia de un control, un elemento deshabilitado se sigue recorriendo
con las flechas y NVDA dice «no disponible»: por eso la regla de los
controles no lo cuenta.
"""

from __future__ import annotations

from guyrapu.core import diagnostico

logger = diagnostico.obtener_logger(__name__)


def habilitar(item, activo) -> None:
    """Prende o apaga un elemento de menú que wx todavía no destruyó."""
    try:
        item.Enable(activo)
    except Exception as error:
        logger.debug("no se pudo cambiar el estado del menú: %s", error)


def habilitar_varios(items, activo) -> None:
    """Prende o apaga cada elemento de la lista de menú."""
    for item in items:
        habilitar(item, activo)
