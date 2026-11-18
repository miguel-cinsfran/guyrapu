# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Qué eventos de TikTok no se leen.

Funciones puras del filtrado: si el evento es viejo, si TikTok lo marcó como
histórico y cuántos me gusta pasan por ventana. Sin wx ni la librería.
"""

from __future__ import annotations


def es_previo_a_conexion(creado_ms, conectado_s, margen_s=5.0) -> bool:
    """¿El evento se creó más de `margen_s` antes de conectar? Ante la duda
    (sin hora, hora 0 o todavía sin conectar) es Falso: se lee."""
    try:
        if isinstance(creado_ms, bool):
            return False
        if not isinstance(creado_ms, (int, float)):
            return False
        if creado_ms <= 0:
            return False
        if conectado_s is None or isinstance(conectado_s, bool):
            return False
        return (creado_ms / 1000) < (float(conectado_s) - float(margen_s))
    except Exception:
        return False


def _creado_ms(evento):
    """ms de creación del evento (`common.create_time`); 0 si no se puede leer."""
    try:
        return getattr(getattr(evento, "common", None), "create_time", 0)
    except Exception:
        return 0


def es_historico(evento) -> bool:
    """¿TikTok lo marcó como mensaje viejo (`is_history` del sobre)? El cliente
    de la librería no copia esa marca a los eventos, así que la anota el
    envoltorio de `_envolver_marcador_historico`. Ante la duda, es Falso."""
    try:
        return bool(getattr(evento, "_historico", False))
    except Exception:
        return False


def debe_pasar_me_gusta(ultimo, ahora, intervalo=3.0) -> bool:
    """¿Este me gusta puede pasar? Como mucho UNO cada `intervalo` segundos:
    los me gusta llegan de a montones y saturarían el sonido. `ultimo` es el
    `time.monotonic()` del último que pasó, o None si aún no pasó ninguno.
    Ante la duda, pasa."""
    try:
        if ultimo is None:
            return True
        return (float(ahora) - float(ultimo)) >= float(intervalo)
    except (TypeError, ValueError):
        return True
