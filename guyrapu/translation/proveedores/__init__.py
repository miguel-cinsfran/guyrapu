# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Registro ordenado de los proveedores de traducción.

Importar el paquete no habla por la red: httpx se carga recién al traducir.
"""

from __future__ import annotations

from guyrapu.translation.proveedores.google import PROVEEDOR_GOOGLE

PROVEEDORES = (PROVEEDOR_GOOGLE,)


def obtener(id):
    """Devuelve el proveedor con ese id, o None si no está registrado."""
    for proveedor in PROVEEDORES:
        if proveedor.id == id:
            return proveedor
    return None
