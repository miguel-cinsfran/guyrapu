# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Piezas comunes de los proveedores de traducción.

Este módulo no importa wx ni habla por la red: lo comparten el proveedor
de Google y los que se sumen después.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


class ErrorTraduccion(Exception):
    """No se pudo traducir y se lee el mensaje original."""


@dataclass(frozen=True)
class Traduccion:
    """Un texto traducido y el idioma del que salió.

    `origen` queda en None cuando la traducción no llegó y se lee el
    original.
    """

    texto: str
    origen: str | None


@dataclass(frozen=True)
class Proveedor:
    """Un servicio registrado, con lo que pide y cómo traduce."""

    id: str
    nombre: str
    pide_clave: str | bool
    traducir: Callable[..., list[Traduccion]]
