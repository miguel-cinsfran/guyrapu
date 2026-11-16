# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Ciclo de vida de subprocesos con cancelación y tope."""

import contextlib
import logging
import os
import subprocess
import threading
import time
from enum import Enum


logger = logging.getLogger(__name__)


class Estado(str, Enum):
    exito = "exito"
    fallo = "fallo"
    cancelado = "cancelado"
    vencido = "vencido"


def terminar_arbol(proceso):
    """Corta el proceso y a sus hijos. Nunca lanza excepciones.

    En Windows ejecuta taskkill con /T (árbol) y /F ANTES de que el padre
    muera, porque si el padre ya murió /T no encuentra a los hijos, y
    después espera al proceso con tope. Fuera de Windows usa terminate
    y kill como antes.
    """
    try:
        pid = getattr(proceso, "pid", None)
        if os.name == "nt" and isinstance(pid, int):
            _terminar_arbol_windows(proceso, pid)
            return
        _terminar_arbol_fuera_de_windows(proceso)
    except Exception as exc:
        logger.debug("terminar árbol: %s", exc)


def _terminar_arbol_windows(proceso, pid):
    try:
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except Exception as exc:
        logger.debug("taskkill del árbol: %s", exc)
    try:
        proceso.wait(timeout=5)
        return
    except subprocess.TimeoutExpired:
        pass
    except Exception as exc:
        logger.debug("espera del árbol: %s", exc)
        return
    try:
        proceso.kill()
    except Exception as exc:
        logger.debug("kill del árbol: %s", exc)
    try:
        proceso.wait(timeout=5)
    except Exception as exc:
        logger.debug("espera final del árbol: %s", exc)


def _terminar_arbol_fuera_de_windows(proceso):
    try:
        proceso.terminate()
    except OSError:
        pass
    except Exception as exc:
        logger.debug("terminate: %s", exc)
    try:
        proceso.wait(timeout=2)
        return
    except subprocess.TimeoutExpired:
        pass
    except Exception as exc:
        logger.debug("espera: %s", exc)
        return
    try:
        proceso.kill()
    except OSError:
        pass
    except Exception as exc:
        logger.debug("kill: %s", exc)
    try:
        proceso.wait()
    except Exception as exc:
        logger.debug("espera final: %s", exc)


def _terminar(proceso):
    terminar_arbol(proceso)


def _leer_carpeta_dll_heredada():
    """Carga kernel32 y lee la carpeta de DLL heredada del cargador.

    Devuelve el núcleo y la carpeta, o None y "" si falla o no hay ninguna.
    """
    if os.name != "nt":
        return None, ""
    try:
        import ctypes
        from ctypes import wintypes
        nucleo = ctypes.WinDLL("kernel32", use_last_error=True)
        nucleo.GetDllDirectoryW.argtypes = [wintypes.DWORD,
                                            wintypes.LPWSTR]
        nucleo.GetDllDirectoryW.restype = wintypes.DWORD
        nucleo.SetDllDirectoryW.argtypes = [wintypes.LPCWSTR]
        nucleo.SetDllDirectoryW.restype = wintypes.BOOL
        bufer = ctypes.create_unicode_buffer(32768)
        if nucleo.GetDllDirectoryW(32768, bufer) > 0:
            return nucleo, bufer.value
        return nucleo, ""
    except Exception as exc:
        logger.debug("carpeta de DLL heredada, lectura: %s", exc)
        return None, ""


@contextlib.contextmanager
def sin_carpeta_dll_heredada():
    """El código de adentro del bloque lanza sus hijos sin la carpeta de DLL que heredó del cargador.

    El cargador de PyInstaller llama a SetDllDirectoryW con la carpeta
    _internal de la app. Un proceso hijo la hereda y busca ahí sus DLL
    antes que en System32, lo que deja archivos de la app en uso. Dentro
    de este contexto el hijo no ve esa carpeta; al salir se restaura tal
    como estaba, aunque el bloque lance. Fuera de Windows, si ctypes
    falla o si no hay carpeta fijada, no hace nada y nunca lanza.
    """
    nucleo, anterior = _leer_carpeta_dll_heredada()
    if nucleo is None or not anterior:
        yield
        return
    quitada = False
    try:
        if nucleo.SetDllDirectoryW(None):
            quitada = True
        else:
            logger.debug("no se pudo quitar la carpeta de DLL heredada")
    except Exception as exc:
        logger.debug("carpeta de DLL heredada, quitarla: %s", exc)
        quitada = False
    if not quitada:
        yield
        return
    try:
        yield
    finally:
        try:
            nucleo.SetDllDirectoryW(anterior)
        except Exception as exc:
            logger.debug("carpeta de DLL heredada, restaurarla: %s", exc)


