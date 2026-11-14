# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Piezas comunes de los proveedores de voz.

Un proveedor describe un motor y sabe crearlo y listar sus voces. Este módulo
no importa Prism ni wx: lo comparten los motores de Windows y los de la nube.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol, runtime_checkable


class MotorNoDisponible(Exception):
    """El motor pedido no se puede crear en esta máquina."""


@runtime_checkable
class Motor(Protocol):
    """La interfaz que cumple todo motor de voz de la aplicación."""

    def voces(self) -> list[str]: ...

    def elegir_voz(self, idx) -> bool: ...

    def hablar(self, texto) -> bool: ...

    def hablando(self) -> bool: ...

    def parar(self) -> None: ...

    def pausar(self) -> None: ...

    def reanudar(self) -> None: ...

    def fijar_velocidad(self, pct) -> None: ...

    def fijar_volumen(self, pct) -> None: ...

    def fijar_tono(self, pct) -> None: ...

    def cerrar(self) -> None: ...


@dataclass(frozen=True)
class Capacidades:
    """Lo que el motor sabe hacer, para elegir y avisar sin probarlo."""

    streaming: bool
    tono: bool
    nube: bool


@dataclass(frozen=True)
class Proveedor:
    """Un motor registrado, con lo que hace y cómo se crea."""

    id: str
    nombre: str
    licencia: str
    capacidades: Capacidades
    crear: Callable[..., Motor]
    listar_voces: Callable[..., list[str]]
