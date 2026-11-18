# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Qué eventos de TikTok no se leen.

Lo que decide el filtrado: si el evento es viejo, si TikTok lo marcó como
histórico, cuántos me gusta pasan por ventana y qué ya se leyó en la sesión.
Sin wx ni la librería.
"""

from __future__ import annotations

import unicodedata
from collections import deque

TOPE_MENSAJES = 2000


def nombre_para_leer(nombre, usuario="") -> str:
    """Nombre del autor limpio para leer: NFKC y, si no queda letra ni cifra,
    el usuario de TikTok; si tampoco, «Usuario»."""
    for candidato in (nombre, usuario):
        limpio = unicodedata.normalize("NFKC", str(candidato or "")).strip()
        if any(caracter.isalnum() for caracter in limpio):
            return limpio
    return "Usuario"


class MemoriaSesion:
    """Lo que ya se leyó en esta sesión, para no repetirlo al reconectar."""

    def __init__(self, maximo=TOPE_MENSAJES):
        self._seguidores = set()
        self._mensajes = set()
        self._orden = deque()
        self._maximo = maximo

    def registrar_seguidor(self, ident) -> bool:
        """True la primera vez que esa persona sigue en la sesión."""
        if ident in self._seguidores:
            return False
        self._seguidores.add(ident)
        return True

    def registrar_mensaje(self, ident) -> bool:
        """True la primera vez que se ve ese mensaje en la sesión."""
        if ident in self._mensajes:
            return False
        self._mensajes.add(ident)
        self._orden.append(ident)
        while len(self._orden) > self._maximo:
            self._mensajes.discard(self._orden.popleft())
        return True


def es_previo_a_conexion(creado_ms, conectado_s, margen_s=5.0) -> bool:
    """¿El evento se creó más de `margen_s` antes de conectar? Ante la duda
    (sin hora, hora 0 o todavía sin conectar) es Falso: se lee."""
    try:
        if isinstance(creado_ms, bool):
            return False
        if not isinstance(creado_ms, (int, float)):
            return False
        if creado_ms <= 0:
            return False
        if conectado_s is None or isinstance(conectado_s, bool):
            return False
        return (creado_ms / 1000) < (float(conectado_s) - float(margen_s))
    except Exception:
        return False


def _creado_ms(evento):
    """ms de creación del evento (`common.create_time`); 0 si no se puede leer."""
    try:
        return getattr(getattr(evento, "common", None), "create_time", 0)
    except Exception:
        return 0


def es_historico(evento) -> bool:
    """¿TikTok lo marcó como mensaje viejo (`is_history` del sobre)? El cliente
    de la librería no copia esa marca a los eventos, así que la anota el
    envoltorio de `_envolver_marcador_historico`. Ante la duda, es Falso."""
    try:
        return bool(getattr(evento, "_historico", False))
    except Exception:
        return False


def debe_pasar_me_gusta(ultimo, ahora, intervalo=3.0) -> bool:
    """¿Este me gusta puede pasar? Como mucho UNO cada `intervalo` segundos:
    los me gusta llegan de a montones y saturarían el sonido. `ultimo` es el
    `time.monotonic()` del último que pasó, o None si aún no pasó ninguno.
    Ante la duda, pasa."""
    try:
        if ultimo is None:
            return True
        return (float(ahora) - float(ultimo)) >= float(intervalo)
    except (TypeError, ValueError):
        return True


def descartar_evento(evento, conectado_s, memoria, modulo_eventos,
                     autor_de_evento) -> bool:
    """Si el evento se descarta: viejo, histórico, seguir repetido o comentario
    con un identificador ya visto en esta sesión."""
    if es_historico(evento) or es_previo_a_conexion(
            _creado_ms(evento), conectado_s):
        return True
    clase_seguir = getattr(modulo_eventos, "FollowEvent", None)
    if clase_seguir is not None and isinstance(evento, clase_seguir):
        _nombre, ident = autor_de_evento(evento)
        return bool(ident) and not memoria.registrar_seguidor(ident)
    clase_comentar = getattr(modulo_eventos, "CommentEvent", None)
    if clase_comentar is not None and isinstance(evento, clase_comentar):
        ident = getattr(getattr(evento, "common", None), "msg_id", 0)
        return bool(ident) and not memoria.registrar_mensaje(ident)
    return False
