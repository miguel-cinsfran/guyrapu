# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Sintetizador espía del carril: no suena y avisa cada índice y el fin.

NVDA espera que el sintetizador notifique cada `IndexCommand` y que avise
cuando terminó de hablar. Si no lo hace, el administrador de habla no quita
la secuencia de la cola y se queda esperando. En esta fase no simula
duración: notifica en cuanto procesa la secuencia. `cancel` vacía la cola y
no avisa el fin, igual que el espía de NV Access.
"""

from __future__ import annotations

import queue
import threading

import synthDriverHandler
from speech.commands import IndexCommand


def notificar_secuencia(secuencia, cancelado, al_indice, al_fin) -> bool:
    """Recorre una secuencia; devuelve True si la cancelación la cortó."""
    for elemento in secuencia:
        if cancelado():
            return True
        if isinstance(elemento, IndexCommand):
            al_indice(elemento.index)
    if cancelado():
        return True
    al_fin()
    return False


class SynthDriver(synthDriverHandler.SynthDriver):
    name = "espia_guyrapu"
    description = "Espía del carril de QA, no suena"
    # NVDA deriva esta propiedad de `availableVoices`, que el espía no tiene.
    availableLanguages = {"es", "en"}
    supportedSettings = []
    supportedNotifications = {
        synthDriverHandler.synthIndexReached,
        synthDriverHandler.synthDoneSpeaking,
    }

    @classmethod
    def check(cls):
        return True

    def __init__(self):
        super().__init__()
        self._cola = queue.SimpleQueue()
        self._cancelado = False
        self._vivo = True
        self._hilo = threading.Thread(target=self._procesar,
                                      name="espia guyrapu", daemon=True)
        self._hilo.start()

    def terminate(self):
        self._cancelado = True
        self._vivo = False
        self._hilo.join(2.0)

    def speak(self, speechSequence):
        self._cancelado = False
        self._cola.put(speechSequence)

    def cancel(self):
        self._cancelado = True
        while True:
            try:
                self._cola.get_nowait()
            except queue.Empty:
                break

    def _procesar(self):
        while self._vivo:
            try:
                secuencia = self._cola.get(timeout=0.2)
            except queue.Empty:
                continue
            self._procesar_secuencia(secuencia)

    def _procesar_secuencia(self, secuencia) -> bool:
        return notificar_secuencia(
            secuencia, lambda: self._cancelado, self._indice, self._fin)

    def _indice(self, indice):
        synthDriverHandler.synthIndexReached.notify(synth=self, index=indice)

    def _fin(self):
        synthDriverHandler.synthDoneSpeaking.notify(synth=self)
