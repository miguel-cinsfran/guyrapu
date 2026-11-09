# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Directo real de prueba por Restream, para correr a mano.

Un perfil vertical con TikTok, YouTube no listado y los dos chats durante un
minuto, conducido por UI Automation. Antes de tocar nada frena si hay un
directo en curso. Al terminar deja los destinos, los archivos y el vídeo como
estaban. No corre en la suite ni en el hook.
"""

from __future__ import annotations

import argparse
import importlib.util
from datetime import datetime
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "qa"))

from guyrapu.core.config import APP_NAME  # noqa: E402
from guyrapu.restream import perfiles  # noqa: E402

import titulos_restream  # noqa: E402
from directo_comun import (  # noqa: E402
    NOMBRE_PERFIL, PRIVACIDAD_ESPERADA, armar_perfil,
    comparar_destinos_en_vivo, comprobar_chats,
    destino_tiktok,  # noqa: F401  (lo importan las pruebas de este módulo)
    esperar_anuncio, imprimir, limpiar,
)
from directo_real import (  # noqa: E402
    OK_FIN, _LANZADOR, _buscar_video_por_titulo,
    _cliente_youtube, _control, _dialogo_hijo, _esperar_estado,
    _guardar_token_si_renovo, _leer_anuncios, _leer_valor, _limpiar_sentinel,
    _obs_en_ejecucion, _ventana, armar_titulo, extraer_id_video,
)

PREFIJO_OPCION = "restream:"
OK_AL_AIRE = "directo iniciado en youtube"
ERRORES_AL_AIRE = ("no se pudo", "error", "falló", "no tiene",
                   "todavía no muestra")
SEGUNDOS_WS = 20


def _ayuda() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Directo real por Restream: perfil vertical con TikTok y "
                    "YouTube no listado, de un minuto, que se finaliza y se "
                    "borra. Corre a mano, nunca en la suite.")
    parser.add_argument("--duracion", type=int, default=60,
                        help="segundos al aire antes de finalizar "
                             "(por defecto 60)")
    parser.add_argument("--timeout-salida", type=int, default=240,
                        help="segundos esperando «Directo iniciado en YouTube»")
    parser.add_argument("--timeout-chat", type=int, default=90,
                        help="segundos esperando los dos chats conectados")
    parser.add_argument("--timeout-fin", type=int, default=90,
                        help="segundos esperando «Transmisión detenida»")
    return parser


def _paso_cero() -> tuple[bool, str]:
    guion = RAIZ / "herramientas" / "sin_directo.py"
    try:
        salida = subprocess.run([sys.executable, str(guion)],
                                capture_output=True, text=True, timeout=60)
    except Exception as exc:
        return (False, f"no se pudo comprobar: {exc}")
    texto = ((salida.stdout or "") + (salida.stderr or "")).strip()
    return (salida.returncode == 0, texto)


def _respaldar_todo(estado, anotar) -> bool:
    for clave, ruta in estado["rutas"].items():
        respaldo = None
        if Path(ruta).exists():
            try:
                respaldo = tempfile.mktemp(
                    prefix=f"directo-restream-{clave}-")
                shutil.copy2(ruta, respaldo)
            except OSError:
                if clave == "config":
                    anotar("respaldo de config.ini", False,
                           "no se pudo copiar")
                    return False
        estado["respaldos"][clave] = respaldo
    anotar("respaldos", True, "config.ini, sounds.ini y perfiles_restream.json")
    estado["estaba_obs"] = _obs_en_ejecucion()
    if not estado["estaba_obs"]:
        _limpiar_sentinel()
    anotar("OBS sin modo seguro", True,
           "sentinel limpio" if not estado["estaba_obs"]
           else "ya estaba abierto, no se toca el sentinel")
    return True


def _guardar_perfil(estado, anotar) -> bool:
    perfil = armar_perfil(estado["canal_tiktok"],
                          armar_titulo(time.strftime("%H:%M")))
    otros = [previo for previo in perfiles.cargar(estado["rutas"]["perfiles"])
             if previo.nombre.strip().casefold() != NOMBRE_PERFIL.casefold()]
    problemas = perfiles.validar(perfil, otros)
    if problemas:
        anotar("perfil de Restream", False, "; ".join(problemas))
        return False
    perfiles.guardar(estado["rutas"]["perfiles"], otros + [perfil])
    estado["perfil_guardado"] = True
    anotar("perfil de Restream", True, f"«{perfil.nombre}», vertical, YouTube y ambos chats")
    destino = PREFIJO_OPCION + NOMBRE_PERFIL
    from guyrapu.core import config
    config.guardar_opcion(estado["rutas"]["config"], "transmision", "destino",
                          destino)
    anotar("destino en config.ini", True, destino)
    estado["titulo"] = perfil.directo["titulo"]
    return True


def _preparar(anotar, cuenta_mod):
    estado = titulos_restream.leer_cuenta(anotar, cuenta_mod)
    if estado is None or not _respaldar_todo(estado, anotar):
        return None
    if not _guardar_perfil(estado, anotar):
        return None
    return estado


def _lanzar_app(estado, anotar) -> bool:
    tmpdir = tempfile.mkdtemp(prefix="directo-restream-")
    estado["tmpdir"] = tmpdir
    estado["ruta_anuncios"] = os.path.join(tmpdir, "anuncios.txt")
    estado["ruta_chat"] = os.path.join(tmpdir, "chat.txt")
    open(estado["ruta_anuncios"], "w").close()
    open(estado["ruta_chat"], "w").close()
    ruta_lanzador = os.path.join(tmpdir, "app_directo_restream.py")
    with open(ruta_lanzador, "w", encoding="utf-8") as archivo:
        archivo.write(_LANZADOR.format(repo=str(estado["raiz"])))
    entorno = dict(os.environ,
                   DIRECTO_REAL_ANUNCIOS=estado["ruta_anuncios"],
                   DIRECTO_REAL_CHAT=estado["ruta_chat"])
    from guyrapu.core import paths
    estado["ruta_log"] = paths.log_detallado()
    estado["marca_log"] = datetime.now()
    estado["app"] = subprocess.Popen([sys.executable, ruta_lanzador],
                                     cwd=str(estado["raiz"]), env=entorno)
    try:
        estado["principal"] = _ventana(APP_NAME, 60)
        time.sleep(4)
        anotar("ventana principal", True, f"pid {estado['app'].pid}")
        return True
    except RuntimeError as exc:
        anotar("ventana principal", False, str(exc))
        return False


def _elegir_destino(estado, anotar) -> bool:
    try:
        _control(estado["principal"], "Transmitir en directo",
                 "Button").invoke()
        dialogo = _dialogo_hijo(estado["principal"], "Transmitir a", 20)
        destino = _leer_valor(_control(dialogo, "Transmitir a", "ComboBox"))
        anotar("diálogo de destino", True, f"destino «{destino}»")
        if NOMBRE_PERFIL not in destino:
            anotar("perfil de Restream", False, f"la lista dice «{destino}»")
            return False
        _control(dialogo, "Continuar", "Button").invoke()
        return True
    except RuntimeError as exc:
        anotar("diálogo de destino", False, str(exc))
        return False


def _armar_y_transmitir(estado, anotar) -> bool:
    try:
        directo = _dialogo_hijo(estado["principal"],
                                "Directo con Restream", 180)
        titulo = _leer_valor(_control(directo, "Título del directo", "Edit"))
        privacidad = _leer_valor(_control(directo, "Privacidad", "ComboBox"))
        anotar("diálogo del directo", True,
               f"título «{titulo}», privacidad «{privacidad}»")
        from guyrapu.core.idioma import _
        from guyrapu.youtube.emision import ETIQUETAS_PRIVACIDAD
        aceptados = {PRIVACIDAD_ESPERADA,
                     _(ETIQUETAS_PRIVACIDAD[PRIVACIDAD_ESPERADA])}
        if not any(a.casefold() in (privacidad or "").casefold() for a in aceptados):
            anotar("privacidad no listado", False, f"dice «{privacidad}»")
            return False
        anotar("privacidad no listado", True, "«No listado»")
        estado["marca_salida"] = len(_leer_anuncios(estado["ruta_anuncios"]))
        _control(directo, "Transmitir", "Button").invoke()
        estado["pulso_transmitir"] = True
        return True
    except RuntimeError as exc:
        anotar("diálogo del directo", False, str(exc))
        return False


def _candidatos(canal) -> set[str]:
    valores = {str(canal.id)}
    if getattr(canal, "identificador", ""):
        valores.add(canal.identificador)
    return valores


def _escuchar(segundos: int):
    ruta = Path(__file__).resolve().parent.parent / "herramientas"         / "sin_directo.py"
    especificacion = importlib.util.spec_from_file_location(
        "sin_directo_qa", ruta)
    modulo = importlib.util.module_from_spec(especificacion)
    especificacion.loader.exec_module(modulo)
    return modulo.escuchar(segundos)


def comprobar_restream(estado, anotar) -> bool:
    tiktok = _candidatos(estado["canal_tiktok"])
    youtube: set[str] = set()
    otros: set[str] = set()
    for canal in estado["canales_antes"]:
        if canal.id == estado["canal_tiktok"].id:
            continue
        if perfiles.es_manual_youtube(canal):
            continue
        if perfiles.es_youtube_conectado(canal):
            youtube |= _candidatos(canal)
        else:
            otros |= _candidatos(canal)
    try:
        entrada, en_vivo = _escuchar(SEGUNDOS_WS)
    except Exception as exc:
        anotar("destinos en vivo de Restream", False, f"no se pudo escuchar: {exc}")
        return False
    bien, detalle = comparar_destinos_en_vivo(en_vivo, tiktok, youtube, otros)
    anotar("destinos en vivo de Restream", bien, f"{detalle}; entrada {entrada or 'sin dato'}")
    return bien


def _esperar_al_aire(estado, anotar, args) -> bool:
    resultado = esperar_anuncio(estado, (OK_AL_AIRE,) + ERRORES_AL_AIRE,
                               args.timeout_salida, estado["marca_salida"])
    if resultado is None or OK_AL_AIRE not in resultado.lower():
        anotar("salir al aire", False,
               f"sin «Directo iniciado en YouTube» en {args.timeout_salida} s"
               if resultado is None else f"la app anunció «{resultado}»")
        return False
    anotar("salir al aire", True, resultado)
    estado["salio_al_aire"] = True
    estado["id_video"] = extraer_id_video(
        _leer_anuncios(estado["ruta_anuncios"])[estado["marca_salida"]:])
    return True


def _resolver_video(estado, anotar) -> bool:
    try:
        cliente, creds = _cliente_youtube()
    except Exception as exc:
        anotar("YouTube del perfil", False, f"sin cliente API: {exc}")
        return False
    estado["cliente"] = cliente
    estado["creds"] = creds
    id_video = estado.get("id_video") or ""
    if not id_video:
        try:
            id_video, _, _ = _buscar_video_por_titulo(cliente,
                                                      estado["titulo"])
            _guardar_token_si_renovo(cliente, creds)
        except Exception as exc:
            anotar("vídeo de YouTube", False,
                   f"no se pudo buscar por título: {exc}")
            return False
    if not id_video:
        anotar("vídeo de YouTube", False,
               "ni los anuncios ni la API dejaron el id")
        return False
    estado["id_video"] = id_video
    estado["enlace_manual"] = "https://www.youtube.com/watch?v=" + id_video
    anotar("vídeo de YouTube", True, f"id {id_video}")
    return True


def _finalizar_directo(estado, anotar, args) -> bool:
    try:
        marca = len(_leer_anuncios(estado["ruta_anuncios"]))
        _control(estado["principal"], "Finalizar directo", "Button").invoke()
        confirmacion = _dialogo_hijo(estado["principal"],
                                     "Finalizar directo", 20)
        _control(confirmacion, "Finalizar directo", "Button").invoke()
    except RuntimeError as exc:
        anotar("finalizar directo", False, str(exc))
        return False
    resultado = esperar_anuncio(estado, OK_FIN, args.timeout_fin, marca)
    if resultado is None:
        anotar("finalizar directo", False,
               f"sin «Transmisión detenida» en {args.timeout_fin} s")
        return False
    anotar("finalizar directo", True, resultado)
    estado_yt = _esperar_estado(estado["cliente"], estado["id_video"])
    if estado_yt != "complete":
        anotar("YouTube terminó el directo", False,
               f"estado «{estado_yt or 'desconocido'}» tras 30 s")
        return False
    anotar("YouTube terminó el directo", True, "estado «complete»")
    estado["finalizado"] = True
    return True


def _transmitir(args, anotar, cuenta_mod, estado) -> int:
    if not _lanzar_app(estado, anotar):
        return 1
    if not _elegir_destino(estado, anotar):
        return 1
    if not _armar_y_transmitir(estado, anotar):
        return 1
    if not _esperar_al_aire(estado, anotar, args):
        return 1
    if not _resolver_video(estado, anotar):
        return 1
    if not comprobar_restream(estado, anotar):
        return 1
    if not comprobar_chats(estado, anotar, args.timeout_chat):
        return 1
    time.sleep(max(0, args.duracion))
    anotar("directo al aire", True, f"{args.duracion} s")
    if not _finalizar_directo(estado, anotar, args):
        return 1
    return 0


def _correr(args, *, paso_cero=None, preparar=None, cuenta_mod=None):
    pasos: list[tuple[str, bool, str]] = []

    def anotar(nombre: str, bien: bool, detalle: str = "") -> None:
        pasos.append((nombre, bien, detalle))

    bien_paso, detalle_paso = (paso_cero or _paso_cero)()
    anotar("sin directo en Restream", bien_paso,
           detalle_paso or ("comprobado" if bien_paso else "no se comprobó"))
    if not bien_paso:
        imprimir(pasos)
        return (pasos, 2)
    from guyrapu.youtube import credenciales
    if not credenciales.hay_sesion():
        anotar("sesión de Google", False, "sin token")
        imprimir(pasos)
        return (pasos, 2)
    anotar("sesión de Google", True, "hay token")
    if cuenta_mod is None:
        from guyrapu.restream import cuenta as cuenta_mod
    estado: dict = {}
    codigo = 1
    try:
        preparado = (preparar or _preparar)(anotar, cuenta_mod)
        if preparado is not None:
            estado = preparado
            codigo = _transmitir(args, anotar, cuenta_mod, estado)
    except Exception as exc:
        anotar("prueba", False, f"{type(exc).__name__}: {exc}")
        codigo = 1
    finally:
        limpiar(estado, anotar, cuenta_mod)
        titulos_restream.paso_devolver(estado, anotar, cuenta_mod)
    imprimir(pasos)
    if any(not bien for _, bien, _ in pasos):
        return (pasos, 1)
    return (pasos, codigo)


if __name__ == "__main__":
    sys.exit(_correr(_ayuda().parse_args())[1])
