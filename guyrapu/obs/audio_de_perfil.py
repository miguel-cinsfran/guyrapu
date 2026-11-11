# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Los ajustes de audio que tienen que coincidir entre perfiles de OBS.

OBS abre un cuadro de reiniciar al cambiar de perfil cuando el perfil de
destino tiene otra frecuencia de muestreo u otra distribución de altavoces.
Igualar esos dos valores antes del cambio evita el cuadro; lo que se oye no
cambia, porque OBS sigue con el audio que está en marcha.
"""

from __future__ import annotations

from guyrapu.core import diagnostico
from guyrapu.obs import obs_cliente, perfil_en_disco

logger = diagnostico.obtener_logger(__name__)

CLAVES = ("SampleRate", "ChannelSetup")


def _advertir(mensaje, error):
    logger.warning("%s: %s", mensaje, error)


def _parametro(cliente, categoria, nombre, parada):
    respuesta = cliente.pedir(
        "GetProfileParameter",
        {"parameterCategory": categoria, "parameterName": nombre},
        parada)
    datos = (respuesta or {}).get("responseData", respuesta or {})
    valor = datos.get("parameterValue")
    if valor is None or valor == "":
        valor = datos.get("defaultParameterValue")
    return "" if valor is None else str(valor)


def audio_en_uso(cliente, parada=None):
    """El muestreo y los canales del perfil que está en uso."""
    audio = {}
    try:
        for clave in CLAVES:
            valor = _parametro(cliente, "Audio", clave, parada)
            if valor:
                audio[clave] = valor
    except (obs_cliente.ObsError, OSError) as error:
        _advertir("no se pudo leer el audio del perfil en uso de OBS", error)
        return {}
    return audio


def igualar(cliente, perfil, parada=None):
    """Deja el archivo del perfil de destino con el audio del perfil en uso."""
    try:
        audio = audio_en_uso(cliente, parada)
        if not audio:
            return False
        return perfil_en_disco.igualar_audio(perfil, audio)
    except (obs_cliente.ObsError, OSError) as error:
        logger.warning(
            "no se pudo igualar el audio del perfil %s de OBS: %s",
            perfil, error)
        return False


def poner_en_uso(cliente, audio, parada=None):
    """Pone al perfil recién creado, ya en uso, el audio que se leyó antes."""
    try:
        for clave, valor in (audio or {}).items():
            cliente.pedir("SetProfileParameter", {
                "parameterCategory": "Audio",
                "parameterName": clave,
                "parameterValue": str(valor),
            }, parada)
    except (obs_cliente.ObsError, OSError) as error:
        _advertir("no se pudo poner el audio del perfil de OBS", error)
