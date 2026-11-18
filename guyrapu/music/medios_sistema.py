# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Qué botón de los controles de medios maneja qué acción y qué se muestra.

Función pura, sin wx ni WinRT: la tabla de botones y el título y el artista
que salen de un tema.
"""

from __future__ import annotations


_BOTONES = {
    "PLAY": "musica_play",
    "PAUSE": "musica_play",
    "NEXT": "musica_siguiente",
    "PREVIOUS": "musica_anterior",
    "STOP": "musica_detener",
}


def accion_de_boton(boton) -> str | None:
    """La acción de música del botón de los controles, o None si no es suyo.

    El nombre llega como el de `SystemMediaTransportControlsButton`, en
    mayúsculas: PLAY, PAUSE, NEXT, PREVIOUS o STOP.
    """
    return _BOTONES.get(boton)


def titulo_y_artista(tema) -> tuple[str, str]:
    """El título y el artista que muestra el panel de medios de un tema."""
    if tema is None:
        return "", ""
    return str(tema.titulo or ""), str(tema.artista or "")
