# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Qué total de me gusta del directo se conoce.

Puro y sin wx ni TikTokLive. Única razón para cambiar: qué total mandó
TikTok. Lo escribe el hilo de la captura y lo lee el de la interfaz, así que
va con candado como el registro de metas.
"""

from __future__ import annotations

import threading

_candado = threading.Lock()
_total = None


def anotar(total) -> None:
    """Guarda el total si es entero y no baja el que ya se conocía."""
    global _total
    try:
        numero = int(total)
    except (TypeError, ValueError):
        return
    with _candado:
        if _total is None or numero > _total:
            _total = numero


def total():
    """El último total conocido, o None si TikTok no lo mandó."""
    with _candado:
        return _total


def reiniciar() -> None:
    """Olvida el total de la conexión anterior."""
    global _total
    with _candado:
        _total = None
