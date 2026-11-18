# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Cómo se escribe la transcripción de una ventana del carril.

Arma una línea por paso con la tecla, la fase, lo que NVDA dijo y los datos
del foco, lee y escribe la transcripción aprobada, y devuelve el diff cuando
la nueva difiere. Es puro: no toca NVDA, ni Windows, ni ventanas.
"""

from __future__ import annotations

import difflib
from pathlib import Path

CARPETA = Path(__file__).resolve().parent / "transcripciones"


def _habla(paso) -> str:
    dicho = " ".join(str(evento.get("texto") or "")
                     for evento in paso.get("habla") or ()).strip()
    nombre = str((paso.get("foco") or {}).get("nombre") or "").strip()
    if nombre and dicho.endswith(f"{nombre} {nombre}"):
        return dicho[:-len(nombre) - 1]
    return dicho


def _linea(paso) -> str:
    foco = paso.get("foco") or {}
    estados = sorted(str(estado) for estado in foco.get("estados") or ())
    rol = foco.get("rol_nombre") or foco.get("rol")
    return (f"tecla={paso.get('tecla')} fase={paso.get('fase')} "
            f"dijo={_habla(paso)!r} foco={{nombre={foco.get('nombre')!r}, "
            f"rol={rol!r}, estados={estados!r}, "
            f"valor={foco.get('valor')!r}, atajo={foco.get('atajo')!r}}}")


def texto(datos) -> str:
    """Una línea por paso, sin horas, milisegundos, hwnd ni pid."""
    lineas = [_linea(paso) for paso in datos.get("pasos") or ()]
    return "\n".join(lineas) + ("\n" if lineas else "")


def diferencia(aprobada: str, nueva: str) -> str:
    return "".join(difflib.unified_diff(
        aprobada.splitlines(keepends=True),
        nueva.splitlines(keepends=True),
        fromfile="aprobada", tofile="nueva"))


def _ruta(nombre, carpeta=None) -> Path:
    return Path(carpeta or CARPETA) / f"{nombre}.txt"


def leer(nombre, carpeta=None):
    """La transcripción aprobada, o None si todavía no hay."""
    try:
        return _ruta(nombre, carpeta).read_text(encoding="utf-8")
    except FileNotFoundError:
        return None


def escribir(nombre, contenido, carpeta=None) -> Path:
    ruta = _ruta(nombre, carpeta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(contenido, encoding="utf-8", newline="\n")
    return ruta


def comparar(nombre, nueva, aprobar=False, carpeta=None) -> str:
    """Guarda la primera, o la nueva si se aprueba, y devuelve el diff."""
    aprobada = leer(nombre, carpeta)
    if aprobar or aprobada is None:
        escribir(nombre, nueva, carpeta)
        return ""
    return diferencia(aprobada, nueva)
