# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Atajos de lo que sale en el vídeo, activos en cualquier programa.

Ctrl+Alt+Mayús más una letra. Son globales de fábrica: se registran al
arrancar y, si otro programa ya usa uno, se dice una vez con su nombre.
Dentro de la app valen igual por los aceleradores del menú Interacción.
"""

from __future__ import annotations

import wx

from guyrapu.core import diagnostico
from guyrapu.music import anuncios
from guyrapu.ui import atajos_globales, comando_en_directo
from guyrapu.ui.accesibilidad import anunciar
from guyrapu.ui.atajos_globales import combinacion_ctrl_alt_mayus
from guyrapu.voice import sound_player as _snd

logger = diagnostico.obtener_logger(__name__)

# Acciones de interacción en directo con atajo global, en orden: el índice
# da el id.
ORDEN = (
    "video_pausar",
    "video_saltar",
    "video_vaciar",
    "video_silenciar",
    "video_panico",
    "mensajes_automaticos_alternar",
)

# Base de los ids propios para `RegisterHotKey`, lejos de las otras áreas.
BASE_IDS = 0xB400


class InteraccionAtajos:
    """Los atajos de interacción en directo, activos siempre.

    `frame` es la ventana principal: de ella salen los atajos configurados y
    la ventana que registra las combinaciones. Nunca lanza: registrar o
    soltar puede fallar y se informa con el aviso.
    """

    def __init__(self, frame) -> None:
        self._ventana = frame
        self._acciones = {
            "video_pausar":
                lambda: comando_en_directo.alternar_pausa(frame),
            "video_saltar": lambda: comando_en_directo.saltar(frame),
            "video_vaciar": lambda: comando_en_directo.vaciar(frame),
            "video_silenciar":
                lambda: comando_en_directo.alternar_silencio(frame),
            "video_panico":
                lambda: comando_en_directo.alternar_panico(frame),
            "mensajes_automaticos_alternar":
                lambda: comando_en_directo.alternar_mensajes(frame),
        }
        self._globales = atajos_globales.AtajosGlobales(
            frame, self._acciones, orden=ORDEN, base_ids=BASE_IDS,
            traducir=combinacion_ctrl_alt_mayus)
        # Después de que la ventana exista: el registro es del sistema y pide
        # el bucle de eventos.
        try:
            wx.CallAfter(self.activar_arranque)
        except Exception:
            logger.debug("No se pudieron activar los atajos de interacción")

    def _textos(self) -> dict:
        """Los atajos efectivos de interacción, acción → texto guardado."""
        atajos = getattr(self._ventana, "_atajos", None) or {}
        textos = {}
        for accion in ORDEN:
            atajo = atajos.get(accion)
            texto = getattr(atajo, "texto", atajo)
            if texto:
                textos[accion] = texto
        return textos

    def activar_arranque(self) -> None:
        """Registra los globales y dice una vez los que usa otro programa."""
        try:
            fallidos = self._globales.activar(self._textos())
        except Exception:
            logger.exception("No se pudieron activar los atajos de interacción")
            return
        if fallidos:
            self._avisar(anuncios.aviso_atajos_globales_fallo(fallidos))

    def _avisar(self, aviso) -> None:
        if aviso is None:
            return
        if aviso.sonido:
            try:
                _snd.reproducir(aviso.sonido)
            except Exception:
                logger.debug("No se pudo reproducir el sonido %s", aviso.sonido)
        if aviso.texto:
            anunciar(aviso.texto)
