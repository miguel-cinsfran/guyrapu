# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Registro ordenado de los proveedores de voz.

Importar el paquete no importa Prism: la biblioteca de los motores de
Windows se carga recién al crear uno.
"""

from __future__ import annotations

from guyrapu.voice.proveedores.elevenlabs import PROVEEDOR_ELEVENLABS
from guyrapu.voice.proveedores.prism import PROVEEDOR_ONECORE, PROVEEDOR_SAPI

PROVEEDORES = (PROVEEDOR_SAPI, PROVEEDOR_ONECORE, PROVEEDOR_ELEVENLABS)


def obtener(id):
    """Devuelve el proveedor con ese id, o None si no está registrado."""
    for proveedor in PROVEEDORES:
        if proveedor.id == id:
            return proveedor
    return None
