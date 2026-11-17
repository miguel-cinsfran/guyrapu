# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Cuánto tiempo se puede reusar la dirección de audio de un vídeo.

Guarda en memoria, hasta que esté por vencer, la dirección que yt-dlp dio
para un vídeo, para no volver a pedirla al reabrir el mismo tema. Sin wx y
sin disco. No lee el reloj: quien busca pasa el momento.
"""

from __future__ import annotations

import threading
import urllib.parse


def vencimiento(url: str):
    """El `expire` de la consulta de la dirección, o None si no lo trae."""
    consulta = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
    expire = consulta.get("expire")
    if not expire:
        return None
    try:
        return int(expire[0])
    except (TypeError, ValueError):
        return None


class CacheEnlaces:
    """Direcciones de audio recientes, en memoria, con un tope de entradas.

    Lo llaman hilos distintos, así que todo pasa por el candado. Al pasar el
    tope se descarta la que se guardó primero.
    """

    def __init__(self, tope=200):
        self._tope = tope
        self._candado = threading.Lock()
        self._entradas: dict[str, tuple[str, float | None]] = {}

    def guardar(self, video_id, url, duracion) -> None:
        """Guarda la dirección si trae vencimiento."""
        if vencimiento(url) is None:
            return
        with self._candado:
            self._entradas[video_id] = (url, duracion)
            while len(self._entradas) > self._tope:
                self._entradas.pop(next(iter(self._entradas)))

    def buscar(self, video_id, ahora):
        """La dirección si falta para su vencimiento más que el tema y el
        margen; si no, la descarta y da None."""
        with self._candado:
            entrada = self._entradas.get(video_id)
            if entrada is None:
                return None
            url, duracion = entrada
            vence = vencimiento(url)
            margen = (duracion if duracion is not None else 600) + 600
            if vence is not None and vence - ahora > margen:
                return url
            del self._entradas[video_id]
            return None

    def olvidar(self, video_id) -> None:
        """Descarta lo guardado de ese vídeo."""
        with self._candado:
            self._entradas.pop(video_id, None)
