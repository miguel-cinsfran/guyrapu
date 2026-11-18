# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""El PNG del fondo de una tarjeta: dónde y cómo se guarda en disco."""

from __future__ import annotations

import hashlib
import os

from guyrapu.core import paths

_ESPERA_BORRADO = 0.5
_INTENTOS_BORRADO = 4


def _podar(carpeta, actual) -> None:
    archivos = sorted(carpeta.glob("*.png"),
                      key=lambda ruta: ruta.stat().st_mtime)
    while len(archivos) > 20:
        viejo = next((ruta for ruta in archivos if ruta != actual), None)
        if viejo is None:
            break
        viejo.unlink()
        archivos.remove(viejo)


def guardar_fondo(png, ancho, alto, estilo, escala):
    carpeta = paths.fondos_de_avisos()
    valores = "|".join(str(valor) for valor in (
        ancho, alto, str(estilo.get("color_fondo", "#000000")),
        float(estilo.get("opacidad_fondo", 0) or 0),
        str(estilo.get("esquinas", "rectas")) == "redondeadas",
        bool(estilo.get("sombra", False)), escala))
    resumen = hashlib.sha1(valores.encode("utf-8")).hexdigest()[:12]
    ruta = carpeta / f"fondo-{resumen}.png"
    if ruta.exists():
        os.utime(ruta, None)
    else:
        carpeta.mkdir(parents=True, exist_ok=True)
        ruta.write_bytes(png)
    _podar(carpeta, ruta)
    return ruta


def borrar(ruta, esperar) -> None:
    for _intento in range(_INTENTOS_BORRADO):
        try:
            ruta.unlink()
            return
        except PermissionError:
            esperar(_ESPERA_BORRADO)
