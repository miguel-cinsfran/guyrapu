# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Traduce una tecla física a las teclas virtuales y al carácter de los
teclados instalados en Windows.

La tecla física se identifica por su código de exploración, que no cambia
con la distribución. Nunca carga un teclado: usa solo los que el usuario ya
tiene instalados, porque cargar uno lo agrega a su lista.
"""

from __future__ import annotations

import sys

# MAPVK_VSC_TO_VK: del código de exploración al virtual, según el teclado.
_MAPVK_VSC_TO_VK = 1
# No altera el estado de las teclas muertas: solo interesa qué escribe.
_BANDERA_NO_TOCAR_MUERTAS = 4
# Nombre de la tecla en el teclado de Estados Unidos, para cuando el
# carácter del teclado activo no se puede leer.
_NOMBRES_ESTADOS_UNIDOS = {0x0C: "-", 0x0D: "="}

_user32 = None


def _obtener_user32():
    """Firma las funciones de Windows una sola vez, en su propio objeto.

    Las firmas puestas sobre el objeto compartido las heredaría el resto del
    proceso.
    """
    global _user32
    if _user32 is None:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.WinDLL("user32", use_last_error=True)
        user32.GetKeyboardLayoutList.argtypes = [
            ctypes.c_int, ctypes.POINTER(wintypes.HKL)]
        user32.GetKeyboardLayoutList.restype = ctypes.c_int
        user32.GetKeyboardLayout.argtypes = [wintypes.DWORD]
        user32.GetKeyboardLayout.restype = wintypes.HKL
        user32.MapVirtualKeyExW.argtypes = [
            wintypes.UINT, wintypes.UINT, wintypes.HKL]
        user32.MapVirtualKeyExW.restype = wintypes.UINT
        user32.ToUnicodeEx.argtypes = [
            wintypes.UINT, wintypes.UINT, ctypes.POINTER(ctypes.c_ubyte),
            wintypes.LPWSTR, ctypes.c_int, wintypes.UINT, wintypes.HKL]
        user32.ToUnicodeEx.restype = ctypes.c_int
        _user32 = user32
    return _user32


def _api(api):
    """La API recibida o, si no hay, la de Windows; None fuera de Windows."""
    if api is not None:
        return api
    if sys.platform != "win32":
        return None
    return _obtener_user32()


def teclados_instalados(api=None) -> list[int]:
    """Los identificadores de los teclados instalados, en el orden de Windows."""
    api = _api(api)
    if api is None:
        return []
    from ctypes import wintypes

    cantidad = api.GetKeyboardLayoutList(0, None)
    if cantidad <= 0:
        return []
    buffer = (wintypes.HKL * cantidad)()
    api.GetKeyboardLayoutList(cantidad, buffer)
    return list(buffer)


def teclas_virtuales(exploracion: int, api=None) -> list[int]:
    """Las teclas virtuales de una tecla física, una por teclado y sin repetir.

    Dos teclados pueden compartir la misma tecla virtual; en ese caso se
    registra una sola vez.
    """
    api = _api(api)
    if api is None:
        return []
    codigos: list[int] = []
    for teclado in teclados_instalados(api):
        codigo = api.MapVirtualKeyExW(
            exploracion, _MAPVK_VSC_TO_VK, teclado)
        if codigo and codigo not in codigos:
            codigos.append(codigo)
    return codigos


def caracter(exploracion: int, teclado: int, api=None) -> str:
    """Lo que escribe una tecla física con ese teclado, sin modificadores."""
    api = _api(api)
    if api is None:
        return ""
    import ctypes

    codigo = api.MapVirtualKeyExW(exploracion, _MAPVK_VSC_TO_VK, teclado)
    if not codigo:
        return ""
    estado = (ctypes.c_ubyte * 256)()
    buffer = ctypes.create_unicode_buffer(8)
    escrito = api.ToUnicodeEx(
        codigo, exploracion, estado, buffer, len(buffer),
        _BANDERA_NO_TOCAR_MUERTAS, teclado)
    return buffer.value if escrito > 0 else ""


def caracter_activo(exploracion: int, api=None) -> str:
    """Lo que escribe una tecla física con el teclado activo."""
    api = _api(api)
    if api is None:
        return ""
    return caracter(exploracion, api.GetKeyboardLayout(0), api)


def texto_tecla(exploracion: int, api=None) -> str:
    """El carácter del teclado activo o el nombre de Estados Unidos."""
    return (caracter_activo(exploracion, api)
            or _NOMBRES_ESTADOS_UNIDOS.get(exploracion, ""))
