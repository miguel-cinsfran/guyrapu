# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Cómo se vuelcan en un ítem de la cola los avisos de una descarga.

Los avisos de estado, progreso y detalle los llama yt-dlp desde el hilo de
descarga: este módulo no importa `wx`.
"""
import time

from guyrapu.core import diagnostico

logger = diagnostico.obtener_logger(__name__)

# La velocidad y el tiempo restante cambian muy seguido: escribirlos en el
# ítem cada 500 ms haría hablar al lector sin parar.
INTERVALO_VELOCIDAD_S = 3.0


class AvisosItem:
    """Vuelca el estado, el progreso y el detalle de una descarga en su ítem."""

    def __init__(self, it, item_id, gestor, progreso_cb, estado_cb) -> None:
        self._item = it
        self._item_id = item_id
        self._gestor = gestor
        self._progreso_cb = progreso_cb
        self._estado_cb = estado_cb
        self._ultimo_detalle_ts = None

    def estado(self, estado: str, mensaje: str = "") -> None:
        self._gestor._avisar_estado(self._item, estado, mensaje, self._estado_cb)

    def progreso(self, pct: float, vel, eta, nombre: str) -> None:
        it = self._item
        it.progreso = max(0.0, min(100.0, float(pct)))
        if nombre and not (it.tipo == "playlist" and it.nombre != it.url):
            it.nombre = nombre
        if isinstance(vel, (int, float)) or isinstance(eta, (int, float)):
            ahora = time.monotonic()
            if (self._ultimo_detalle_ts is None
                    or ahora - self._ultimo_detalle_ts >= INTERVALO_VELOCIDAD_S):
                it.velocidad, it.eta = vel, eta
                self._ultimo_detalle_ts = ahora
        try:
            self._progreso_cb(self._item_id, it.progreso, vel, eta, it.nombre)
        except Exception as exc:
            logger.debug("progreso_cb lanzó: %s", exc)

    def detalle(self, cambios: dict) -> None:
        it = self._item
        avisa = cambios.get("procesando") is True and not it.procesando and it.total <= 1
        if "ruta" in cambios:
            it.rutas.append(cambios["ruta"])
        for clave in ("indice", "total", "procesando"):
            if clave in cambios:
                setattr(it, clave, cambios[clave])
        if avisa:
            self._gestor._avisar_suscriptores("procesando", "", it)
