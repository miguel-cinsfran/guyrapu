# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""La cola que junta lo que llega en el mismo medio segundo.

Puro: no espera ni duerme, el instante llega como argumento. Su única
razón para cambiar es cuándo se pide un lote y cuándo se rinde y entrega
el original.

Los lotes se piden en orden y `recibir` se llama en ese mismo orden: es la
respuesta del lote más viejo todavía en vuelo.
"""

from __future__ import annotations

from dataclasses import dataclass

from guyrapu.translation.memoria import Memoria
from guyrapu.translation.proveedores.base import Traduccion


@dataclass
class _Entrada:
    original: str
    llegada: float
    traduccion: Traduccion | None = None
    pedida: bool = False


class Cola:
    """Agrupa lo que llega junto y lo entrega traducido o en su original."""

    VENTANA = 0.5
    ESPERA = 2.0

    def __init__(self, destino, memoria=None):
        self._destino = destino
        self._memoria = memoria if memoria is not None else Memoria()
        self._pendientes = []
        self._en_vuelo = []

    def agregar(self, texto, ahora):
        """Suma un texto, ya traducido si la memoria lo tiene."""
        cacheada = self._memoria.obtener(texto, self._destino)
        self._pendientes.append(_Entrada(texto, ahora, cacheada))

    def lote_listo(self, ahora):
        """Los textos que toca pedir ahora, o nada si la ventana no cerró."""
        sin_pedir = [entrada for entrada in self._pendientes
                     if not entrada.pedida and entrada.traduccion is None]
        if not sin_pedir or ahora - sin_pedir[0].llegada < self.VENTANA:
            return []
        for entrada in sin_pedir:
            entrada.pedida = True
        self._en_vuelo.append(sin_pedir)
        return [entrada.original for entrada in sin_pedir]

    def recibir(self, traducciones):
        """Guarda lo que volvió para el lote más viejo en vuelo."""
        if not self._en_vuelo:
            return
        lote = self._en_vuelo.pop(0)
        for entrada, traduccion in zip(lote, traducciones):
            entrada.traduccion = traduccion
            self._memoria.guardar(entrada.original, self._destino, traduccion)

    def fallo(self):
        """Descarta el lote más viejo en vuelo sin traducirlo."""
        if self._en_vuelo:
            self._en_vuelo.pop(0)

    def entregables(self, ahora):
        """Lo que ya se puede leer, en orden de llegada."""
        listos = []
        while self._pendientes:
            entrada = self._pendientes[0]
            if entrada.traduccion is not None:
                listos.append(entrada.traduccion)
            elif ahora - entrada.llegada >= self.ESPERA:
                listos.append(Traduccion(entrada.original, None))
            else:
                break
            self._pendientes.pop(0)
        return listos
