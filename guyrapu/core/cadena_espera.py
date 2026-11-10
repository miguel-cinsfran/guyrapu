# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Cadena de espera nativa de un hilo de Windows."""

from __future__ import annotations

import ctypes
import os
from ctypes import wintypes


TEXTO_SIN_CADENA = "no se pudo leer la cadena de espera de Windows."
# Medido el 10/11/2026 en Windows 11 26200: la bandera no cambia la cadena
# de un mutex entre procesos. Se pide 0x7 para seguir COM y secciones críticas fuera del proceso.
_FLAGS_CADENA = 0x7
_MAXIMO_NODOS = 16
_PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

TIPOS_NODO = {
    1: "WctCriticalSectionType",
    2: "WctSendMessageType",
    3: "WctMutexType",
    4: "WctAlpcType",
    5: "WctComType",
    6: "WctThreadWaitType",
    7: "WctProcessWaitType",
    8: "WctThreadType",
    9: "WctComActivationType",
    10: "WctUnknownType",
    11: "WctSocketIoType",
    12: "WctSmbIoType",
}

ESTADOS_NODO = {
    1: "WctStatusNoAccess",
    2: "WctStatusRunning",
    3: "WctStatusBlocked",
    4: "WctStatusPidOnly",
    5: "WctStatusPidOnlyRpcss",
    6: "WctStatusOwned",
    7: "WctStatusNotOwned",
    8: "WctStatusAbandoned",
    9: "WctStatusUnknown",
    10: "WctStatusError",
}


class _ObjetoBloqueo(ctypes.Structure):
    _fields_ = [
        ("nombre", ctypes.c_wchar * 128),
        ("tiempo_espera", ctypes.c_longlong),
        ("alerta", wintypes.DWORD),
    ]


class _ObjetoHilo(ctypes.Structure):
    _fields_ = [
        ("proceso", wintypes.DWORD),
        ("hilo", wintypes.DWORD),
        ("espera_ms", wintypes.DWORD),
        ("cambios_contexto", wintypes.DWORD),
    ]


class _DatosNodo(ctypes.Union):
    _fields_ = [("bloqueo", _ObjetoBloqueo), ("hilo", _ObjetoHilo)]


class _NodoNativo(ctypes.Structure):
    _fields_ = [
        ("tipo", ctypes.c_int),
        ("estado", ctypes.c_int),
        ("datos", _DatosNodo),
    ]


def texto_sin_cadena() -> str:
    """Texto fijo para cuando Windows no entrega la cadena."""
    return TEXTO_SIN_CADENA


def componer_cadena_espera(nodos) -> str:
    """Convierte los nodos en una línea por nodo, sin lanzar excepciones."""
    if not nodos:
        return TEXTO_SIN_CADENA
    lineas = []
    for numero, nodo in enumerate(nodos):
        try:
            tipo = nodo.get("tipo") or "desconocido"
            estado = nodo.get("estado") or "desconocido"
            partes = [f"nodo {numero}", tipo, f"estado={estado}"]
            if tipo == "WctThreadType":
                partes.append(f"proceso={nodo.get('proceso')}")
                partes.append(
                    f"ejecutable={nodo.get('ejecutable') or 'desconocido'}")
                partes.append(f"hilo={nodo.get('hilo')}")
                partes.append(f"ms_espera={nodo.get('ms_espera')}")
            lineas.append(" ".join(partes))
        except Exception:
            lineas.append(f"nodo {numero} desconocido")
    return "\n".join(lineas)


def _configurar_prototipos(advapi32, kernel32) -> None:
    advapi32.OpenThreadWaitChainSession.argtypes = [
        wintypes.DWORD, ctypes.c_void_p]
    advapi32.OpenThreadWaitChainSession.restype = ctypes.c_void_p
    advapi32.GetThreadWaitChain.argtypes = [
        ctypes.c_void_p, ctypes.c_size_t, wintypes.DWORD, wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD), ctypes.POINTER(_NodoNativo),
        ctypes.POINTER(wintypes.BOOL)]
    advapi32.GetThreadWaitChain.restype = wintypes.BOOL
    advapi32.CloseThreadWaitChainSession.argtypes = [ctypes.c_void_p]
    advapi32.CloseThreadWaitChainSession.restype = wintypes.BOOL
    kernel32.OpenProcess.argtypes = [
        wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.QueryFullProcessImageNameW.argtypes = [
        wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR,
        ctypes.POINTER(wintypes.DWORD)]
    kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL


def _nombre_ejecutable(kernel32, proceso: int) -> str:
    handle = kernel32.OpenProcess(
        _PROCESS_QUERY_LIMITED_INFORMATION, False, proceso)
    if not handle:
        return ""
    try:
        tamano = wintypes.DWORD(260)
        bufer = ctypes.create_unicode_buffer(tamano.value)
        if not kernel32.QueryFullProcessImageNameW(
                handle, 0, bufer, ctypes.byref(tamano)):
            return ""
        return (bufer.value or "").rsplit("\\", 1)[-1].rsplit("/", 1)[-1]
    finally:
        kernel32.CloseHandle(handle)


def _nodo_a_diccionario(kernel32, nodo: _NodoNativo) -> dict:
    tipo = TIPOS_NODO.get(nodo.tipo, f"desconocido_{nodo.tipo}")
    resultado = {
        "tipo": tipo,
        "estado": ESTADOS_NODO.get(nodo.estado, f"desconocido_{nodo.estado}"),
    }
    if tipo == "WctThreadType":
        proceso = int(nodo.datos.hilo.proceso)
        try:
            ejecutable = _nombre_ejecutable(kernel32, proceso)
        except Exception:
            ejecutable = ""
        resultado.update({
            "proceso": proceso,
            "ejecutable": ejecutable,
            "hilo": int(nodo.datos.hilo.hilo),
            "ms_espera": int(nodo.datos.hilo.espera_ms),
        })
    return resultado


def leer_cadena_espera(identificador: int | None) -> list[dict]:
    """Devuelve los nodos de la cadena, o una lista vacía si no se puede leer."""
    if os.name != "nt" or not identificador:
        return []
    advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _configurar_prototipos(advapi32, kernel32)
    sesion = advapi32.OpenThreadWaitChainSession(0, None)
    if not sesion:
        return []
    try:
        nodos = (_NodoNativo * _MAXIMO_NODOS)()
        cuenta = wintypes.DWORD(_MAXIMO_NODOS)
        ciclo = wintypes.BOOL()
        if not advapi32.GetThreadWaitChain(
                sesion, 0, _FLAGS_CADENA, int(identificador),
                ctypes.byref(cuenta), nodos, ctypes.byref(ciclo)):
            return []
        return [_nodo_a_diccionario(kernel32, nodos[i])
                for i in range(cuenta.value)]
    finally:
        advapi32.CloseThreadWaitChainSession(sesion)


def cadena_espera_de_hilo(identificador: int | None) -> str:
    """Devuelve la cadena ya en texto, o el texto fijo si no se pudo leer."""
    try:
        return componer_cadena_espera(leer_cadena_espera(identificador))
    except Exception:
        return TEXTO_SIN_CADENA
