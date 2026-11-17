# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Dice si la cortina de pantalla de NVDA está puesta.

La cortina se reconoce por la matriz que Windows aplica a toda la pantalla
con la API de ampliación: con la cortina puesta los tres primeros valores
de la diagonal quedan en cero. Cualquier fallo devuelve None, que es
desconocido, y se anota en diagnóstico.
"""

from __future__ import annotations

import ctypes
import os

from guyrapu.core import diagnostico

logger = diagnostico.obtener_logger(__name__)


class _EfectoDeColor(ctypes.Structure):
    _fields_ = [("transform", ctypes.c_float * 25)]


def es_cortina(matriz) -> bool:
    """True si los tres primeros valores de la diagonal están en cero."""
    return matriz[0] == 0 and matriz[6] == 0 and matriz[12] == 0


def cortina_puesta() -> bool | None:
    """True si la cortina está puesta, False si no, None si no se pudo saber."""
    if os.name != "nt":
        logger.debug("No se puede consultar la cortina de pantalla de NVDA "
                     "fuera de Windows")
        return None
    try:
        biblioteca = ctypes.WinDLL("Magnification.dll")
        biblioteca.MagInitialize.argtypes = []
        biblioteca.MagInitialize.restype = ctypes.c_bool
        biblioteca.MagGetFullscreenColorEffect.argtypes = [
            ctypes.POINTER(_EfectoDeColor)]
        biblioteca.MagGetFullscreenColorEffect.restype = ctypes.c_bool
        biblioteca.MagUninitialize.argtypes = []
        biblioteca.MagUninitialize.restype = ctypes.c_bool
        if not biblioteca.MagInitialize():
            logger.debug("MagInitialize falló al consultar la cortina de "
                         "pantalla de NVDA")
            return None
        try:
            efecto = _EfectoDeColor()
            if not biblioteca.MagGetFullscreenColorEffect(ctypes.byref(efecto)):
                logger.debug("MagGetFullscreenColorEffect falló al consultar "
                             "la cortina de pantalla de NVDA")
                return None
            return es_cortina(efecto.transform)
        finally:
            biblioteca.MagUninitialize()
    except Exception as exc:
        logger.debug("No se pudo consultar la cortina de pantalla de NVDA: %s",
                     exc)
        return None
