# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Localiza y abre OBS solo cuando hace falta, sin robar el foco."""

import csv
import os
import subprocess
import time

from guyrapu.core import diagnostico
from guyrapu.core import paths
from guyrapu.core import subprocesos
from guyrapu.core.idioma import N_, _
from guyrapu.obs import obs_activacion
from guyrapu.obs import obs_cliente


TEXTO_ABRIENDO = N_("Abriendo OBS en segundo plano, en el área de "
                    "notificación. Puede tardar hasta un minuto.")
TEXTO_MODO_SEGURO = N_("OBS se cerró mal la última vez y va a preguntar si "
                       "iniciar en modo seguro. Elige Mostrar OBS en el menú "
                       "OBS y después iniciar normalmente.")
TEXTO_SIN_RESPUESTA = N_("OBS se abrió pero no responde. Comprueba que su "
                         "servidor WebSocket esté activado.")
TEXTO_SIN_RESPUESTA_MODO_SEGURO = N_(
    "OBS no responde. Puede estar esperando que contestes si iniciar "
    "en modo seguro: elige Mostrar OBS en el menú OBS.")
# Traductores: aviso mientras OBS ya está abierto y su servidor termina de iniciar.
TEXTO_TERMINANDO_DE_ABRIR = N_("Esperando a que OBS termine de abrirse.")

logger = diagnostico.obtener_logger(__name__)

_CLAVE_OBS = r"SOFTWARE\OBS Studio"
_CLAVE_OBS_32 = r"SOFTWARE\WOW6432Node\OBS Studio"
_EJECUTABLE = os.path.join("bin", "64bit", "obs64.exe")


class ObsNoInstalado(obs_cliente.ObsError):
    """OBS no está instalado en este equipo."""


def _leer_registro_por_defecto(clave):
    """Lee el valor predeterminado de una clave de OBS o devuelve None."""
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, clave) as subclave:
            valor, _sin_uso = winreg.QueryValueEx(subclave, "")
            return str(valor) if valor else None
    except (OSError, ValueError):
        return None


def ruta_obs(leer_registro=None, existe=os.path.isfile, entorno=os.environ):
    """Devuelve la ruta de obs64.exe o "" si no se encuentra."""
    leer = leer_registro or _leer_registro_por_defecto
    for clave in (_CLAVE_OBS, _CLAVE_OBS_32):
        try:
            base = leer(clave)
        except Exception:
            base = None
        if base:
            ruta = os.path.join(base, _EJECUTABLE)
            if existe(ruta):
                return ruta
    program_files = entorno.get("ProgramFiles", "")
    if program_files:
        ruta = os.path.join(program_files, "obs-studio", _EJECUTABLE)
        if existe(ruta):
            return ruta
    return ""


def cierre_incorrecto_previo(carpeta=None, listar=os.listdir):
    """Dice si OBS se cerró mal antes, por sus archivos sentinel run_*.

    True si hay algún archivo cuyo nombre empieza con «run_» en la
    carpeta `%APPDATA%\\obs-studio\\.sentinel`. Carpeta inexistente o
    ilegible da False, para no frenar la apertura por avisar."""
    if carpeta is None:
        carpeta = str(paths.carpeta_obs("sentinel"))
    try:
        nombres = listar(carpeta)
    except (OSError, ValueError):
        return False
    return any(str(nombre).startswith("run_") for nombre in nombres)


def borrar_marca_cierre(carpeta=None, listar=os.listdir, borrar=os.remove):
    """Borra los sentinel `run_*` para que OBS no pregunte por el modo seguro.

    True si no queda ninguno, incluso si no había. Carpeta inexistente da
    True. Cualquier otro error se registra y da False, para que quien
    llama avise igual que antes."""
    if carpeta is None:
        carpeta = str(paths.carpeta_obs("sentinel"))
    try:
        nombres = listar(carpeta)
    except FileNotFoundError:
        return True
    except (OSError, ValueError) as error:
        logger.warning("no se pudo leer la marca de cierre de OBS: %s", error)
        return False
    borrado_limpio = True
    for nombre in nombres:
        if not str(nombre).startswith("run_"):
            continue
        try:
            borrar(os.path.join(carpeta, nombre))
        except (OSError, ValueError) as error:
            logger.warning("no se pudo borrar la marca de cierre de OBS %s: %s",
                           nombre, error)
            borrado_limpio = False
    return borrado_limpio


def _modo_seguro_pendiente(hubo_cierre_incorrecto, borrar_cierre):
    """Dice si el aviso de modo seguro sigue haciendo falta al abrir OBS."""
    if not hubo_cierre_incorrecto():
        return False
    if borrar_cierre():
        logger.info("se borró la marca de cierre incorrecto de OBS")
        return False
    return True


