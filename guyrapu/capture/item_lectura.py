# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Ítem que un mensaje del chat manda a la voz.

Única razón para cambiar: qué datos lleva el ítem que la lectura recibe.
Puro y sin wx.
"""

from __future__ import annotations

from guyrapu.core import avisos_tiktok
from guyrapu.core.config import (
    TIPO_SUPERCHAT, TIPO_STICKER, TIPO_MIEMBRO, TIPO_COFRE,
)
from guyrapu.core.sonidos_eventos import ROL_PROPIETARIO, ROL_MODERADOR


def armar(texto_tts, autor_visible, tipo, rol, modo) -> dict:
    item = {"texto_tts": texto_tts, "autor": autor_visible}
    # Importante: con ElevenLabs y «solo importantes» activado, esto decide
    # qué sale por la nube. Son los eventos con aporte y los roles de peso.
    if (tipo in (TIPO_SUPERCHAT, TIPO_STICKER, TIPO_MIEMBRO, TIPO_COFRE)
            or rol in (ROL_PROPIETARIO, ROL_MODERADOR)):
        item["importante"] = True
    # Los eventos con voz secundaria llevan la marca; el worker conoce la
    # voz, la velocidad y el volumen.
    if avisos_tiktok.con_secundaria(modo):
        item["secundaria"] = True
    return item
