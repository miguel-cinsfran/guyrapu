# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Fines de directo que se terminan con la app cerrada."""

from __future__ import annotations

from guyrapu.core import diagnostico
from guyrapu.youtube import credenciales

logger = diagnostico.obtener_logger(__name__)


def _guardar_token_si_hay(cliente) -> None:
    try:
        nuevo = cliente.token_actualizado()
    except Exception:
        nuevo = None
    if nuevo:
        try:
            credenciales.guardar_campo("token", nuevo)
        except Exception as error:
            logger.warning("no se pudo guardar el token actualizado: %s", error)