def abrir_obs(ruta, popen=subprocess.Popen):
    """Abre OBS minimizado y sin activarse; no espera ni guarda el proceso."""
    carpeta = os.path.dirname(ruta)
    info = subprocess.STARTUPINFO()
    info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    info.wShowWindow = 7
    try:
        # OBS no trae VCRUNTIME ni MSVCP en su carpeta: sin esto las busca
        # en la _internal heredada del cargador y deja archivos en uso.
        with subprocesos.sin_carpeta_dll_heredada():
            # La ventana minimizada igual se activa sola al terminar de cargar.
            popen([ruta, "--disable-shutdown-check", "--minimize-to-tray"],
                  cwd=carpeta, startupinfo=info,
                  creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except OSError as error:
        raise obs_cliente.ObsError(_("No se pudo abrir OBS.")) from error


def _pids_obs(ejecutar=subprocess.run):
    """Los PID de obs64.exe, leídos con tasklist sin abrir una consola."""
    try:
        resultado = ejecutar(
            ["tasklist", "/FI", "IMAGENAME eq obs64.exe",
             "/FO", "CSV", "/NH"],
            capture_output=True, text=True, check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except (OSError, subprocess.SubprocessError):
        return []
    pids = []
    for fila in csv.reader((resultado.stdout or "").splitlines()):
        if len(fila) < 2 or fila[0].casefold() != "obs64.exe":
            continue
        try:
            pids.append(int(fila[1]))
        except ValueError:
            continue
    return pids


def _terminar_obs(pid, ejecutar=subprocess.run):
    """Pide a OBS que se cierre, sin forzarlo."""
    ejecutar(["taskkill", "/PID", str(pid)],
             capture_output=True, text=True, check=False,
             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))


def _pedir_cierre(pids, ejecutar) -> None:
    for pid in pids:
        try:
            _terminar_obs(pid, ejecutar)
        except (OSError, subprocess.SubprocessError) as error:
            logger.debug("no se pudo pedir el cierre de OBS %s: %s", pid,
                         error)


def cerrar_obs(en_ejecucion=obs_activacion.obs_esta_en_ejecucion,
               ejecutar=subprocess.run, dormir=time.sleep,
               reloj=time.monotonic, limite=30.0, intervalo=0.5,
               intervalo_pedido=5.0):
    """Cierra OBS sin forzarlo y devuelve si se cerró.

    En el área de notificación el primer pedido no alcanza: se repite sin
    `/F` cada `intervalo_pedido` segundos mientras OBS siga vivo.
    """
    if not en_ejecucion():
        return True
    pids = _pids_obs(ejecutar)
    _pedir_cierre(pids, ejecutar)
    inicio = reloj()
    siguiente = intervalo_pedido
    while en_ejecucion():
        transcurrido = reloj() - inicio
        if transcurrido >= limite:
            return False
        if transcurrido >= siguiente:
            _pedir_cierre(pids, ejecutar)
            siguiente = transcurrido + intervalo_pedido
        dormir(intervalo)
    return True


def _esperar_obs_abierto(probar_conexion, al_anunciar, parada, dormir, reloj,
                         limite=60.0, intervalo=2.0):
    """Espera a que un OBS ya abierto acepte el WebSocket, sin abrirlo."""
    try:
        probar_conexion()
        return False
    except Exception as error:
        logger.debug("OBS abierto todavía no responde, se reintenta: %s", error)
    if al_anunciar is not None:
        al_anunciar(_(TEXTO_TERMINANDO_DE_ABRIR))
    inicio = reloj()
    while True:
        if parada is not None and parada.is_set():
            return False
        if reloj() - inicio >= limite:
            raise obs_cliente.ObsError(
                _(obs_cliente.TEXTO_ABIERTO_SIN_RESPUESTA))
        if parada is not None and dormir is time.sleep:
            parada.wait(intervalo)
        else:
            dormir(intervalo)
        try:
            probar_conexion()
            return False
        except Exception as error:
            logger.debug("OBS abierto todavía no responde, se reintenta: %s",
                         error)


def asegurar_obs(probar_conexion, al_anunciar=None, parada=None,
                 en_ejecucion=obs_activacion.obs_esta_en_ejecucion,
                 buscar=ruta_obs, abrir=abrir_obs, dormir=time.sleep,
                 reloj=time.monotonic, limite=120.0, intervalo=2.0,
                 hubo_cierre_incorrecto=cierre_incorrecto_previo,
                 borrar_cierre=borrar_marca_cierre):
    """Abre OBS si no corre y espera a que su websocket responda."""
    if parada is not None and parada.is_set():
        return True
    if en_ejecucion():
        return _esperar_obs_abierto(probar_conexion, al_anunciar, parada, dormir, reloj)
    ruta = buscar()
    if not ruta:
        raise ObsNoInstalado(_("OBS no está instalado en este equipo. "
                               "Instálalo desde obsproject.com y vuelve a "
                               "intentarlo."))
    modo_seguro = _modo_seguro_pendiente(hubo_cierre_incorrecto, borrar_cierre)
    if al_anunciar is not None:
        al_anunciar(_(TEXTO_ABRIENDO))
        if modo_seguro:
            al_anunciar(_(TEXTO_MODO_SEGURO))
    abrir(ruta)
    inicio = reloj()
    while True:
        if parada is not None and parada.is_set():
            return True
        try:
            probar_conexion()
            return True
        except Exception as error:
            logger.debug("no se pudo conectar con OBS, se reintenta: %s", error)
        if reloj() - inicio >= limite:
            if modo_seguro:
                raise obs_cliente.ObsError(_(TEXTO_SIN_RESPUESTA_MODO_SEGURO))
            raise obs_cliente.ObsError(_(TEXTO_SIN_RESPUESTA))
        if parada is not None and dormir is time.sleep:
            parada.wait(intervalo)
        else:
            dormir(intervalo)
