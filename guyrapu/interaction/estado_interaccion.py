# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Qué dice el estado de la interacción del directo.

Puro y sin wx. Recibe las frases que ya armó F2 y el número de preguntas
pendientes y decide el texto que se anuncia al pedir el estado.
"""

from __future__ import annotations

from guyrapu.core.idioma import _, ngettext


def _limpia(frase: str) -> str:
    """La frase sin el punto final, para unirla con las demás como en F2."""
    return (frase or "").strip().removesuffix(".").strip()


def texto(encuesta: str, batalla: str, meta: str, video: str,
          preguntas: int) -> str:
    """El estado de la interacción, en orden y sin lo que esté vacío."""
    partes = [_limpia(frase) for frase in (encuesta, batalla, meta, video)]
    if preguntas:
        partes.append(_limpia(ngettext("Espera 1 pregunta.",
                                       "Esperan {n} preguntas.",
                                       preguntas).format(n=preguntas)))
    partes = [frase for frase in partes if frase]
    if not partes:
        return _("No hay nada de la interacción en curso.")
    return "; ".join(partes) + "."
