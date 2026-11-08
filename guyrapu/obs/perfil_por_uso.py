# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Qué perfil de OBS corresponde a una plataforma según config.ini.

Puro salvo la lectura de `config.ini`, que se hace en el momento igual que
en `grabar_al_transmitir`. La ruta es inyectable para las pruebas.
"""

from __future__ import annotations

import configparser

from guyrapu.core import diagnostico, ini_tipado, paths, plataformas

logger = diagnostico.obtener_logger(__name__)

CLAVES = {
    "horizontal": "perfil_horizontal",
    "vertical": "perfil_vertical",
}


def _leer(orientacion, ruta=None) -> str:
    clave = CLAVES.get(orientacion)
    if clave is None:
        return ""
    try:
        parser = configparser.ConfigParser(interpolation=None)
        parser.read(ruta or paths.config_ini(), encoding="utf-8")
        return ini_tipado.leer_texto(parser, "transmision", clave)
    except Exception as error:
        logger.debug("no se pudo leer %s: %s", clave, error)
        return ini_tipado.predeterminado("transmision", clave)


def perfil_elegido(plataforma, ruta=None):
    """El perfil configurado para la orientación de la plataforma.

    None si la plataforma no está en el registro: quien llama la trata como
    nombre de perfil. Cadena vacía si la configuración pide no cambiar el
    perfil que tenga OBS.
    """
    datos = plataformas.obtener(plataforma)
    if datos is None:
        return None
    return _leer(datos.orientacion, ruta)
