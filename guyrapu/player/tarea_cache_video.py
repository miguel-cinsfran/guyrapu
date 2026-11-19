# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Qué descarga de caché de vídeo está en curso y si suena el archivo local."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import threading


@dataclass(eq=False)
class TareaCacheVideo:
    """Identidad de una descarga de caché con evento propio."""

    video_id: str
    generacion: int
    destino: Path
    cancelacion: threading.Event = field(default_factory=threading.Event)

    def __post_init__(self):
        self.destino = Path(self.destino)


@dataclass
class EstadoCacheVideo:
    """Descarga vigente para el vídeo que suena y si suena el archivo local."""

    tarea: TareaCacheVideo | None = None
    local: bool = False

    def empezar(self, video_id, generacion, destino) -> TareaCacheVideo:
        if self.tarea is not None:
            self.tarea.cancelacion.set()
        self.tarea = TareaCacheVideo(video_id, generacion, destino)
        return self.tarea

    def recibir(self, tarea) -> bool:
        if self.tarea is not tarea:
            return False
        self.tarea = None
        return True

    def cancelar(self) -> None:
        if self.tarea is not None:
            self.tarea.cancelacion.set()
        self.tarea = None
        self.local = False
