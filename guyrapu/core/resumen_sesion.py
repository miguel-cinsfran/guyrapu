# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Archivo con el resumen de participación al terminar un directo.

Puro salvo el disco. Única razón para cambiar: cómo se guarda el resumen
de un directo, con qué nombre, con qué contenido y cuántos se conservan.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

MAXIMO = 50
FORMATO = "%Y-%m-%d %H-%M"


def guardar(lineas, carpeta, ahora=None) -> Path | None:
    """Escribe el resumen y elimina los más viejos. Sin líneas no escribe."""
    if not lineas:
        return None
    carpeta = Path(carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta = _ruta_libre(carpeta, ahora or datetime.now())
    ruta.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    _podar(carpeta)
    return ruta


def _ruta_libre(carpeta: Path, ahora: datetime) -> Path:
    base = ahora.strftime(FORMATO)
    ruta = carpeta / f"{base}.txt"
    sufijo = 2
    while ruta.exists():
        ruta = carpeta / f"{base} ({sufijo}).txt"
        sufijo += 1
    return ruta


def _podar(carpeta: Path) -> None:
    for ruta in sorted(carpeta.glob("*.txt"))[:-MAXIMO]:
        ruta.unlink()
