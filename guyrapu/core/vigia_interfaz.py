# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Vigilancia de un hilo de interfaz que deja de responder."""

from __future__ import annotations

import sys
import threading
import time
import traceback

from guyrapu.core import diagnostico


UMBRAL_BLOQUEO_INTERFAZ_MS = 500
logger = diagnostico.obtener_logger(__name__)


def decidir_bloqueo_interfaz(
    marca_latido: float, ahora: float, ya_registrado: bool
) -> tuple[bool, bool]:
    """Decide si corresponde registrar el estado actual del latido."""
    demora_ms = (ahora - marca_latido) * 1000
    if demora_ms < UMBRAL_BLOQUEO_INTERFAZ_MS:
        return False, False
    return not ya_registrado, True


def componer_bloqueo_interfaz(demora_ms: float, pila: str) -> str:
    return f"INTERFAZ bloqueada_ms={demora_ms:.0f}\n{pila.rstrip()}"


def esta_vivo_el_latido(marca_inicial: float, marca_actual: float,
                        ya_vivo: bool) -> bool:
    """Indica si el latido ya cambió al menos una vez."""
    return ya_vivo or marca_actual != marca_inicial


def pila_hilo_interfaz(marcos: dict[int, object], identificador: int | None) -> str:
    marco = marcos.get(identificador)
    return "".join(traceback.format_stack(marco)).rstrip() if marco else "no disponible"


def vigilar_hilo_interfaz(obtener_marca, parada: threading.Event) -> None:
    """Registra una pila del hilo principal mientras su latido está atrasado."""
    ya_registrado = False
    marca_inicial = None
    latido_vivo = False
    while not parada.wait(0.1):
        ahora = time.monotonic()
        marca_latido = obtener_marca()
        if marca_inicial is None:
            marca_inicial = marca_latido
        latido_vivo = esta_vivo_el_latido(
            marca_inicial, marca_latido, latido_vivo)
        if not latido_vivo:
            continue
        registrar, ya_registrado = decidir_bloqueo_interfaz(
            marca_latido, ahora, ya_registrado)
        if registrar:
            demora_ms = (ahora - marca_latido) * 1000
            pila = pila_hilo_interfaz(
                sys._current_frames(), threading.main_thread().ident)
            logger.warning("%s", componer_bloqueo_interfaz(demora_ms, pila))
