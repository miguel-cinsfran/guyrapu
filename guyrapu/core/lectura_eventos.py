# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Texto que la voz lee de un mensaje o evento del chat.

Limpieza del texto, qué dice la voz ante un evento y armado del texto de un
mensaje entrante. Puro y sin wx. Única razón para cambiar: qué texto se lee.
"""

from __future__ import annotations

import re

from guyrapu.core.idioma import _
from guyrapu.core.tipos_mensaje import (
    TIPO_SUPERCHAT, TIPO_MIEMBRO, TIPO_ENTRADA, TIPO_SEGUIR, TIPO_COMPARTIR,
    TIPO_COFRE, TIPO_ME_GUSTA, TIPO_ENCUESTA, TIPO_ENCUESTA_FIN, TIPO_META,
    TIPO_BATALLA, TIPO_BATALLA_FIN, VARIANTE_REGALO, VARIANTE_SUPERFANS,
)


def texto_evento(tipo, autor, monto, mensaje="") -> str | None:
    """Texto de la voz para un evento del directo, o None si no lo es."""
    if tipo in (TIPO_ENCUESTA, TIPO_ENCUESTA_FIN, TIPO_META,
                TIPO_BATALLA, TIPO_BATALLA_FIN):
        return mensaje
    if tipo == TIPO_MIEMBRO:
        if monto == VARIANTE_REGALO:
            return _("Suscripción de regalo: {autor}").format(autor=autor)
        return _("Nuevo miembro: {autor}").format(autor=autor)
    if tipo == TIPO_ENTRADA:
        try:
            varios = int(monto) > 1
        except (TypeError, ValueError):
            varios = False
        # Traductores: {autor} es quien entró; en un grupo, varios nombres.
        return (_("{autor} entraron") if varios
                else _("{autor} entró")).format(autor=autor)
    if tipo == TIPO_SEGUIR:
        return _("{autor} sigue el canal").format(autor=autor)
    if tipo == TIPO_COMPARTIR:
        return _("{autor} compartió el directo").format(autor=autor)
    if tipo == TIPO_COFRE:
        if monto == VARIANTE_SUPERFANS:
            return _("{autor} envió una caja de superfans").format(autor=autor)
        return _("{autor} envió un cofre").format(autor=autor)
    if tipo == TIPO_ME_GUSTA:
        # Traductores: {n} es cuántos «me gusta» dieron.
        return (_("{autor} dio {n} me gusta").format(autor=autor, n=monto)
                if monto else _("{autor} dio me gusta").format(autor=autor))
    return None


# ── Sanitización de texto ────────────────────────────────────────────────────

_EMOJI = re.compile(
    "[\U0001F300-\U0001F9FF\U0001FA00-\U0001FAFF"
    "\U00002702-\U000027B0\U0001F1E0-\U0001F1FF"
    "\u2600-\u2B55\u200d\ufe0f\u3030]+",
    flags=re.UNICODE,
)
_URL   = re.compile(r"https?://[^\s<>\"']+|www\.[^\s<>\"']+", re.IGNORECASE)
_CTRL  = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")
_SPACE = re.compile(r"\s+")
# Emojis personalizados de YouTube que pytchat entrega como texto «:nombre:»
# (p. ej. :blue_heart:). Sin esto el TTS leería «dos puntos blue heart…».
_SHORTCODE = re.compile(r":[a-zA-Z0-9_+\-]{2,}:")


def quitar_emojis(texto: str) -> str:
    """Quita emojis Unicode y los shortcodes :nombre: de YouTube."""
    if not texto:
        return ""
    return _SHORTCODE.sub("", _EMOJI.sub("", texto))


def sanitizar(texto: str, emojis: bool, urls: bool, maxlen: int) -> str:
    if not texto:
        return ""
    if urls:   texto = _URL.sub("", texto)
    if emojis: texto = quitar_emojis(texto)
    texto = _CTRL.sub("", texto)
    texto = _SPACE.sub(" ", texto).strip()
    if maxlen > 0 and len(texto) > maxlen:
        t  = texto[:maxlen]
        sp = t.rfind(" ")
        texto = (t[:sp] if sp > maxlen // 2 else t) + "..."
    return texto


def construir_tts(autor: str, mensaje: str, config: dict) -> str:
    # Traductores: autor cuando el chat no da el nombre; una sola palabra.
    autor_limpio = sanitizar(autor, config["limpiar_emojis"], False, 50) or _("Usuario")
    fmt = config.get("formato_prefijo", "nombre_mensaje")
    if fmt == "solo_mensaje": return mensaje
    if fmt == "solo_nombre":  return autor_limpio
    # Traductores: {m} es el mensaje y {a} su autor; se lee en voz alta.
    if fmt == "mensaje_nombre": return _("{m}, de {a}").format(m=mensaje, a=autor_limpio)
    return _("{autor}: {mensaje}").format(autor=autor_limpio, mensaje=mensaje)


def texto_para_leer(autor_visible: str, ml: str, mensaje: str, tipo: str,
                    monto: str, umbral: int, cola, config: dict,
                    etiqueta_monto) -> str:
    """Arma el texto que la voz lee de un mensaje o evento entrante."""
    if tipo == TIPO_SUPERCHAT and monto:
        # Traductores: {etiqueta} es «Super Chat» o «Regalo».
        return (_("{etiqueta} de {autor}: {monto}. {mensaje}") if ml
                else _("{etiqueta} de {autor}: {monto}")).format(
            etiqueta=_(etiqueta_monto), autor=autor_visible, monto=monto, mensaje=ml)
    texto_del_evento = texto_evento(tipo, autor_visible, monto, mensaje)
    if texto_del_evento is not None:
        return texto_del_evento
    if umbral > 0 and cola.qsize() >= umbral:
        return sanitizar(autor_visible, config["limpiar_emojis"], False, 50) or _("Usuario")
    return construir_tts(autor_visible, ml or mensaje, config)
