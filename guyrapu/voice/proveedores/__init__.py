# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Registro ordenado de los proveedores de voz.

Importar el paquete no importa Prism ni ptts: las bibliotecas de los motores
locales se cargan recién al crear uno.
"""

from __future__ import annotations

from guyrapu.voice.proveedores.elevenlabs import PROVEEDOR_ELEVENLABS
from guyrapu.voice.proveedores.phonon import PROVEEDOR_PHONON
from guyrapu.voice.proveedores.piper import PROVEEDOR_PIPER
from guyrapu.voice.proveedores.prism import PROVEEDOR_ONECORE, PROVEEDOR_SAPI

PROVEEDORES = (PROVEEDOR_SAPI, PROVEEDOR_ONECORE, PROVEEDOR_ELEVENLABS,
               PROVEEDOR_PHONON, PROVEEDOR_PIPER)


def obtener(id):
    """Devuelve el proveedor con ese id, o None si no está registrado."""
    for proveedor in PROVEEDORES:
        if proveedor.id == id:
            return proveedor
    return None
