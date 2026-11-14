# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Cómo se lee una release de GitHub para elegir el paquete, sin interfaz.

El paquete compatible es un activo `.zip` con su `.sha256` en la misma
release, y las dos URL tienen que ser https.
"""

from __future__ import annotations

from typing import NamedTuple

from guyrapu.core.versiones import version_como_tupla


class PaqueteElegido(NamedTuple):
    """Lo que `elegir_paquete` saca de la respuesta JSON de la API."""

    version: str
    notas: str
    url_zip: str
    url_firma: str
    tamanio: int | None


def _es_https(url: object) -> bool:
    return isinstance(url, str) and url.lower().startswith("https://")


def elegir_paquete(release: dict | None) -> PaqueteElegido | None:
    """Saca versión, notas y URLs del paquete de la respuesta JSON de la API.

    Paquete compatible: un activo cuyo nombre termina en `.zip` y otro
    activo llamado exactamente igual más `.sha256`. Si hay varios zip
    con firma, None por ambiguo. No se depende de ningún nombre de
    archivo en particular. Las URL tienen que ser https.
    """
    if not isinstance(release, dict):
        return None
    activos = release.get("assets")
    if not isinstance(activos, list):
        return None
    nombres = {}
    for activo in activos:
        if not isinstance(activo, dict):
            continue
        nombre = activo.get("name")
        url = activo.get("browser_download_url")
        if isinstance(nombre, str) and isinstance(url, str):
            nombres[nombre] = url
    candidatos = [nombre for nombre in nombres
                  if nombre.lower().endswith(".zip")
                  and (nombre + ".sha256") in nombres]
    if len(candidatos) != 1:
        return None
    nombre_zip = candidatos[0]
    url_zip = nombres[nombre_zip]
    url_firma = nombres[nombre_zip + ".sha256"]
    if not _es_https(url_zip) or not _es_https(url_firma):
        return None
    version = release.get("tag_name", "")
    if not isinstance(version, str) or version_como_tupla(version) is None:
        return None
    notas = release.get("body") or ""
    if not isinstance(notas, str):
        notas = ""
    tamanio = None
    for activo in activos:
        if (isinstance(activo, dict)
                and activo.get("name") == nombre_zip
                and isinstance(activo.get("size"), int)):
            tamanio = activo.get("size")
    return PaqueteElegido(version=version, notas=notas, url_zip=url_zip,
                           url_firma=url_firma, tamanio=tamanio)
