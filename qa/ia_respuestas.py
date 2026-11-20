# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Cómo se juzga lo que contesta la IA en el banco."""

import unicodedata


def sin_tildes(texto) -> str:
    """Minúsculas sin tildes, para comparar sin importar el acento."""
    base = unicodedata.normalize("NFD", str(texto or ""))
    return "".join(x for x in base if unicodedata.category(x) != "Mn").lower()


def nombra_colores(texto) -> bool:
    """Si nombra al menos uno de los colores de las ventanas de prueba."""
    base = sin_tildes(texto)
    return any(c in base for c in ("verde", "magenta", "fucsia", "rosa",
                                   "violeta", "morado"))


def lista_cargada(textos) -> bool:
    return bool(textos) and all("cargando" not in sin_tildes(t) for t in textos)


_ERRORES = None


def _textos_error() -> tuple:
    """Frases de `consulta` que anuncian una falla, para comparar."""
    global _ERRORES
    if _ERRORES is None:
        from guyrapu.ai import consulta
        dic = getattr(consulta, "_TEXTOS", getattr(consulta, "_ERRORES", None))
        lista = list(dic.values()) if isinstance(dic, dict) else []
        lista.extend(getattr(consulta, n, "") for n in
                     ("TEXTO_SIN_NIVEL_GRATUITO", "_MSG_PROVEEDOR",
                      "_MSG_MODELO", "_MSG_DIRECCION"))
        lista.extend(("Agrega una captura antes de preguntar.",
                      "Escribe una pregunta.",
                      "No se pudo completar la consulta. Vuelve a intentarlo.",
                      "Falta la clave de"))
        _ERRORES = tuple(str(f) for f in lista if f)
    return _ERRORES


def es_error(texto) -> bool:
    """Si el anuncio es una falla de la consulta, no una respuesta."""
    base = sin_tildes(texto)
    return bool(base.strip()) and any(
        p and p in base for p in map(sin_tildes, _textos_error()))
