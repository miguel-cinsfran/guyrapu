# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Enciende una sola vez los atajos de escena fuera de la aplicación.

Las configuraciones viejas guardaron `[transmision] escena_atajos_globales`
apagado al completarse con los valores de fábrica, aunque el usuario nunca
lo hubiera tocado. Puro y sin wx: `config` lo llama al cargar config.ini.
"""

from __future__ import annotations

VERSION_ESCENA_GLOBAL = 1

_CLAVE_VERSION = "version_escena_global"


def migrar(parser, ruta, guardar, guardar_varias=None) -> None:
    """Enciende los atajos de escena una sola vez.

    La marca vive en `[sesion] version_escena_global` y se graba aunque no
    haya nada que cambiar, para no volver a tocar lo que el usuario apague
    después."""
    try:
        version = parser.getint("sesion", _CLAVE_VERSION)
    except Exception:
        version = 0
    if version >= VERSION_ESCENA_GLOBAL:
        return
    cambios = [("transmision", "escena_atajos_globales", "true"),
               ("sesion", _CLAVE_VERSION, str(VERSION_ESCENA_GLOBAL))]
    for seccion, clave, valor in cambios:
        _fijar(parser, seccion, clave, valor)
    _escribir(ruta, cambios, guardar, guardar_varias)


def _fijar(parser, seccion, clave, valor) -> None:
    if not parser.has_section(seccion):
        parser.add_section(seccion)
    parser.set(seccion, clave, valor)


def _escribir(ruta, cambios, guardar, guardar_varias) -> None:
    if guardar_varias is not None:
        guardar_varias(ruta, cambios)
        return
    for seccion, clave, valor in cambios:
        guardar(ruta, seccion, clave, valor)
