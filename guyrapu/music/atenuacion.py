# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Cómo baja y sube la música cuando suena otra cosa.

El registro de fuentes decide qué pedidos bajan la música y de dónde salen
las casillas y las claves de Preferencias. `Atenuador` solo mide el factor
con un reloj inyectado; el hilo del módulo avisa a quien lo reaplica en VLC.
"""

from __future__ import annotations

import threading
import time
import weakref
from dataclasses import dataclass

from guyrapu.core import diagnostico
from guyrapu.core.idioma import N_

PASO_S = 0.05
BAJADA_S = 0.3
ESPERA_S = 0.8
SUBIDA_S = 1.5
VOLUMEN_FABRICA = 30


@dataclass(frozen=True)
class Fuente:
    id: str
    rotulo: str
    fabrica: bool


FUENTES = (
    Fuente("voz", N_("Bajar música mientras &habla la voz"), False),
    Fuente("medio", N_("Bajar música mientras &suena un medio"), True),
)


class Atenuador:
    """Factor de volumen según los pedidos todavía vivos de cada fuente."""

    def __init__(self, reloj=time.monotonic):
        self._reloj = reloj
        self._pedidos = {}
        self._activas = set()
        self._porcentaje = 100
        self._inicio = None
        self._desde = 1.0
        self._hasta = 1.0
        self._fin = None
        self._en_fin = 1.0

    def configurar(self, activas, porcentaje):
        """Cambia las fuentes que atienden y el volumen al bajar, en caliente."""
        ahora = self._reloj()
        anterior = self.factor(ahora)
        tenia_pedidos = bool(self._pedidos)
        self._activas = set(activas)
        self._porcentaje = max(0, min(100, int(porcentaje)))
        for fuente in tuple(self._pedidos):
            if fuente not in self._activas:
                del self._pedidos[fuente]
        if self._pedidos:
            self._desde = anterior
            self._inicio = ahora
            self._hasta = self._porcentaje / 100.0
        elif tenia_pedidos and self._fin is None:
            self._fin, self._en_fin = ahora, anterior

    def pedir(self, fuente, segundos):
        """Pide bajar la música durante `segundos`; volver a pedirlo lo renueva."""
        ahora = self._reloj()
        if fuente not in self._activas:
            return
        if not self._pedidos:
            self._desde = self.factor(ahora)
            self._inicio = ahora
            self._hasta = self._porcentaje / 100.0
            self._fin = None
        self._pedidos[fuente] = ahora + max(0.0, float(segundos))

    def soltar(self, fuente):
        """Da por terminado el pedido de una fuente."""
        ahora = self._reloj()
        if fuente not in self._pedidos:
            return
        valor = self._bajada(ahora)
        del self._pedidos[fuente]
        if not self._pedidos:
            self._fin, self._en_fin = ahora, valor

    def factor(self, ahora):
        """El multiplicador del volumen en el instante `ahora`."""
        self._vencer(ahora)
        if self._pedidos:
            return self._bajada(ahora)
        if self._fin is None:
            return self._en_fin
        transcurrido = ahora - self._fin - ESPERA_S
        if transcurrido <= 0:
            return self._en_fin
        avance = min(1.0, transcurrido / SUBIDA_S)
        return self._en_fin + (1.0 - self._en_fin) * avance

    def _vencer(self, ahora):
        vencidas = [fuente for fuente, limite in self._pedidos.items()
                    if limite <= ahora]
        if not vencidas:
            return
        for fuente in vencidas:
            del self._pedidos[fuente]
        if not self._pedidos:
            self._fin, self._en_fin = ahora, self._bajada(ahora)

    def _bajada(self, ahora):
        if self._inicio is None:
            return self._hasta
        avance = min(1.0, max(0.0, (ahora - self._inicio) / BAJADA_S))
        return self._desde + (self._hasta - self._desde) * avance


logger = diagnostico.obtener_logger(__name__)
_bloqueo = threading.Lock()
_avisados = []
_atenuador = Atenuador()
_ultimo = 1.0
_hilo = None


def configurar(activas, porcentaje):
    """Aplica al atenuador compartido las preferencias guardadas."""
    _atenuador.configurar(activas, porcentaje)


def pedir(fuente, segundos):
    """Pide al atenuador compartido que baje la música."""
    _atenuador.pedir(fuente, segundos)


def soltar(fuente):
    """Da por terminado un pedido del atenuador compartido."""
    _atenuador.soltar(fuente)


def atenuado(valor):
    """El volumen que debe recibir VLC, ya multiplicado por el factor de ahora."""
    return int(round(float(valor) * _atenuador.factor(time.monotonic())))


def aplicar(config):
    """Configura la atenuación con las preferencias ya guardadas en memoria."""
    activas = tuple(fuente.id for fuente in FUENTES
                    if config.get(f"musica_atenuar_{fuente.id}", fuente.fabrica))
    configurar(activas, config.get("musica_volumen_atenuado", VOLUMEN_FABRICA))


def al_cambiar(funcion):
    """Avisa a `funcion` cada vez que el factor se mueve."""
    global _hilo
    try:
        referencia = weakref.WeakMethod(funcion)
    except TypeError:
        referencia = weakref.ref(funcion)
    with _bloqueo:
        _avisados.append(referencia)
        if _hilo is None:
            _hilo = diagnostico.crear_hilo(_atender, "musica-atenuacion")
            _hilo.start()


def _atender():
    """Despierta cada 50 ms y avisa solo cuando el factor cambió."""
    global _ultimo
    while True:
        time.sleep(PASO_S)
        factor = _atenuador.factor(time.monotonic())
        if factor == _ultimo:
            continue
        _ultimo = factor
        with _bloqueo:
            vivos = []
            avisados = []
            for referencia in _avisados:
                funcion = referencia()
                if funcion is not None:
                    vivos.append(referencia)
                    avisados.append(funcion)
            _avisados[:] = vivos
        for funcion in avisados:
            try:
                funcion()
            except Exception as exc:
                logger.debug("No se pudo reaplicar la atenuación: %s", exc)
