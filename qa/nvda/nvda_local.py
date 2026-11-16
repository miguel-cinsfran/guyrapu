# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Todo lo que toca procesos y ventanas de NVDA.

Encontrar la copia que corre, cerrarla sin matarla, arrancar la portátil con
`-c` y armar esa copia desde la instalada. Las decisiones puras (qué versión
es, si hay que armar la copia) están separadas para poder probarlas.
"""

from __future__ import annotations

import ctypes
import os
import time
from ctypes import wintypes
from pathlib import Path

WM_QUIT = 0x0012
WAIT_TIMEOUT = 0x0102
WAIT_FAILED = 0xFFFFFFFF
SEE_MASK_NOCLOSEPROCESS = 0x00000040
SW_SHOWNORMAL = 1
SW_HIDE = 0
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
SYNCHRONIZE = 0x00100000
CLASE_VENTANA = "wxWindowClassNR"
TITULO_VENTANA = "NVDA"

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
shell32 = ctypes.WinDLL("shell32", use_last_error=True)
version = ctypes.WinDLL("version", use_last_error=True)

user32.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
user32.FindWindowW.restype = wintypes.HWND
user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT,
                                wintypes.WPARAM, wintypes.LPARAM]
user32.PostMessageW.restype = wintypes.BOOL
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND,
                                            ctypes.POINTER(wintypes.DWORD)]
user32.GetWindowThreadProcessId.restype = wintypes.DWORD
kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel32.OpenProcess.restype = wintypes.HANDLE
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
kernel32.WaitForSingleObject.restype = wintypes.DWORD
kernel32.GetExitCodeProcess.argtypes = [wintypes.HANDLE,
                                        ctypes.POINTER(wintypes.DWORD)]
kernel32.GetExitCodeProcess.restype = wintypes.BOOL
kernel32.QueryFullProcessImageNameW.argtypes = [
    wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR,
    ctypes.POINTER(wintypes.DWORD)]
kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
version.GetFileVersionInfoSizeW.argtypes = [wintypes.LPCWSTR,
                                            ctypes.POINTER(wintypes.DWORD)]
version.GetFileVersionInfoSizeW.restype = wintypes.DWORD
version.GetFileVersionInfoW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD,
                                        wintypes.DWORD, ctypes.c_void_p]
version.GetFileVersionInfoW.restype = wintypes.BOOL
version.VerQueryValueW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR,
                                   ctypes.POINTER(ctypes.c_void_p),
                                   ctypes.POINTER(wintypes.UINT)]
version.VerQueryValueW.restype = wintypes.BOOL


class VersionInvalida(RuntimeError):
    """La copia portátil fija y el NVDA instalado no son la misma versión."""


class _VersionFija(ctypes.Structure):
    _fields_ = [
        ("firma", wintypes.DWORD),
        ("estructura", wintypes.DWORD),
        ("archivo_ms", wintypes.DWORD),
        ("archivo_ls", wintypes.DWORD),
        ("producto_ms", wintypes.DWORD),
        ("producto_ls", wintypes.DWORD),
        ("mascara", wintypes.DWORD),
        ("banderas", wintypes.DWORD),
        ("sistema", wintypes.DWORD),
        ("tipo", wintypes.DWORD),
        ("subtipo", wintypes.DWORD),
        ("fecha_ms", wintypes.DWORD),
        ("fecha_ls", wintypes.DWORD),
    ]


class _InfoShell(ctypes.Structure):
    _fields_ = [
        ("tamano", wintypes.DWORD),
        ("mascara", wintypes.DWORD),
        ("ventana", wintypes.HWND),
        ("verbo", wintypes.LPCWSTR),
        ("archivo", wintypes.LPCWSTR),
        ("parametros", wintypes.LPCWSTR),
        ("carpeta", wintypes.LPCWSTR),
        ("mostrar", ctypes.c_int),
        ("instancia", wintypes.HINSTANCE),
        ("lista", ctypes.c_void_p),
        ("clase", wintypes.LPCWSTR),
        ("clave", wintypes.HANDLE),
        ("tecla", wintypes.DWORD),
        ("icono", wintypes.HANDLE),
        ("proceso", wintypes.HANDLE),
    ]


shell32.ShellExecuteExW.argtypes = [ctypes.POINTER(_InfoShell)]
shell32.ShellExecuteExW.restype = wintypes.BOOL


def normalizar_version(texto) -> str:
    """Los tres primeros números de una versión, sin el número de compilación."""
    partes = [p for p in str(texto or "").strip().split(".") if p.isdigit()]
    return ".".join(partes[:3])


def decidir_copia(existe, version_instalada, version_esperada) -> str:
    """«usar» si la copia ya está, «armar» si la instalada es la fijada."""
    esperada = normalizar_version(version_esperada)
    if existe:
        return "usar"
    instalada = normalizar_version(version_instalada)
    if not instalada or instalada != esperada:
        raise VersionInvalida(
            f"la copia portátil del carril es {esperada} y el NVDA instalado "
            f"es {instalada or 'de versión desconocida'}")
    return "armar"


def version_de_ejecutable(ruta) -> str:
    """La versión de producto que Windows declara para un `.exe`."""
    ruta = str(ruta)
    tam = version.GetFileVersionInfoSizeW(ruta, None)
    if not tam:
        return ""
    datos = ctypes.create_string_buffer(tam)
    if not version.GetFileVersionInfoW(ruta, 0, tam, datos):
        return ""
    puntero = ctypes.c_void_p()
    largo = wintypes.UINT()
    if not version.VerQueryValueW(datos, "\\", ctypes.byref(puntero),
                                  ctypes.byref(largo)):
        return ""
    info = ctypes.cast(puntero, ctypes.POINTER(_VersionFija)).contents
    # Los campos de producto del binario de NVDA son genéricos; la versión
    # que interesa es la de archivo, la misma que muestra Windows.
    partes = (info.archivo_ms >> 16, info.archivo_ms & 0xFFFF,
              info.archivo_ls >> 16, info.archivo_ls & 0xFFFF)
    return ".".join(str(p) for p in partes)


def instalado_por_defecto() -> Path:
    programa = os.environ.get("ProgramFiles", r"C:\Program Files")
    return Path(programa) / "NVDA" / "nvda.exe"


def pid_de_ventana(ventana) -> int:
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(ventana, ctypes.byref(pid))
    return int(pid.value)


def ejecutable_de_pid(pid) -> str:
    manejo = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not manejo:
        return ""
    try:
        largo = wintypes.DWORD(32768)
        bufer = ctypes.create_unicode_buffer(largo.value)
        if not kernel32.QueryFullProcessImageNameW(
                manejo, 0, bufer, ctypes.byref(largo)):
            return ""
        return bufer.value
    finally:
        kernel32.CloseHandle(manejo)


def nvda_en_marcha():
    """La ventana, el proceso y el ejecutable del NVDA que corre, o None."""
    ventana = user32.FindWindowW(CLASE_VENTANA, TITULO_VENTANA)
    if not ventana:
        return None
    pid = pid_de_ventana(ventana)
    return {"ventana": ventana, "pid": pid,
            "ejecutable": ejecutable_de_pid(pid)}


def proceso_vivo(pid) -> bool:
    manejo = kernel32.OpenProcess(SYNCHRONIZE, False, pid)
    if not manejo:
        return False
    try:
        return kernel32.WaitForSingleObject(manejo, 0) == WAIT_TIMEOUT
    finally:
        kernel32.CloseHandle(manejo)


def esperar_salida(pid, segundos) -> bool:
    limite = time.monotonic() + segundos
    while time.monotonic() < limite:
        if not proceso_vivo(pid):
            return True
        time.sleep(0.2)
    return not proceso_vivo(pid)


def _citar(argumento) -> str:
    texto = str(argumento)
    if not texto or any(caracter in texto for caracter in ' \t"'):
        return '"' + texto.replace('"', '\\"') + '"'
    return texto


def _parametros(argumentos) -> str:
    return " ".join(_citar(argumento) for argumento in argumentos)


def ejecutar_shell(ejecutable, argumentos=(), esperar=False,
                   tope_s=600.0, mostrar=SW_SHOWNORMAL) -> int:
    """Arranca un ejecutable con ShellExecuteEx, como un doble clic.

    Windows no deja iniciar el `nvda.exe` instalado con CreateProcess porque
    declara uiAccess, y falla con el error 740. ShellExecuteEx lo arranca con
    el token del escritorio, sin elevar y sin pedir `runas`.
    """
    info = _InfoShell()
    info.tamano = ctypes.sizeof(_InfoShell)
    info.mascara = SEE_MASK_NOCLOSEPROCESS
    info.verbo = "open"
    info.archivo = str(ejecutable)
    info.parametros = _parametros(argumentos) or None
    info.mostrar = mostrar
    if not shell32.ShellExecuteExW(ctypes.byref(info)):
        raise ctypes.WinError(ctypes.get_last_error())
    if not info.proceso:
        return 0
    try:
        if not esperar:
            return 0
        resultado = kernel32.WaitForSingleObject(
            info.proceso, int(tope_s * 1000))
        if resultado == WAIT_TIMEOUT:
            raise TimeoutError(
                f"«{ejecutable}» no terminó en {tope_s:.0f} s")
        if resultado == WAIT_FAILED:
            raise ctypes.WinError(ctypes.get_last_error())
        codigo = wintypes.DWORD()
        if not kernel32.GetExitCodeProcess(info.proceso,
                                           ctypes.byref(codigo)):
            raise ctypes.WinError(ctypes.get_last_error())
        return int(codigo.value)
    finally:
        kernel32.CloseHandle(info.proceso)


def cerrar(actual, espera_s=20.0) -> bool:
    """`WM_QUIT` y espera a que guarde y salga; `-q` solo como último recurso."""
    if not actual:
        return True
    pid = actual["pid"]
    if actual.get("ventana"):
        user32.PostMessageW(actual["ventana"], WM_QUIT, 0, 0)
    if esperar_salida(pid, espera_s):
        return True
    ejecutable = actual.get("ejecutable")
    if not ejecutable:
        return False
    try:
        ejecutar_shell(ejecutable, ["-q"], esperar=False)
    except OSError:
        return False
    return esperar_salida(pid, 10.0)


def lanzar(ejecutable, argumentos=()) -> int:
    return ejecutar_shell(ejecutable, argumentos, esperar=False)


def crear_portatil(instalado, destino) -> int:
    """Arma la copia fija desde la instalada, sin arrancarla."""
    Path(destino).mkdir(parents=True, exist_ok=True)
    return ejecutar_shell(
        instalado,
        ["--create-portable-silent", f"--portable-path={destino}"],
        esperar=True, tope_s=600.0)
