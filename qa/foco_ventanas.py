# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Ayudantes de foco de las ventanas y los controles del banco.

Windows no deja pasar al frente una ventana lanzada desde una tarea
programada solo con `Raise`. El banco usa estos ayudantes: una pulsación
suelta de Alt, `SetForegroundWindow` con reintentos y el primer control que
puede tomar foco dentro de un contenedor.
"""

from __future__ import annotations

import ctypes
import logging
import time

logger = logging.getLogger(__name__)

VK_MENU = 0x12
TECLA_ARRIBA = 0x0002


def primer_foco(ventana):
    """El primer descendiente que puede tomar foco, en el orden de wx."""
    if ventana is None:
        return None
    for hijo in ventana.GetChildren():
        if not hijo.IsShownOnScreen() or not hijo.IsEnabled():
            continue
        if hijo.AcceptsFocus():
            return hijo
        encontrado = primer_foco(hijo)
        if encontrado is not None:
            return encontrado
    return None


def pid_al_frente():
    """Pid de la ventana al frente, None si no se pudo saber."""
    try:
        actual = ctypes.windll.user32.GetForegroundWindow()
        if not actual:
            return None
        pid = ctypes.c_ulong()
        ctypes.windll.user32.GetWindowThreadProcessId(actual,
                                                      ctypes.byref(pid))
        return int(pid.value) or None
    except Exception:
        return None


def pulsar_alt(usuario) -> None:
    """Pulsación suelta de Alt para levantar el bloqueo del primer plano.

    Windows le niega el primer plano a un proceso que no es el del
    frente; esa pulsación lo levanta. Es lo que hace `pywinauto` en
    `set_focus`.
    """
    try:
        usuario.keybd_event(VK_MENU, 0, 0, 0)
        usuario.keybd_event(VK_MENU, 0, TECLA_ARRIBA, 0)
    except Exception as exc:
        logger.debug("no se pudo pulsar Alt: %s", exc)


def traer_al_frente(hwnd, pid: int, segundos: float = 10.0) -> bool:
    """Lleva al frente la ventana y espera que Windows confirme.

    Comprueba con `GetForegroundWindow` que el primer plano es del pid
    dueño de la ventana e intenta `SetForegroundWindow` con su hwnd si
    no, con una pulsación suelta de Alt antes de cada intento para
    levantar el bloqueo del primer plano. Devuelve si quedó al frente.
    """
    try:
        usuario = ctypes.windll.user32
    except Exception:
        return False
    if hwnd is None or pid is None:
        return False
    limite = time.monotonic() + segundos
    while time.monotonic() < limite:
        if pid_al_frente() == pid:
            return True
        pulsar_alt(usuario)
        try:
            usuario.SetForegroundWindow(hwnd)
        except Exception as exc:
            logger.debug("no se pudo poner la ventana al frente: %s", exc)
        time.sleep(0.3)
    try:
        return pid_al_frente() == pid
    except Exception:
        return False
