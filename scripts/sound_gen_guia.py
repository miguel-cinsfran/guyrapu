# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Sonidos fijos de la guía de encuadre de la cámara.

Carpeta fija `sounds/guia/`, igual para los dos temas: no son eventos y
por eso no entran en TEMAS. Los pitidos y el tono del centro se generan
en memoria con `guyrapu/camera/tono_guia.py`; acá quedan solo `listo`
(confirmación que sube) y `sin_rostro` (zumbido grave y corto).
"""

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
GUIA_DIR = RAIZ / "sounds" / "guia"

E5, A5 = 659.25, 880.00
D3 = 146.83


def _base():
    raiz = str(RAIZ)
    if raiz not in sys.path:
        sys.path.insert(0, raiz)
    from scripts import sound_gen
    return sound_gen


def gen_guia_listo():
    # Confirmación de que quedó centrada: dos notas que suben, E5→A5.
    base = _base()
    n1 = base._perc(base._seno(E5, 0.09, 0.32), 0.004, 0.07)
    n2 = base._perc(base._seno(A5, 0.16, 0.34), 0.004, 0.12)
    return base._normalizar(base._concat(n1, n2), 0.7)


def gen_guia_sin_rostro():
    # Zumbido grave y corto: no hay rostro a la vista.
    base = _base()
    return base._normalizar(
        base._perc(base._seno(D3, 0.20, 0.40), 0.005, 0.15), 0.65)


GUIA = {"listo.wav": gen_guia_listo, "sin_rostro.wav": gen_guia_sin_rostro}


def generar_guia(destino: Path | None = None,
                 sobreescribir: bool = False) -> int:
    base = _base()
    destino = destino or GUIA_DIR
    destino.mkdir(parents=True, exist_ok=True)
    n = 0
    for nombre, generador in GUIA.items():
        ruta = destino / nombre
        if ruta.exists() and not sobreescribir:
            print(f"  [saltar]  {nombre}  (ya existe)")
            continue
        base._escribir_wav(ruta, generador(), pan=0.0)
        print(f"  [crear ]  {nombre:20s}  {ruta.stat().st_size:6d} bytes")
        n += 1
    return n
