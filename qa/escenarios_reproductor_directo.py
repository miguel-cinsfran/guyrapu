# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Un directo de YouTube que sigue sonando y se recupera solo de un corte.

Mide las dos cosas que ningún escenario del banco miraba: que durante un
minuto ninguna lectura del reproductor deje de estar en «playing», y que tras
matar el ffmpeg del relevo vuelva a «playing» por su cuenta. Pide un directo
real, como `reproductor_en_marcha`, así que no entra en la corrida completa.

La lógica que juzga las lecturas es pura y se prueba aparte. Lo que abre la
aplicación y mata el proceso se prueba corriéndolo contra un directo vivo.
"""

from __future__ import annotations

import ctypes
import os
import signal
import time
from ctypes import wintypes

from banco_app import (
    Aplicacion, DIRECTO_YOUTUBE, Resultado, conectar_de_verdad,
)

# Lo que la aplicación dice cuando el directo se corta o el relevo se reabre.
# Se busca como fragmento y sin distinguir mayúsculas.
FRASES_DE_CORTE = (
    "se interrumpió",
    "interrumpido",
    "con cortes",
    "reconectando el directo",
)

FRAGMENTO_RECONEXION = "reconectando"

SEGUNDOS_LECTURA = 5.0
SEGUNDOS_CONTINUIDAD = 60.0
SEGUNDOS_CONTINUIDAD_TRAS_CORTE = 30.0
SEGUNDOS_VUELTA = 45.0
INTERVALO_VUELTA = 0.5

TH32CS_SNAPPROCESS = 0x00000002
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value


def revisar_continuidad(lecturas, anuncios=()):
    """El problema de una serie de lecturas, o None si todas son «playing».

    `lecturas` son pares (segundos desde el inicio, estado). `anuncios` son
    los textos que la aplicación dijo en ese tiempo.
    """
    for numero, (segundo, estado) in enumerate(lecturas, 1):
        if estado != "playing":
            return (f"la lectura {numero} a los {segundo:g} s no era "
                    f"«playing», dijo «{estado}»")
    for texto in anuncios:
        bajo = texto.lower()
        if any(frase in bajo for frase in FRASES_DE_CORTE):
            return f"la aplicación anunció un corte: «{texto[:120]}»"
    return None


def segundos_hasta_volver(lecturas, tope, hubo_anuncio=False):
    """(segundos, True) de la primera vuelta a «playing», o (None, False).

    Solo cuenta la vuelta si antes hubo una lectura que no era «playing» o si
    la aplicación anunció una reconexión después del corte. En ese segundo
    caso, la última lectura es la primera posterior al anuncio, porque quien
    llama mira los anuncios en cada vuelta del bucle.
    """
    hubo_corte = False
    for segundo, estado in lecturas:
        if segundo > tope:
            break
        if estado != "playing":
            hubo_corte = True
        elif hubo_corte:
            return segundo, True
    if hubo_anuncio and lecturas:
        segundo, estado = lecturas[-1]
        if segundo <= tope and estado == "playing":
            return segundo, True
    return None, False


class _EntradaDeProceso(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("cntUsage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("th32DefaultHeapID", ctypes.c_size_t),
        ("th32ModuleID", wintypes.DWORD),
        ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD),
        ("pcPriClassBase", wintypes.LONG),
        ("dwFlags", wintypes.DWORD),
        ("szExeFile", wintypes.WCHAR * 260),
    ]


def _hijos_de(pid_padre):
    """(pid, ejecutable) de los procesos hijos de `pid_padre`."""
    nucleo = ctypes.WinDLL("kernel32", use_last_error=True)
    nucleo.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    nucleo.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    nucleo.Process32FirstW.argtypes = [
        wintypes.HANDLE, ctypes.POINTER(_EntradaDeProceso)]
    nucleo.Process32FirstW.restype = wintypes.BOOL
    nucleo.Process32NextW.argtypes = [
        wintypes.HANDLE, ctypes.POINTER(_EntradaDeProceso)]
    nucleo.Process32NextW.restype = wintypes.BOOL
    nucleo.CloseHandle.argtypes = [wintypes.HANDLE]
    nucleo.CloseHandle.restype = wintypes.BOOL

    instantanea = nucleo.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if instantanea == INVALID_HANDLE_VALUE:
        return []
    hijos = []
    entrada = _EntradaDeProceso()
    entrada.dwSize = ctypes.sizeof(_EntradaDeProceso)
    try:
        if not nucleo.Process32FirstW(instantanea, ctypes.byref(entrada)):
            return []
        while True:
            if entrada.th32ParentProcessID == pid_padre:
                hijos.append((entrada.th32ProcessID, entrada.szExeFile))
            if not nucleo.Process32NextW(instantanea, ctypes.byref(entrada)):
                break
    finally:
        nucleo.CloseHandle(instantanea)
    return hijos


def _ffmpeg_del_relevo(pid_padre):
    """El pid del ffmpeg hijo del relevo, o None si el directo no fue por relevo."""
    for pid, nombre in _hijos_de(pid_padre):
        bajo = (nombre or "").lower()
        # imageio_ffmpeg lo llama ffmpeg-win-x86_64-v<versión>.exe, no
        # ffmpeg.exe.
        if bajo.startswith("ffmpeg") and bajo.endswith(".exe"):
            return pid
    return None


def _leer_estado(app):
    """El estado del reproductor según la sonda, o «sin respuesta»."""
    try:
        return (app.reproductor() or {}).get("estado", "desconocido")
    except Exception:
        return "sin respuesta"


def _resumen(textos, limite: int = 160) -> str:
    """Lo que dijo la aplicación, en una línea y recortado."""
    junto = " | ".join(t.strip() for t in textos if t.strip())
    return junto[:limite] if junto else "nada"


def _continuidad(app, res, segundos):
    """Toma una lectura cada 5 s y anota el veredicto de la continuidad."""
    inicio = len(app.anuncios)
    lecturas = []
    arranque = time.monotonic()
    while True:
        transcurrido = time.monotonic() - arranque
        lecturas.append((round(transcurrido, 1), _leer_estado(app)))
        if transcurrido >= segundos:
            break
        time.sleep(min(SEGUNDOS_LECTURA, segundos - transcurrido))
    anuncios = [a.get("texto", "") for a in app.anuncios[inicio:]]
    problema = revisar_continuidad(lecturas, anuncios)
    if problema:
        res.fallo(f"reproductor directo ({segundos:g} s): {problema}")
    else:
        res.nota(f"reproductor directo ({segundos:g} s): {len(lecturas)} "
                 f"lecturas «playing»")


def _cortar_relevo(app, res) -> bool:
    """Mata el ffmpeg del relevo y espera a que el reproductor vuelva solo."""
    pid_app = app.pedir("pid").get("datos", {}).get("pid")
    pid_ffmpeg = (_ffmpeg_del_relevo(pid_app)
                  if isinstance(pid_app, int) else None)
    if pid_ffmpeg is None:
        res.no_probado("reproductor directo: sin probar el corte, no hay un "
                       "ffmpeg hijo de la app (el directo no fue por relevo)")
        return False
    inicio = len(app.anuncios)
    corte = time.monotonic()
    try:
        # En Windows, os.kill con SIGTERM mata ese proceso y solo ese.
        os.kill(pid_ffmpeg, signal.SIGTERM)
    except OSError as exc:
        res.fallo(f"reproductor directo: no se pudo cortar el ffmpeg del "
                  f"relevo (pid {pid_ffmpeg}), {exc}")
        return False
    lecturas = []
    volvio = False
    segundos = None
    while True:
        hubo_anuncio = any(
            FRAGMENTO_RECONEXION in a.get("texto", "").lower()
            for a in app.anuncios[inicio:])
        transcurrido = time.monotonic() - corte
        lecturas.append((round(transcurrido, 1), _leer_estado(app)))
        segundos, volvio = segundos_hasta_volver(
            lecturas, SEGUNDOS_VUELTA, hubo_anuncio)
        if volvio or transcurrido >= SEGUNDOS_VUELTA:
            break
        time.sleep(INTERVALO_VUELTA)
    dichos = _resumen([a.get("texto", "") for a in app.anuncios[inicio:]])
    if not volvio:
        res.fallo(f"reproductor directo: no volvió a «playing» en "
                  f"{SEGUNDOS_VUELTA:g} s tras cortar el ffmpeg; "
                  f"{len(lecturas)} lecturas, dijo «{dichos}»")
        return False
    res.nota(f"reproductor directo: volvió a «playing» {segundos:g} s después "
             f"del corte, con {len(lecturas)} lecturas, dijo «{dichos}»")
    return True


def escenario_reproductor_directo(app: Aplicacion, args, res: Resultado):
    """Un directo real sigue sonando y se recupera solo de un corte del relevo.

    Pide el directo de `--url-youtube` y espera a que la aplicación diga
    «Reproduciendo». Mide la continuidad un minuto, mata el ffmpeg del relevo,
    espera a que vuelva por su cuenta y mide otro medio minuto.
    """
    url = getattr(args, "url_youtube", None) or DIRECTO_YOUTUBE
    res.nota(f"reproductor directo: {url}")
    n = len(app.anuncios)
    if not conectar_de_verdad(app, res, url, "reproductor directo"):
        return
    if not app.esperar_dicho("reproduciendo", segundos=60, desde=n):
        res.fallo("reproductor directo: no se oyó «Reproduciendo» en 60 s")
        return
    limite = time.monotonic() + 60
    estado = _leer_estado(app)
    while estado != "playing" and time.monotonic() < limite:
        time.sleep(0.25)
        estado = _leer_estado(app)
    if estado != "playing":
        res.fallo("reproductor directo: no llegó a «playing» en 60 s; "
                  f"estado «{estado}»")
        return
    res.nota("reproductor directo: reproduce el directo")
    _continuidad(app, res, SEGUNDOS_CONTINUIDAD)
    if not _cortar_relevo(app, res):
        return
    _continuidad(app, res, SEGUNDOS_CONTINUIDAD_TRAS_CORTE)
