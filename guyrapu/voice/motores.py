# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Fachada de los motores de voz registrados.

La aplicación pide por id y este módulo delega en el proveedor. Un id
desconocido se comporta como siempre: al crear cae en Prism, que lanza
`MotorNoDisponible`, y al listar devuelve una lista vacía.
"""

from __future__ import annotations

from guyrapu.voice import proveedores
from guyrapu.voice.proveedores.base import MotorNoDisponible

__all__ = ("MOTORES", "NOMBRES", "MotorNoDisponible", "crear_motor",
           "listar_voces")

MOTORES = tuple(proveedor.id for proveedor in proveedores.PROVEEDORES)
NOMBRES = {proveedor.id: proveedor.nombre
           for proveedor in proveedores.PROVEEDORES}


def crear_motor(motor, clave_elevenlabs=None):
    """Crea el motor pedido. Lanza `MotorNoDisponible` si no se puede.

    Para ElevenLabs, la clave se lee de `credenciales` cuando no se pasa (el
    archivo es del usuario y nunca vive en config.ini) y el proveedor importa
    su motor de forma perezosa.
    """
    proveedor = proveedores.obtener(motor)
    if proveedor is not None:
        return proveedor.crear(clave_elevenlabs)
    from guyrapu.voice.proveedores import prism
    return prism.MotorPrism(motor)


def listar_voces(motor, fabrica_contexto=None) -> list[str]:
    """Devuelve las voces de un motor sin tocar el del hilo de voz.

    El proveedor crea una instancia propia y la cierra. Lista vacía si el
    motor no está disponible (para ElevenLabs, sin clave guardada también es
    vacía).
    """
    proveedor = proveedores.obtener(motor)
    if proveedor is None:
        return []
    return proveedor.listar_voces(fabrica_contexto)
