# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Cómo se describe una meta en la lista y al escucharla.

Puro y sin wx. Única razón para cambiar: las palabras con que la app cuenta
una meta guardada.
"""

from __future__ import annotations

from guyrapu.core.idioma import _
from guyrapu.interaction.metas import NOMBRES_QUE_CUENTA, Meta


def _que_cuenta(meta: Meta) -> str:
    return _(NOMBRES_QUE_CUENTA.get(meta.que_cuenta, meta.que_cuenta))


def fila(meta: Meta) -> str:
    """La línea de la lista: nombre, qué cuenta, objetivo y si está en pausa."""
    partes = [meta.nombre, _que_cuenta(meta),
              _("objetivo {objetivo}").format(objetivo=meta.objetivo)]
    if not meta.activa:
        partes.append(_("en pausa"))
    return ", ".join(partes)


def escuchar(meta: Meta, nombre_estilo: str) -> str:
    """La frase que cuenta una meta entera al pedir Escuchar."""
    frase = _("{nombre}: {que_cuenta}, objetivo {objetivo}, estilo "
              "{estilo}.").format(
                  nombre=meta.nombre, que_cuenta=_que_cuenta(meta),
                  objetivo=meta.objetivo, estilo=nombre_estilo)
    if (meta.festejo or "").strip():
        frase += " " + _("Festejo: {medio}.").format(medio=meta.festejo)
    if not meta.activa:
        frase += " " + _("En pausa.")
    return frase
