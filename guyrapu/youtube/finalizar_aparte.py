# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Fines de directo que se terminan con la app cerrada.

Al salir con un fin pendiente, la app lanza este módulo como un proceso
aparte, sin ventana y que sobrevive al cierre. Reintenta el fin cada 30
segundos durante 6 horas y deja constancia en su registro. No abre ventanas
ni toma el mutex de instancia única: si ya hay otro proceso de este modo,
sale enseguida.
"""

from __future__ import annotations

import ctypes
import subprocess
import time
from datetime import datetime

from guyrapu.core import diagnostico, paths
from guyrapu.core.idioma import _
from guyrapu.youtube import credenciales, emision, fin_pendiente, youtube_api

logger = diagnostico.obtener_logger(__name__)

INTERVALO = 30.0
LIMITE = 6 * 60 * 60

_NOMBRE_MUTEX = "Guyrapu_FinalizarPendientes_Mutex"

_ERROR_ACCESS_DENIED = 5      # el mutex existe pero es de otro usuario / instancia elevada
_ERROR_ALREADY_EXISTS = 183   # el mutex ya lo tiene otro proceso de este modo

_mutex_handle = None


def _guardar_token_si_hay(cliente) -> None:
    try:
        nuevo = cliente.token_actualizado()
    except Exception:
        nuevo = None
    if nuevo:
        try:
            credenciales.guardar_campo("token", nuevo)
        except Exception as error:
            logger.warning("no se pudo guardar el token actualizado: %s", error)


def _registrar(texto) -> None:
    """Anota una línea con fecha en el registro del modo."""
    linea = f"{datetime.now().isoformat(timespec='seconds')} {texto}\n"
    try:
        ruta = paths.fin_pendiente_log()
        ruta.parent.mkdir(parents=True, exist_ok=True)
        with open(ruta, "a", encoding="utf-8") as archivo:
            archivo.write(linea)
    except Exception as error:
        logger.warning("no se pudo escribir el registro de fines pendientes: %s",
                       error)


def _crear_mutex(nombre):
    """Crea el mutex y devuelve (handle, GetLastError); (None, None) sin Windows."""
    try:
        # Sin restype ctypes devuelve un int de 32 bits y trunca el HANDLE en x64.
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateMutexW.restype = ctypes.c_void_p
        handle = kernel32.CreateMutexW(None, False, nombre)
        return handle, ctypes.get_last_error()
    except Exception:
        return None, None


def _tomar_mutex() -> bool:
    """Dice si este proceso puede correr el modo; el handle queda vivo."""
    global _mutex_handle
    _mutex_handle, error = _crear_mutex(_NOMBRE_MUTEX)
    if error is None:
        return True
    return error not in (_ERROR_ALREADY_EXISTS, _ERROR_ACCESS_DENIED)


def lanzar():
    """Lanza el modo aparte, sin ventana y desprendido de la app."""
    try:
        return subprocess.Popen(
            paths.orden_de_la_app() + ["--finalizar-pendientes"],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, close_fds=True,
            cwd=str(paths.carpeta_instalacion()),
            creationflags=(subprocess.CREATE_NO_WINDOW
                           | subprocess.DETACHED_PROCESS
                           | subprocess.CREATE_NEW_PROCESS_GROUP))
    except Exception as error:
        logger.warning("no se pudo lanzar la finalización de los directos "
                       "pendientes: %s", error)
        return None


def _cliente():
    """Cliente de YouTube con la sesión guardada, o None si no hay sesión."""
    try:
        datos = credenciales.cargar()
        if not credenciales.hay_sesion(datos):
            return None
        return youtube_api.ClienteYouTube(credenciales.efectivas(datos))
    except Exception as error:
        logger.warning("no se pudo abrir la sesión de YouTube: %s", error)
        return None


def _finalizar_reintentando(cliente, id_video, reloj, dormir, limite) -> bool:
    """Reintenta el fin de un id y deja una línea por intento."""
    def intento():
        try:
            emision.finalizar_en_youtube(cliente, id_video)
        except Exception as error:
            _registrar(f"{id_video}: no se confirmó ({type(error).__name__})")
            raise
        else:
            _registrar(f"{id_video}: finalizado")
        finally:
            _guardar_token_si_hay(cliente)

    return fin_pendiente.reintentar(
        intento, dormir or time.sleep, reloj or time.monotonic,
        intervalo=INTERVALO, limite=limite)


def principal(argv=None, reloj=None, dormir=None) -> int:
    """Termina los fines pendientes y sale; 0 siempre que la app lo espere."""
    if not _tomar_mutex():
        return 0
    ruta = paths.fin_pendiente()
    pendientes = fin_pendiente.leer(ruta)
    if not pendientes:
        _registrar(_("Sin directos pendientes."))
        return 0
    cliente = _cliente()
    if cliente is None:
        # Traductores: {cuantos} es la cantidad de directos sin finalizar.
        _registrar(_("Sin sesión de YouTube: quedan {cuantos} directos "
                     "pendientes.").format(cuantos=len(pendientes)))
        return 0
    ahora = reloj or time.monotonic
    inicio = ahora()
    finalizados, quedan = 0, 0
    for entrada in pendientes:
        restante = LIMITE - (ahora() - inicio)
        if restante <= 0:
            quedan += 1
            continue
        if _finalizar_reintentando(cliente, entrada["id"], reloj, dormir,
                                   restante):
            fin_pendiente.quitar(ruta, entrada["id"])
            finalizados += 1
        else:
            quedan += 1
    # Traductores: {finalizados} y {quedan} son cantidades de directos.
    _registrar(_("Resultado: {finalizados} finalizados, {quedan} "
                 "pendientes.").format(
                     finalizados=finalizados, quedan=quedan))
    return 0
