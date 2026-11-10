# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Vigilancia de un hilo de interfaz que deja de responder."""

from __future__ import annotations

import faulthandler
import sys
import threading
import time
import traceback

from guyrapu.core import cadena_espera, diagnostico


UMBRAL_BLOQUEO_INTERFAZ_MS = 500
SEGUNDOS_SIN_LATIDO = 30
INTERVALO_REARME_VIGIA_S = 1.0
logger = diagnostico.obtener_logger(__name__)


def decidir_bloqueo_interfaz(
    marca_latido: float, ahora: float, ya_registrado: bool
) -> tuple[bool, bool]:
    """Decide si corresponde registrar el estado actual del latido."""
    demora_ms = (ahora - marca_latido) * 1000
    if demora_ms < UMBRAL_BLOQUEO_INTERFAZ_MS:
        return False, False
    return not ya_registrado, True


def componer_bloqueo_interfaz(demora_ms: float, pila: str,
                              cadena: str = "") -> str:
    texto = f"INTERFAZ bloqueada_ms={demora_ms:.0f}\n{pila.rstrip()}"
    if cadena:
        texto += f"\ncadena de espera de Windows:\n{cadena.rstrip()}"
    return texto


def esta_vivo_el_latido(marca_inicial: float, marca_actual: float,
                        ya_vivo: bool) -> bool:
    """Indica si el latido ya cambió al menos una vez."""
    return ya_vivo or marca_actual != marca_inicial


def pila_hilo_interfaz(marcos: dict[int, object], identificador: int | None) -> str:
    marco = marcos.get(identificador)
    return "".join(traceback.format_stack(marco)).rstrip() if marco else "no disponible"


def _latido_al_dia(marca_latido: float, ahora: float) -> bool:
    return (ahora - marca_latido) * 1000 < UMBRAL_BLOQUEO_INTERFAZ_MS


def _armar_vigia(archivo, segundos: int) -> None:
    # El volcado del vigía es de todos los hilos: con la app ya colgada
    # medio minuto, el riesgo de leer otro hilo en marcha es aceptable.
    # No se escribe una línea propia: si el intérprete está trabado, este
    # hilo de Python tampoco corre, y el volcado ya abre con «Timeout».
    faulthandler.dump_traceback_later(
        segundos, repeat=False, file=archivo, exit=False)


def _registrar_bloqueo(demora_ms: float) -> None:
    pila = pila_hilo_interfaz(
        sys._current_frames(), threading.main_thread().ident)
    cadena = cadena_espera.cadena_espera_de_hilo(
        threading.main_thread().native_id)
    logger.warning("%s", componer_bloqueo_interfaz(demora_ms, pila, cadena))


def vigilar_hilo_interfaz(obtener_marca, parada: threading.Event,
                          segundos: int = SEGUNDOS_SIN_LATIDO) -> None:
    """Registra una pila del hilo principal mientras su latido está atrasado."""
    archivo = diagnostico.archivo_fallos()
    ya_registrado = False
    marca_inicial = None
    latido_vivo = False
    ultimo_rearme = None
    try:
        while not parada.wait(0.1):
            ahora = time.monotonic()
            marca_latido = obtener_marca()
            if marca_inicial is None:
                marca_inicial = marca_latido
            al_dia = _latido_al_dia(marca_latido, ahora)
            if archivo is not None and al_dia and (
                    ultimo_rearme is None
                    or ahora - ultimo_rearme >= INTERVALO_REARME_VIGIA_S):
                _armar_vigia(archivo, segundos)
                ultimo_rearme = ahora
            latido_vivo = esta_vivo_el_latido(
                marca_inicial, marca_latido, latido_vivo)
            if not latido_vivo:
                continue
            registrar, ya_registrado = decidir_bloqueo_interfaz(
                marca_latido, ahora, ya_registrado)
            if registrar:
                _registrar_bloqueo((ahora - marca_latido) * 1000)
    finally:
        faulthandler.cancel_dump_traceback_later()