_JOB_APP = None
_BLOQUEO_JOB = threading.Lock()


def _definir_estructuras_job():
    """Las estructuras de ctypes de los límites extendidos del Job Object."""
    import ctypes
    from ctypes import wintypes

    class _LimitesBasicos(ctypes.Structure):
        _fields_ = [
            ("PerProcessUserTimeLimit", ctypes.c_int64),
            ("PerJobUserTimeLimit", ctypes.c_int64),
            ("LimitFlags", wintypes.DWORD),
            ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t),
            ("ActiveProcessLimit", wintypes.DWORD),
            ("Affinity", ctypes.c_size_t),
            ("PriorityClass", wintypes.DWORD),
            ("SchedulingClass", wintypes.DWORD),
        ]

    class _Contadores(ctypes.Structure):
        _fields_ = [
            ("ReadOperationCount", ctypes.c_ulonglong),
            ("WriteOperationCount", ctypes.c_ulonglong),
            ("OtherOperationCount", ctypes.c_ulonglong),
            ("ReadTransferCount", ctypes.c_ulonglong),
            ("WriteTransferCount", ctypes.c_ulonglong),
            ("OtherTransferCount", ctypes.c_ulonglong),
        ]

    class _LimitesExtendidos(ctypes.Structure):
        _fields_ = [
            ("BasicLimitInformation", _LimitesBasicos),
            ("IoInfo", _Contadores),
            ("ProcessMemoryLimit", ctypes.c_size_t),
            ("JobMemoryLimit", ctypes.c_size_t),
            ("PeakProcessMemoryUsed", ctypes.c_size_t),
            ("PeakJobMemoryUsed", ctypes.c_size_t),
        ]

    return _LimitesExtendidos


def _crear_job(limites_extendidos):
    """Crea el Job Object con el límite de matar al cerrar, o None."""
    import ctypes
    from ctypes import wintypes
    nucleo = ctypes.WinDLL("kernel32", use_last_error=True)
    trabajo = nucleo.CreateJobObjectW(None, None)
    if not trabajo:
        logger.debug("CreateJobObjectW devolvió NULL")
        return None
    info = limites_extendidos()
    ctypes.memset(ctypes.byref(info), 0, ctypes.sizeof(info))
    info.BasicLimitInformation.LimitFlags = 0x2000
    nucleo.SetInformationJobObject.argtypes = [
        wintypes.HANDLE, ctypes.c_int,
        wintypes.LPVOID, wintypes.DWORD,
    ]
    nucleo.SetInformationJobObject.restype = wintypes.BOOL
    if not nucleo.SetInformationJobObject(
            trabajo, 9, ctypes.byref(info),
            ctypes.sizeof(info)):
        logger.debug("SetInformationJobObject falló")
        try:
            nucleo.CloseHandle(trabajo)
        except Exception as error:
            logger.debug("no se pudo cerrar el trabajo tras el fallo: %s", error)
        return None
    return trabajo


def _job_app():
    """Job Object único de la app, o None si no se pudo crear."""
    global _JOB_APP
    with _BLOQUEO_JOB:
        if _JOB_APP is not None:
            return _JOB_APP
        try:
            trabajo = _crear_job(_definir_estructuras_job())
            if not trabajo:
                return None
            # Se guarda a nivel de módulo y su handle no se cierra nunca:
            # al cerrarse el proceso de la app, Windows mata a los
            # procesos asignados.
            _JOB_APP = trabajo
            return _JOB_APP
        except Exception as exc:
            logger.debug("job de la app: %s", exc)
            return None


