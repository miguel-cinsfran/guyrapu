# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Búsqueda de un texto en los mensajes de la sesión del chat.

Función pura, sin wx: recibe los mensajes, lo escrito y el predicado de
autor oculto, y devuelve los que coinciden en el autor o en el texto, del
más nuevo al más viejo. No distingue mayúsculas ni tildes.
"""

from __future__ import annotations

import unicodedata


def _normalizar(texto) -> str:
    descompuesto = unicodedata.normalize("NFKD", str(texto or ""))
    sin_tildes = "".join(
        caracter for caracter in descompuesto
        if not unicodedata.combining(caracter))
    return sin_tildes.casefold()


def buscar(mensajes, texto, autor_oculto) -> list:
    """Mensajes que coinciden con `texto`, del más nuevo al más viejo.

    `mensajes` va en orden de llegada. `autor_oculto` recibe el autor y dice
    si sus mensajes se excluyen.
    """
    consulta = _normalizar(texto).strip()
    if not consulta:
        return []
    encontrados = []
    for mensaje in reversed(list(mensajes)):
        if autor_oculto(mensaje.autor):
            continue
        if (consulta in _normalizar(mensaje.autor)
                or consulta in _normalizar(mensaje.texto)):
            encontrados.append(mensaje)
    return encontrados
