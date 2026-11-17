# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""El texto que la voz dice de un ítem con traducción del chat.

Única razón para cambiar: cómo se arma lo que se lee a partir del ítem y su
traducción. La espera es corta y no hace red: el pedido ya está en marcha.
"""

from __future__ import annotations

from guyrapu.core.lectura_eventos import sanitizar
from guyrapu.translation import idiomas

ESPERA = 2.0


def texto(item, config):
    """El texto que hay que leer: traducido si llegó, original si no."""
    pedido = item.get("pedido")
    texto_tts = item.get("texto_tts") or ""
    if pedido is None:
        return texto_tts
    traduccion = pedido.esperar(ESPERA)
    if traduccion is None or not traduccion.texto or not traduccion.origen:
        return texto_tts
    if idiomas.sigla(traduccion.origen) == idiomas.sigla(pedido.destino):
        return texto_tts
    limpio = sanitizar(traduccion.texto, config.get("limpiar_emojis", True),
                       config.get("eliminar_urls", True),
                       config.get("max_longitud_mensaje", 200))
    if not limpio:
        return texto_tts
    original = item.get("ml") or ""
    if original:
        texto_tts = texto_tts.replace(original, limpio, 1)
    return texto_tts + idiomas.mencion(
        traduccion.origen, config.get("traducir_idioma_original", "completo"),
        voz=True)
