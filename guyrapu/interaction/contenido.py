# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Qué hace válido lo que sale de un comando, una alerta o un mensaje.

Puro y sin wx. Única razón para cambiar: las reglas del texto, el medio y
el destino que comparten los tres cuadros de contenido.
"""

from __future__ import annotations

from guyrapu.core.idioma import _

MAXIMO_CHAT = 200


def validar(texto, medio, destino, *, nombre, error_largo):
    """El primer error de lo que va a salir, o "" si se puede guardar."""
    texto = texto or ""
    medio = medio or ""
    if not texto.strip() and not medio.strip():
        # Traductores: regla de contenido compartida. {nombre} es el comando, la alerta o el mensaje automático.
        return _("{nombre} necesita un texto o un medio.").format(nombre=nombre)
    if destino == "chat" and not texto.strip():
        # Traductores: regla de contenido compartida, cuando solo va al chat.
        return _("Para mostrarlo en el chat, escribe un texto.")
    if destino in ("chat", "ambos") and len(texto) > MAXIMO_CHAT:
        return error_largo.format(actual=len(texto), maximo=MAXIMO_CHAT)
    return ""
