# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Capturar como JPEG el fotograma que muestra el reproductor.

La imagen se guarda en una carpeta temporal que vive lo que dura la
captura: no es una ruta de datos de la app.
"""

from __future__ import annotations

import io
import tempfile
from pathlib import Path

import wx


class FotogramaFallido(Exception):
    """libVLC no entregó una imagen que se pueda enviar."""


def reproductor_de(marco):
    """El MediaPlayer del panel de vídeo, o None si no está."""
    panel = getattr(marco, "_rep_panel", None)
    return getattr(panel, "_player", None)


def muestra_video(reproductor) -> bool:
    """Si el reproductor tiene al menos una salida de vídeo."""
    if reproductor is None:
        return False
    try:
        return reproductor.has_vout() > 0
    except Exception:
        return False


def _lado(reproductor, lado):
    """El ancho original si el vídeo es más angosto que el lado pedido."""
    try:
        ancho, _alto = reproductor.video_get_size(0)
        return min(lado, ancho) if ancho > 0 else lado
    except Exception:
        return lado


def capturar(reproductor, lado=1280):
    """El fotograma actual en JPEG con sus medidas, o FotogramaFallido."""
    with tempfile.TemporaryDirectory() as carpeta:
        ruta = Path(carpeta) / "fotograma.png"
        try:
            resultado = reproductor.video_take_snapshot(
                0, str(ruta), _lado(reproductor, lado), 0)
        except Exception as fallo:
            raise FotogramaFallido(str(fallo)) from fallo
        if resultado == -1 or not ruta.is_file():
            raise FotogramaFallido("libVLC no guardó el fotograma")
        imagen = wx.Image(str(ruta), wx.BITMAP_TYPE_ANY)
        if not imagen.IsOk():
            raise FotogramaFallido("el fotograma no se pudo leer")
        salida = io.BytesIO()
        imagen.SaveFile(salida, wx.BITMAP_TYPE_JPEG)
        return salida.getvalue(), imagen.GetWidth(), imagen.GetHeight()
