# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Qué archivo suena para un evento dentro de un tema de sonidos.

La carpeta del tema manda: si trae `<evento>.wav`, suena ese. Si no, el
archivo del sonido que `eventos_sonido.SONIDOS` le asigna al evento. La
existencia se mira acá, al cargar los sonidos, nunca al reproducir.
"""

from __future__ import annotations

from pathlib import Path

from guyrapu.core import eventos_sonido


def ruta_evento(carpeta_tema: Path, evento: str) -> Path:
    """Ruta del archivo que suena para `evento` en `carpeta_tema`.

    Si no existe ni el archivo del evento ni el del sonido asignado,
    devuelve la del evento, que el reproductor registra como
    `omitido=sin_archivo`.
    """
    propia = carpeta_tema / f"{evento}.wav"
    if propia.is_file():
        return propia
    asignada = carpeta_tema / f"{eventos_sonido.SONIDOS.get(evento, evento)}.wav"
    if asignada.is_file():
        return asignada
    return propia
