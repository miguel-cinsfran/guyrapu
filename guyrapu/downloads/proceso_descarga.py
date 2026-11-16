# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Proceso de yt-dlp de una descarga: lanzarlo, leer su salida y cancelarlo.

Frontera pura/plataforma: este módulo no importa `wx` ni el módulo de yt-dlp.
"""
from __future__ import annotations

import subprocess
import threading
import time
from typing import Callable

from guyrapu.core import diagnostico
from guyrapu.core.idioma import _
from guyrapu.downloads.analisis_enlace import _sin_ventana
from guyrapu.downloads.proceso_ytdlp import (
    _matar_arbol, _vigilar_cancelacion)
from guyrapu.downloads.progreso_ytdlp import resultado_final, tratar_linea
from guyrapu.downloads.restos_descarga import limpiar_restos_descarga

logger = diagnostico.obtener_logger(__name__)


def lanzar_proceso(ruta: str, argumentos: list[str]) -> subprocess.Popen:
    """Lanza yt-dlp y lo vincula a la app, sin que el vínculo corte la descarga."""
    proceso = subprocess.Popen(
        [ruta, *argumentos],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        encoding="utf-8", errors="replace",
        creationflags=_sin_ventana(),
    )
    try:
        from guyrapu.core.subprocesos import vincular_a_la_app
        vincular_a_la_app(proceso)
    except Exception as error:
        logger.debug("no se pudo vincular la descarga a la app: %s", error)
    return proceso


def cancelar(proceso, carpeta: str, estado: dict,
             estado_cb: Callable) -> None:
    """Mata el proceso, borra los restos y avisa que la descarga se canceló."""
    _matar_arbol(proceso)
    proceso.wait()
    borrados = limpiar_restos_descarga(carpeta, estado["ultimo_archivo"])
    if borrados:
        logger.info("descarga cancelada: borrados %d restos", len(borrados))
    estado_cb("cancelado", _("Descarga cancelada"))


def leer_salida(proceso, cancel_event: threading.Event, carpeta: str,
                estado: dict, progreso_cb: Callable, estado_cb: Callable,
                al_detalle: Callable) -> None:
    """Lee la salida de yt-dlp hasta el resultado, cancelando si se pide."""
    estado["ultimo_avance"] = time.monotonic()
    if cancel_event.is_set():
        cancelar(proceso, carpeta, estado, estado_cb)
        return
    diagnostico.crear_hilo(
        _vigilar_cancelacion, "Vigilante-cancelacion",
        args=(proceso, cancel_event, 0.2, estado),
    ).start()
    for linea in iter(proceso.stdout.readline, ""):
        if cancel_event.is_set():
            cancelar(proceso, carpeta, estado, estado_cb)
            return
        tratar_linea(linea, estado, progreso_cb, al_detalle)
    proceso.wait()
    cancelado = cancel_event.is_set()
    if cancelado:
        limpiar_restos_descarga(carpeta, estado["ultimo_archivo"])
        codigo = None
    else:
        codigo = proceso.returncode
        if codigo != 0 and estado["ultimo_error"]:
            logger.warning("yt-dlp terminó con código %s: %s",
                           codigo, estado["ultimo_error"])
    estado_cb(*resultado_final(codigo, cancelado, estado))
