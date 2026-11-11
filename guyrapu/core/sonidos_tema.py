# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Qué archivo suena para un evento dentro de un tema de sonidos.

El tema manda, pero el predeterminado respalda. Primero `<evento>.wav` en
el tema; si no, el archivo del sonido que `eventos_sonido.SONIDOS` le
asigna al evento. Si el tema no trae ninguno de los dos, se repite la
búsqueda en el tema predeterminado. La existencia se mira acá, al cargar
los sonidos, nunca al reproducir.
"""

from __future__ import annotations

from pathlib import Path

from guyrapu.core import eventos_sonido

TEMA_PREDETERMINADO = "default"


def _candidatas(carpeta_tema: Path, evento: str) -> tuple[Path, ...]:
    """Los cuatro archivos, en el orden en que se prueban."""
    asignado = eventos_sonido.SONIDOS.get(evento, evento)
    predeterminado = carpeta_tema.parent / TEMA_PREDETERMINADO
    return (carpeta_tema / f"{evento}.wav",
            carpeta_tema / f"{asignado}.wav",
            predeterminado / f"{evento}.wav",
            predeterminado / f"{asignado}.wav")


def _primera_existente(rutas: tuple[Path, ...]) -> Path | None:
    for ruta in rutas:
        if ruta.is_file():
            return ruta
    return None


def ruta_evento(carpeta_tema: Path, evento: str) -> Path:
    """Ruta del archivo que suena para `evento` en `carpeta_tema`.

    Busca el evento en el tema, el asignado en el tema, el evento en el
    predeterminado y el asignado en el predeterminado, en ese orden. Si
    no hay ninguno, devuelve la del evento en el tema, que el
    reproductor registra como `omitido=sin_archivo`.
    """
    candidatas = _candidatas(carpeta_tema, evento)
    elegida = _primera_existente(candidatas)
    return elegida or candidatas[0]
