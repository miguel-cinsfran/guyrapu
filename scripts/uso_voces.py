# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Qué uso permite la ficha de una voz de Piper.

Lee la licencia y la base declaradas en el MODEL_CARD de la revisión fija.
No lee red ni disco: solo recibe el texto de la ficha y el nombre de la voz.
"""

from __future__ import annotations

import re

LIBRE = "libre"
NO_COMERCIAL = "no_comercial"
INVESTIGACION = "investigacion"
SIN_CONFIRMAR = "sin_confirmar"

_JENNY = ("Licencia propia de Dioco: uso comercial permitido, "
          "citando la voz como Jenny (Dioco)")
_SIN_LICENCIA = "Sin indicar"
_LICENCIA = re.compile(r"^\s*\*\s*License:\s*(.+)$", re.MULTILINE | re.IGNORECASE)
_NO_COMERCIAL = re.compile(r"\b(nc|non[- ]?commercial)\b", re.IGNORECASE)
_ENTRENAMIENTO = re.compile(r"^##\s+Training\s*$(.*?)(?=^##\s|\Z)",
                            re.MULTILINE | re.DOTALL | re.IGNORECASE)
_SIN_BASE = re.compile(r"see\s+(?:url|license)", re.IGNORECASE)


def _nombre(nombre):
    return (nombre or "").strip().lower()


def licencia(nombre, texto) -> str:
    """El texto de licencia de la ficha, o «Sin indicar» si no lo trae."""
    if _nombre(nombre) == "jenny_dioco":
        return _JENNY
    encontrado = _LICENCIA.search(texto or "")
    return encontrado.group(1).strip() if encontrado else _SIN_LICENCIA


def uso(nombre, texto) -> str:
    """La categoría de uso permitido por la ficha de la voz."""
    nombre = _nombre(nombre)
    if nombre == "jenny_dioco":
        return LIBRE
    seccion = _ENTRENAMIENTO.search(texto or "")
    base = seccion.group(1).lower() if seccion else ""
    if nombre == "lessac" or "lessac" in base:
        return INVESTIGACION
    encontrado = _LICENCIA.search(texto or "")
    declarada = encontrado.group(1).strip() if encontrado else ""
    bajo = re.sub(r"[-_]+", " ", declarada.lower())
    if _NO_COMERCIAL.search(bajo) or "ryan" in base:
        return NO_COMERCIAL
    if not declarada or _SIN_BASE.search(bajo) or _SIN_BASE.search(base) \
            or not base.strip():
        return SIN_CONFIRMAR
    return LIBRE
