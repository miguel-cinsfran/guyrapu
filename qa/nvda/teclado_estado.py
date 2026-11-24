# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Deja el teclado de Windows en el estado que necesita el carril.

Con Bloq Mayús encendido, Windows suelta un globo al escribir en un campo de
contraseña y cambia lo que NVDA transcribe. El carril lo apaga mientras recorre
las ventanas y lo deja como estaba al terminar, incluso si la corrida falla.
"""

from __future__ import annotations

import ctypes
from contextlib import contextmanager

VK_CAPITAL = 0x14
TECLA_ARRIBA = 0x0002


def estado():
    """Devuelve 1 si Bloq Mayús está encendido y 0 si no."""
    return ctypes.windll.user32.GetKeyState(VK_CAPITAL) & 1


def alternar():
    """Pulsa y suelta Bloq Mayús para invertir su estado."""
    usuario = ctypes.windll.user32
    usuario.keybd_event(VK_CAPITAL, 0, 0, 0)
    usuario.keybd_event(VK_CAPITAL, 0, TECLA_ARRIBA, 0)


@contextmanager
def con_bloq_mayus_apagado(leer=estado, cambiar=alternar):
    """Apaga Bloq Mayús durante el bloque y restaura el estado al salir."""
    estaba_encendido = leer()
    if estaba_encendido:
        cambiar()
    try:
        yield
    finally:
        if estaba_encendido:
            cambiar()
