"""Cifrado y descifrado con DPAPI, atados a la cuenta de Windows.

Su única razón para cambiar es cómo se llama a DPAPI de Windows. No usa wx.
El alcance es el usuario (sin `LOCAL_MACHINE`): un archivo cifrado en una
cuenta no se descifra con otra cuenta de Windows.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes

CRYPTPROTECT_UI_FORBIDDEN = 0x1


class DpapiError(OSError):
    """Falla de CryptProtectData o CryptUnprotectData."""


class DATA_BLOB(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD),
                ("pbData", ctypes.POINTER(ctypes.c_byte))]


def _configurar() -> None:
    """Declara los tipos de crypt32 y kernel32, para no cortar punteros."""
    crypt32 = ctypes.windll.crypt32
    for funcion in (crypt32.CryptProtectData, crypt32.CryptUnprotectData):
        funcion.argtypes = [
            ctypes.POINTER(DATA_BLOB), ctypes.c_void_p,
            ctypes.POINTER(DATA_BLOB), ctypes.c_void_p, ctypes.c_void_p,
            wintypes.DWORD, ctypes.POINTER(DATA_BLOB)]
        funcion.restype = wintypes.BOOL
    ctypes.windll.kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    ctypes.windll.kernel32.LocalFree.restype = ctypes.c_void_p
    ctypes.windll.kernel32.GetLastError.restype = wintypes.DWORD


def _entrada(datos: bytes) -> tuple[DATA_BLOB, ctypes.Array]:
    bufer = ctypes.create_string_buffer(datos, max(len(datos), 1))
    blob = DATA_BLOB(len(datos),
                     ctypes.cast(bufer, ctypes.POINTER(ctypes.c_byte)))
    return blob, bufer


def _llamar(datos: bytes, funcion, nombre: str) -> bytes:
    _configurar()
    entrada, _bufer = _entrada(datos)
    salida = DATA_BLOB()
    if not funcion(ctypes.byref(entrada), None, None, None, None,
                   CRYPTPROTECT_UI_FORBIDDEN, ctypes.byref(salida)):
        codigo = ctypes.windll.kernel32.GetLastError()
        raise DpapiError(codigo, f"{nombre} falló")
    try:
        return ctypes.string_at(salida.pbData, salida.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(salida.pbData)


def cifrar(datos: bytes) -> bytes:
    """Cifra `datos` para esta cuenta de Windows."""
    return _llamar(datos, ctypes.windll.crypt32.CryptProtectData,
                   "CryptProtectData")


def descifrar(datos: bytes) -> bytes:
    """Descifra `datos` cifrados por esta cuenta de Windows."""
    return _llamar(datos, ctypes.windll.crypt32.CryptUnprotectData,
                   "CryptUnprotectData")
