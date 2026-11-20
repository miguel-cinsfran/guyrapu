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
from ctypes import wintypes

logger = logging.getLogger(__name__)

VK_MENU = 0x12
TECLA_ARRIBA = 0x0002
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
NOTIFICACION_CLASE = "windows.ui.core.corewindow"
NOTIFICACION_PROCESO = "shellexperiencehost"
TH32CS_SNAPPROCESS = 0x00000002


class _PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("cntUsage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
        ("th32ModuleID", wintypes.DWORD),
        ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD),
        ("pcPriClassBase", ctypes.c_long),
        ("dwFlags", wintypes.DWORD),
        ("szExeFile", wintypes.WCHAR * 260),
    ]


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


def arbol_de_procesos() -> dict:
    """Mapa de pid a pid padre, vacío si Windows no lo entrega."""
    kernel = ctypes.windll.kernel32
    instantanea = kernel.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if instantanea in (None, -1):
        return {}
    padres = {}
    try:
        entrada = _PROCESSENTRY32W()
        entrada.dwSize = ctypes.sizeof(entrada)
        if not kernel.Process32FirstW(instantanea, ctypes.byref(entrada)):
            return {}
        while True:
            padres[entrada.th32ProcessID] = entrada.th32ParentProcessID
            if not kernel.Process32NextW(instantanea, ctypes.byref(entrada)):
                break
    finally:
        kernel.CloseHandle(instantanea)
    return padres


def es_proceso_o_descendiente(pid, raiz, arbol=None) -> bool:
    """Si pid es la raíz o cuelga de ella por la cadena de padres.

    El python de un venv es un lanzador y la ventana la tiene su hijo.
    """
    if pid is None or raiz is None:
        return False
    if int(pid) == int(raiz):
        return True
    arbol = arbol_de_procesos() if arbol is None else arbol
    actual = int(pid)
    vistos = set()
    while actual and actual not in vistos:
        if actual == int(raiz):
            return True
        vistos.add(actual)
        actual = arbol.get(actual, 0)
    return False


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


def esperar_frente(intentar, segundos=25.0, plano=None, dormir=time.sleep,
                   pid=None, arbol=None) -> bool:
    """Reintenta hasta que `intentar` dé el frente, esperando notificaciones.

    Si `pid` está al frente, o lo está un descendiente suyo, se da por bueno
    sin tocar nada: forzar el frente abre el menú de sistema de la ventana.
    """
    plano = plano or describir_primer_plano
    limite = time.monotonic() + segundos
    while time.monotonic() < limite:
        actual = plano()
        if es_notificacion(actual):
            dormir(0.2)
            continue
        if pid is not None and es_proceso_o_descendiente(
                actual.get("pid"), pid, arbol):
            return True
        if intentar():
            return True
        dormir(0.2)
    return False


def traer_al_frente(hwnd, pid: int, segundos: float = 10.0,
                    plano=None, pulsar=None) -> bool:
    """Lleva al frente la ventana y espera que Windows confirme.

    Si el frente ya es del pid o de un descendiente no se hace nada: pulsar
    Alt sobre una ventana que ya está al frente abre su menú de sistema.
    """
    try:
        usuario = ctypes.windll.user32
    except Exception:
        return False
    if hwnd is None or pid is None:
        return False
    plano = plano or describir_primer_plano
    pulsar = pulsar or pulsar_alt
    limite = time.monotonic() + segundos
    while time.monotonic() < limite:
        if es_proceso_o_descendiente(plano().get("pid"), pid):
            return True
        pulsar(usuario)
        try:
            usuario.SetForegroundWindow(hwnd)
        except Exception as exc:
            logger.debug("no se pudo poner la ventana al frente: %s", exc)
        time.sleep(0.3)
    return es_proceso_o_descendiente(plano().get("pid"), pid)
