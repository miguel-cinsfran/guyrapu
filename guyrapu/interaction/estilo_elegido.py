# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Cómo se elige un estilo en un cuadro: predeterminado del tipo o uno propio.

Puro y sin wx. Única razón para cambiar: las opciones de esa elección, la
clave que da cada índice y el índice de una clave.
"""

from __future__ import annotations

from guyrapu.core.idioma import _
from guyrapu.obs import estilos_aviso


def opciones(usuario, por_tipo, tipo) -> list[str]:
    """El predeterminado del tipo primero y después todos los estilos."""
    predeterminado = estilos_aviso.buscar_para("", tipo, usuario, por_tipo)
    # Traductores: primera opción de la elección de estilo de un cuadro. {estilo} es el estilo predeterminado del tipo.
    primera = _("Predeterminado ({estilo})").format(
        estilo=_(predeterminado["nombre"]))
    return [primera] + [_(estilo["nombre"])
                        for estilo in estilos_aviso.todos(usuario)]


def clave_de(indice, estilos) -> str:
    """La clave que guarda la opción elegida; la primera guarda el vacío."""
    if indice <= 0:
        return ""
    return estilos[indice - 1]["clave"]


def indice_de(clave, estilos) -> int:
    """La opción que corresponde a esa clave; la primera si no está."""
    for indice, estilo in enumerate(estilos, start=1):
        if estilo["clave"] == clave:
            return indice
    return 0
