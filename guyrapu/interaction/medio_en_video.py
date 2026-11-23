# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Cómo un medio de la biblioteca entra en una pieza del vídeo.

Puro y sin wx. Única razón para cambiar: resolver un medio por nombre y
sumarlo a los datos de una pieza ajustando el tiempo que se muestra.
"""

from __future__ import annotations

from guyrapu.core import paths
from guyrapu.interaction import medios_guardados


def resolver(nombre):
    """El medio de la biblioteca con ese nombre, o None si ya no está."""
    return medios_guardados.medio_para_video(
        medios_guardados.cargar(paths.medios()),
        paths.carpeta_medios(), nombre)


def con_medio(datos, segundos, medio):
    """Los datos y los segundos de la pieza con el medio sumado, si lo hay."""
    if medio is None:
        return datos, segundos
    con = dict(datos)
    con["medio"] = medio
    if medio["tipo"] in ("sonido", "video") and medio["duracion"]:
        segundos = max(1, medio["duracion"])
    return con, segundos
