# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""El formato de los archivos de un perfil de OBS en disco.

Lee y escribe `basic.ini` y `service.json` de la carpeta de un perfil sin
hablar con el WebSocket. Los ajustes viven en `ajustes_perfil` y los
codificadores de la PC, en `codificadores_obs`.
"""

from __future__ import annotations

import configparser

from guyrapu.core import paths


def carpeta_de_perfil(nombre):
    """La carpeta del perfil, la que lleva ese nombre en su basic.ini."""
    try:
        carpetas = list(paths.carpeta_obs("perfiles").iterdir())
    except OSError:
        return None
    for carpeta in carpetas:
        basic = carpeta / "basic.ini"
        if not basic.is_file():
            continue
        analizador = configparser.ConfigParser(interpolation=None)
        try:
            analizador.read(basic, encoding="utf-8-sig")
        except (OSError, UnicodeError, configparser.Error):
            continue
        if analizador.get("General", "Name", fallback="") == nombre:
            return carpeta
    return None
