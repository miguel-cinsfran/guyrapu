# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Qué se le pregunta a la IA por un medio y cómo se limpia lo que contesta.

La respuesta se escribe tal cual en el campo Descripción, así que tiene que
entrar en una línea corta y leerse bien con un lector de pantalla.
"""

from __future__ import annotations

from guyrapu.core.idioma import N_

# Traductores: pregunta que recibe la IA con la imagen o el GIF de un medio.
PREGUNTA = N_("Describe en una frase corta, en el idioma de la aplicación, "
              "qué muestra la imagen a quien no la ve.")

TOPE = 200

_COMILLAS = "\"'«»“”"


def limpiar(respuesta) -> str:
    """Una sola línea, sin comillas alrededor, de doscientos caracteres como mucho."""
    texto = " ".join(str(respuesta).split())
    texto = texto.strip().strip(_COMILLAS).strip()
    if len(texto) <= TOPE:
        return texto
    corte = texto[:TOPE]
    espacio = corte.rfind(" ")
    if espacio > 0:
        corte = corte[:espacio]
    return corte.strip().strip(_COMILLAS).strip()