def _vincular_por_pid(nucleo, trabajo, pid):
    from ctypes import wintypes
    nucleo.OpenProcess.argtypes = [
        wintypes.DWORD, wintypes.BOOL, wintypes.DWORD,
    ]
    nucleo.OpenProcess.restype = wintypes.HANDLE
    handle = nucleo.OpenProcess(0x0100 | 0x0001, False, pid)
    if not handle:
        logger.debug("OpenProcess falló para pid=%s", pid)
        return
    try:
        if not nucleo.AssignProcessToJobObject(
                trabajo, handle):
            logger.debug("AssignProcessToJobObject falló")
    finally:
        try:
            nucleo.CloseHandle(handle)
        except Exception as error:
            logger.debug("no se pudo cerrar el handle del proceso: %s", error)


def vincular_a_la_app(proceso):
    """Ata el proceso a la vida de la app. Nunca lanza ni impide lanzar.

    En Windows asigna el proceso al Job Object único con
    JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE: cuando la app termina por
    cualquier motivo, Windows mata a ese proceso y a los que él haya
    creado. Fuera de Windows no hace nada.
    """
    if os.name != "nt":
        return
    try:
        import ctypes
        from ctypes import wintypes
        trabajo = _job_app()
        if not trabajo:
            return
        nucleo = ctypes.WinDLL("kernel32", use_last_error=True)
        nucleo.AssignProcessToJobObject.argtypes = [
            wintypes.HANDLE, wintypes.HANDLE,
        ]
        nucleo.AssignProcessToJobObject.restype = wintypes.BOOL
        handle = getattr(proceso, "_handle", None)
        if isinstance(handle, int) and handle:
            if not nucleo.AssignProcessToJobObject(
                    trabajo, wintypes.HANDLE(handle)):
                logger.debug("AssignProcessToJobObject falló")
            return
        pid = getattr(proceso, "pid", None)
        if not isinstance(pid, int):
            return
        if not isinstance(proceso, subprocess.Popen):
            return
        _vincular_por_pid(nucleo, trabajo, pid)
    except Exception as exc:
        logger.debug("vincular a la app: %s", exc)


def _agregar_sin_ventana(opciones):
    if hasattr(subprocess, "CREATE_NO_WINDOW"):
        flag = subprocess.CREATE_NO_WINDOW
        if "creationflags" in opciones:
            opciones["creationflags"] = opciones["creationflags"] | flag
        else:
            opciones["creationflags"] = flag


def _esperar(proceso, cancel_event, tope_segundos):
    inicio = time.monotonic()
    while True:
        if cancel_event is not None and cancel_event.is_set():
            _terminar(proceso)
            return Estado.cancelado
        if time.monotonic() - inicio >= tope_segundos:
            _terminar(proceso)
            return Estado.vencido
        codigo = proceso.poll()
        if codigo is not None:
            if cancel_event is not None and cancel_event.is_set():
                proceso.wait()
                return Estado.cancelado
            proceso.wait()
            if codigo == 0:
                return Estado.exito
            return Estado.fallo
        time.sleep(0.05)


def ejecutar(argumentos, cancel_event=None, tope_segundos=3600, **opciones):
    """Lanza argumentos con Popen y espera con cancelación y tope.

    Devuelve un Estado entre éxito, fallo, cancelado y vencido.
    Toda ruta posterior a un Popen exitoso garantiza wait.
    """
    _agregar_sin_ventana(opciones)

    try:
        proceso = subprocess.Popen(argumentos, **opciones)
    except OSError:
        return Estado.fallo
    try:
        vincular_a_la_app(proceso)
    except Exception as error:
        logger.debug("no se pudo vincular el proceso a la app: %s", error)

    try:
        return _esperar(proceso, cancel_event, tope_segundos)
    finally:
        # Garantiza recolección si por algún motivo se sale sin wait.
        # Si poll falla por error de programación, igual se termina el hijo y se propaga.
        try:
            esta_vivo = proceso.poll() is None
        except Exception:
            _terminar(proceso)
            raise
        if esta_vivo:
            _terminar(proceso)
        else:
            proceso.wait()
