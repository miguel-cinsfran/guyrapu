# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Escucha previa de un medio con libVLC, sin mostrar vídeo.

Sin wx: el reproductor es de la instancia compartida y lo usa la página de
medios. Se suelta al cerrar la ventana o al pedir Escuchar otra vez.
"""

from __future__ import annotations

from guyrapu.core import diagnostico
from guyrapu.music import sonoridad
from guyrapu.player import motor_vlc

logger = diagnostico.obtener_logger(__name__)


class EscuchaPrevia:
    """Un reproductor propio para oír el audio de un medio elegido."""

    def __init__(self):
        self._reproductor = None

    def reproducir(self, ruta, ganancia=0.0) -> bool:
        """Empieza a sonar el archivo con la ganancia pedida."""
        self.detener()
        instancia = motor_vlc.instancia()
        if instancia is None:
            return False
        reproductor = motor_vlc.nuevo_reproductor(instancia)
        if reproductor is None:
            return False
        try:
            reproductor.audio_set_volume(
                sonoridad.volumen_efectivo(100, ganancia))
        except Exception as exc:
            logger.debug("No se pudo aplicar el volumen al escuchar: %s", exc)
        try:
            media = instancia.media_new(str(ruta))
            media.add_option(":no-video")
            reproductor.set_media(media)
        except Exception as exc:
            logger.debug("No se pudo preparar el medio para escucharlo: %s", exc)
            self._soltar(reproductor)
            return False
        if reproductor.play() == -1:
            self._soltar(reproductor)
            return False
        self._reproductor = reproductor
        return True

    def sonando(self) -> bool:
        """Si el reproductor sigue sonando."""
        if self._reproductor is None:
            return False
        try:
            return bool(self._reproductor.is_playing())
        except Exception as exc:
            logger.debug("No se pudo preguntar si el medio suena: %s", exc)
            return False

    def detener(self) -> None:
        """Detiene y suelta el reproductor."""
        reproductor = self._reproductor
        self._reproductor = None
        if reproductor is not None:
            self._soltar(reproductor)

    def _soltar(self, reproductor) -> None:
        try:
            reproductor.stop()
        except Exception as exc:
            logger.debug("No se pudo detener la escucha previa: %s", exc)
        try:
            reproductor.release()
        except Exception as exc:
            logger.debug("No se pudo liberar la escucha previa: %s", exc)
