# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Proveedor de voz de ElevenLabs, en la nube.

`motor_elevenlabs` se importa de forma perezosa: quien no usa ElevenLabs no
lo carga.
"""

from __future__ import annotations

from guyrapu.core import diagnostico
from guyrapu.core.idioma import N_
from guyrapu.voice.proveedores.base import (
    Capacidades,
    MotorNoDisponible,
    Proveedor,
)

logger = diagnostico.obtener_logger(__name__)

_LICENCIA = N_("Servicio en la nube, según tu cuenta de ElevenLabs")


def crear(clave_elevenlabs=None):
    from guyrapu.voice import motor_elevenlabs

    if clave_elevenlabs is None:
        from guyrapu.youtube import credenciales
        clave_elevenlabs = credenciales.cargar().get("elevenlabs_clave", "")
    return motor_elevenlabs.MotorElevenLabs(clave_elevenlabs)


def listar_voces(fabrica_contexto=None) -> list[str]:
    try:
        instancia = crear()
    except MotorNoDisponible:
        return []
    try:
        return list(instancia.voces())
    finally:
        try:
            instancia.cerrar()
        except Exception as error:
            logger.debug("no se pudo cerrar el motor de prueba: %s", error)


PROVEEDOR_ELEVENLABS = Proveedor(
    id="elevenlabs",
    nombre=N_("ElevenLabs, en la nube"),
    licencia=_LICENCIA,
    capacidades=Capacidades(streaming=False, tono=False, nube=True),
    crear=crear,
    listar_voces=listar_voces,
)
