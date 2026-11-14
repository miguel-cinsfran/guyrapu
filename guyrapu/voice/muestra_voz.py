# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Vista previa de una voz: una muestra a la vez por libVLC.

Su única razón para cambiar es cómo suena una muestra. No baja nada a disco:
libVLC abre la URL https directamente. Empezar otra corta la anterior y
`detener()` corta la que suena.
"""

from __future__ import annotations

import threading

from guyrapu.core import diagnostico
from guyrapu.core.idioma import _
from guyrapu.player import motor_vlc

logger = diagnostico.obtener_logger(__name__)

VOLUMEN = 100

_lock = threading.Lock()
_reproductor = None


def reproducir(origen, volumen=VOLUMEN):
    """Empieza la muestra y devuelve el reproductor; corta la anterior."""
    global _reproductor
    with _lock:
        _detener_sin_bloqueo()
        instancia = motor_vlc.instancia()
        if instancia is None:
            raise RuntimeError(_("libVLC no está disponible"))
        reproductor = motor_vlc.nuevo_reproductor(instancia)
        if reproductor is None:
            raise RuntimeError(_("libVLC no pudo crear un reproductor"))
        media = instancia.media_new(origen)
        if media is None:
            raise RuntimeError(_("libVLC no pudo abrir la muestra de voz"))
        reproductor.set_media(media)
        reproductor.audio_set_volume(volumen)
        if reproductor.play() == -1:
            raise RuntimeError(_("libVLC no pudo iniciar la vista previa"))
        _reproductor = reproductor
        return reproductor


def detener() -> None:
    """Corta la muestra que esté sonando."""
    with _lock:
        _detener_sin_bloqueo()


def _detener_sin_bloqueo() -> None:
    global _reproductor
    reproductor, _reproductor = _reproductor, None
    if reproductor is None:
        return
    try:
        reproductor.stop()
    except Exception as error:
        logger.debug("no se pudo detener la vista previa: %s", error)
