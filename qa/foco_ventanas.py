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
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
NOTIFICACION_CLASE = "windows.ui.core.corewindow"
NOTIFICACION_PROCESO = "shellexperiencehost"


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


def nombre_proceso(pid) -> str:
    """Nombre del ejecutable de un pid, vacío si no se puede leer."""
    kernel = ctypes.windll.kernel32
    manejador = kernel.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False,
                                   pid)
    if not manejador:
        return ""
    try:
        tamano = ctypes.c_ulong(512)
        ruta = ctypes.create_unicode_buffer(512)
        if kernel.QueryFullProcessImageNameW(
                manejador, 0, ruta, ctypes.byref(tamano)):
            return ruta.value.rsplit("\\", 1)[-1]
    finally:
        kernel.CloseHandle(manejador)
    return ""


def describir_primer_plano() -> dict:
    """Hwnd, pid, proceso, título y clase de la ventana con el primer plano."""
    usuario = ctypes.windll.user32
    usuario.GetForegroundWindow.restype = ctypes.c_void_p
    usuario.GetWindowTextW.argtypes = [
        ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_int]
    usuario.GetClassNameW.argtypes = [
        ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_int]
    hwnd = usuario.GetForegroundWindow()
    if not hwnd:
        return {"hwnd": 0, "pid": 0, "proceso": "", "titulo": "",
                "clase": ""}
    pid = ctypes.c_ulong()
    usuario.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    titulo = ctypes.create_unicode_buffer(512)
    clase = ctypes.create_unicode_buffer(256)
    usuario.GetWindowTextW(hwnd, titulo, 512)
    usuario.GetClassNameW(hwnd, clase, 256)
    return {"hwnd": hwnd, "pid": int(pid.value),
            "proceso": nombre_proceso(int(pid.value)),
            "titulo": titulo.value, "clase": clase.value}


def es_notificacion(plano) -> bool:
    """Si el primer plano es una notificación de Windows que se irá sola."""
    return (str(plano.get("proceso") or "").casefold() == NOTIFICACION_PROCESO
            or str(plano.get("clase") or "").casefold() == NOTIFICACION_CLASE)


def esperar_frente(intentar, segundos=25.0, plano=None, dormir=time.sleep) -> bool:
    """Reintenta hasta que `intentar` dé el frente, esperando notificaciones.

    `intentar` dice si la ventana está al frente. Mientras el primer plano sea
    una notificación de Windows se espera a que se vaya sola.
    """
    plano = plano or describir_primer_plano
    limite = time.monotonic() + segundos
    while time.monotonic() < limite:
        if not es_notificacion(plano()):
            if intentar():
                return True
        dormir(0.2)
    return False


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
