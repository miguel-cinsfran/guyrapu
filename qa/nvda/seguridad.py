# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""La seguridad del carril: presencia física, corte y respaldo.

El carril deja a una persona ciega sin voz si queda a medias. Por eso antes
de tocar nada se niega si hubo teclado o ratón en los últimos 30 segundos,
durante la corrida corta ante el primer evento que no venga inyectado, y
deja una tarea programada que devuelve el NVDA de la PC si el guion muere.

Lo que decide (`es_fisico`, la guardia, el estado a anotar, la hora del
respaldo) es puro y está probado. Lo que toca Windows va detrás de funciones
chicas.
"""

from __future__ import annotations

import ctypes
import json
import subprocess
import threading
from ctypes import wintypes
from datetime import datetime, timedelta
from pathlib import Path

SEGUNDOS_GUARDIA = 30.0
LLKHF_INJECTED = 0x10
LLMHF_INJECTED = 0x01
WH_KEYBOARD_LL = 13
WH_MOUSE_LL = 14
WM_QUIT = 0x0012
NOMBRE_RESPALDO = "GuyrapuCarrilNVDA"
RESPALDO_MINUTOS = 45

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

LRESULT = ctypes.c_ssize_t
HOOKPROC = ctypes.WINFUNCTYPE(LRESULT, ctypes.c_int, wintypes.WPARAM,
                              wintypes.LPARAM)

user32.SetWindowsHookExW.argtypes = [ctypes.c_int, HOOKPROC,
                                     wintypes.HINSTANCE, wintypes.DWORD]
user32.SetWindowsHookExW.restype = ctypes.c_void_p
user32.CallNextHookEx.argtypes = [ctypes.c_void_p, ctypes.c_int,
                                  wintypes.WPARAM, wintypes.LPARAM]
user32.CallNextHookEx.restype = LRESULT
user32.UnhookWindowsHookEx.argtypes = [ctypes.c_void_p]
user32.GetMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND,
                               wintypes.UINT, wintypes.UINT]
user32.GetMessageW.restype = ctypes.c_int
user32.PostThreadMessageW.argtypes = [wintypes.DWORD, wintypes.UINT,
                                      wintypes.WPARAM, wintypes.LPARAM]
user32.GetLastInputInfo.argtypes = [ctypes.c_void_p]
user32.GetLastInputInfo.restype = wintypes.BOOL
kernel32.GetCurrentThreadId.restype = wintypes.DWORD
kernel32.GetTickCount.restype = wintypes.DWORD
kernel32.GetDateFormatW.argtypes = [wintypes.DWORD, wintypes.DWORD,
                                    ctypes.c_void_p, wintypes.LPWSTR,
                                    ctypes.c_int]
kernel32.GetDateFormatW.restype = ctypes.c_int


class ModoRequerido(RuntimeError):
    """`--sin-espera` solo vale con el modo explícito de una sola PC."""


class _EntradaInfo(ctypes.Structure):
    _fields_ = [("tamano", wintypes.UINT), ("ticks", wintypes.DWORD)]


class _FechaSistema(ctypes.Structure):
    _fields_ = [("anio", wintypes.WORD), ("mes", wintypes.WORD),
                ("dia_semana", wintypes.WORD), ("dia", wintypes.WORD),
                ("hora", wintypes.WORD), ("minuto", wintypes.WORD),
                ("segundo", wintypes.WORD), ("milesima", wintypes.WORD)]


class _TeclaLL(ctypes.Structure):
    _fields_ = [("codigo", wintypes.DWORD), ("escaneo", wintypes.DWORD),
                ("banderas", wintypes.DWORD), ("hora", wintypes.DWORD),
                ("extra", ctypes.c_size_t)]


class _RatonLL(ctypes.Structure):
    _fields_ = [("punto", wintypes.POINT), ("datos", wintypes.DWORD),
                ("banderas", wintypes.DWORD), ("hora", wintypes.DWORD),
                ("extra", ctypes.c_size_t)]


def es_fisico(tipo, banderas) -> bool:
    """Si un evento del gancho no lleva la marca de inyectado."""
    if tipo == "teclado":
        marca = LLKHF_INJECTED
    elif tipo == "raton":
        marca = LLMHF_INJECTED
    else:
        raise ValueError(f"tipo de gancho desconocido: {tipo}")
    return not (int(banderas) & marca)


def decidir_guardia(segundos, sin_espera=False, una_pc=False, marca=None,
                    ahora=None):
    """(permitido, motivo) según la última entrada física y el modo.

    Con una marca de fin limpio válida alcanza con que la última entrada de
    Windows sea anterior o igual a ella: lo que inyectó el carril quedó
    antes. Sin marca, ilegible o en el futuro, vale la espera de siempre.
    """
    if sin_espera:
        if not una_pc:
            raise ModoRequerido(
                "--sin-espera exige --una-pc: se saltea la guardia solo en "
                "la PC donde se trabaja")
        return True, "sin espera, modo de una sola PC"
    ahora = ahora or datetime.now()
    if _hay_fin_limpio(segundos, marca, ahora):
        return True, f"sin entrada física desde el fin limpio ({segundos:.0f} s)"
    if segundos < SEGUNDOS_GUARDIA:
        return False, (f"hubo teclado o ratón hace {segundos:.0f} s; "
                       f"se esperan {SEGUNDOS_GUARDIA:.0f} segundos")
    return True, f"sin entrada física hace {segundos:.0f} s"


def _hay_fin_limpio(segundos, marca, ahora) -> bool:
    limpio = _marca_valida(marca, ahora)
    if limpio is None:
        return False
    return ahora - timedelta(seconds=segundos) <= limpio


def _marca_valida(marca, ahora):
    if isinstance(marca, datetime):
        valor = marca
    elif isinstance(marca, str):
        try:
            valor = datetime.fromisoformat(marca.strip())
        except ValueError:
            return None
    else:
        return None
    return None if valor > ahora else valor


def anotar_fin_limpio(ruta, momento=None) -> None:
    """Deja la hora en que se detuvo el vigilante, antes de la devolución."""
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text((momento or datetime.now()).isoformat(),
                    encoding="utf-8")


def leer_fin_limpio(ruta):
    """El texto de la marca, o None si no está."""
    try:
        texto = Path(ruta).read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return texto or None


def segundos_desde_ultima_entrada() -> float:
    """Segundos desde el último teclado o ratón, o cero si no se sabe."""
    info = _EntradaInfo()
    info.tamano = ctypes.sizeof(_EntradaInfo)
    if not user32.GetLastInputInfo(ctypes.byref(info)):
        return 0.0
    ahora = kernel32.GetTickCount()
    return ((ahora - info.ticks) & 0xFFFFFFFF) / 1000.0


def estado_inicial(actual):
    """Lo que se anota antes de cerrar el NVDA de la PC."""
    if not actual:
        return {"habia": False, "ejecutable": None}
    return {"habia": True,
            "ejecutable": actual.get("ejecutable") or "",
            "pid": actual.get("pid")}


def escribir_estado(ruta, estado) -> None:
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(estado, ensure_ascii=False), encoding="utf-8")


def momento_respaldo(minutos, ahora=None) -> datetime:
    return (ahora or datetime.now()) + timedelta(minutes=minutos)


def fecha_local(momento) -> str:
    """La fecha corta en el formato que espera `schtasks` en esta PC."""
    sistema = _FechaSistema(
        momento.year, momento.month, momento.isoweekday() % 7, momento.day,
        momento.hour, momento.minute, momento.second, 0)
    bufer = ctypes.create_unicode_buffer(64)
    if not kernel32.GetDateFormatW(0, 0x0001, ctypes.byref(sistema),
                                   bufer, len(bufer)):
        return momento.strftime("%d/%m/%Y")
    return bufer.value


def linea_comando(python, guion) -> str:
    return f'"{python}" "{guion}"'


def crear_respaldo(nombre, momento, linea):
    """Programa la tarea de una sola vez en la sesión del usuario."""
    try:
        proceso = subprocess.run(
            ["schtasks", "/Create", "/TN", nombre, "/TR", linea,
             "/SC", "ONCE", "/SD", fecha_local(momento),
             "/ST", momento.strftime("%H:%M"), "/IT", "/F"],
            capture_output=True, text=True, timeout=60, check=False)
    except subprocess.TimeoutExpired:
        return False, "schtasks no terminó: puede estar pidiendo contraseña"
    return proceso.returncode == 0, (proceso.stdout + proceso.stderr).strip()


def borrar_respaldo(nombre) -> bool:
    try:
        proceso = subprocess.run(
            ["schtasks", "/Delete", "/TN", nombre, "/F"],
            capture_output=True, text=True, timeout=60, check=False)
    except subprocess.TimeoutExpired:
        return False
    return proceso.returncode == 0


class Vigilante:
    """Ganchos de bajo nivel que levantan la bandera ante entrada física."""

    def __init__(self):
        self._cortado = threading.Event()
        self._instalado = threading.Event()
        self._id = 0
        self._error = ""
        self._hilo = None
        self._procs = []
        self._ganchos = []

    @property
    def cortado(self) -> bool:
        return self._cortado.is_set()

    def iniciar(self) -> None:
        self._hilo = threading.Thread(target=self._bucle,
                                      name="carril-ganchos", daemon=True)
        self._hilo.start()
        if not self._instalado.wait(5.0) or self._error:
            raise RuntimeError(self._error or "no se instalaron los ganchos")

    def detener(self) -> None:
        if not self._hilo or not self._hilo.is_alive():
            return
        if self._id:
            user32.PostThreadMessageW(self._id, WM_QUIT, 0, 0)
        self._hilo.join(5.0)

    def _bucle(self) -> None:
        self._id = kernel32.GetCurrentThreadId()
        teclado = HOOKPROC(self._teclado)
        raton = HOOKPROC(self._raton)
        self._procs = [teclado, raton]
        self._ganchos = [
            user32.SetWindowsHookExW(WH_KEYBOARD_LL, teclado, None, 0),
            user32.SetWindowsHookExW(WH_MOUSE_LL, raton, None, 0),
        ]
        if not all(self._ganchos):
            self._error = "no se pudieron instalar los ganchos de entrada"
            self._instalado.set()
            return
        self._instalado.set()
        mensaje = wintypes.MSG()
        try:
            while user32.GetMessageW(ctypes.byref(mensaje), None, 0, 0) > 0:
                user32.TranslateMessage(ctypes.byref(mensaje))
                user32.DispatchMessageW(ctypes.byref(mensaje))
        finally:
            self._soltar()

    def _soltar(self) -> None:
        for gancho in self._ganchos:
            if gancho:
                user32.UnhookWindowsHookEx(gancho)
        self._ganchos = []

    def _teclado(self, codigo, wparam, lparam):
        return self._mirar("teclado", _TeclaLL, codigo, wparam, lparam)

    def _raton(self, codigo, wparam, lparam):
        return self._mirar("raton", _RatonLL, codigo, wparam, lparam)

    def _mirar(self, tipo, clase, codigo, wparam, lparam):
        if codigo >= 0 and es_fisico(tipo, clase.from_address(lparam).banderas):
            self._cortado.set()
        return user32.CallNextHookEx(None, codigo, wparam, lparam)
