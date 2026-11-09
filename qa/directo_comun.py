# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Decisiones y piezas compartidas de la prueba de punta a punta por Restream."""

from __future__ import annotations

import contextlib
import importlib.util
import os
import shutil
import time
from pathlib import Path

from guyrapu.restream import perfiles

from directo_real import (
    COMENTARIOS_PRUEBA, FUENTE_APLICACION, FUENTE_CAMARA, _borrar_video,
    _buscar_video_por_titulo, _cerrar_obs, _cerrar_ventanas_prueba,
    _cliente_youtube, _comentario_faltante, _detalle_lista_chat,
    _detener_y_finalizar,
    _guardar_token_si_renovo, _leer_anuncios, _live_chat_id,
    _obs_en_ejecucion, _quitar_fuente, contestar_salir_si_aparece,
    es_borrable,
)

NOMBRE_PERFIL = "Prueba de Guyrapu"
PRIVACIDAD_ESPERADA = "unlisted"
CHAT_YOUTUBE = "Conectado al directo. Leyendo el chat."
CHAT_TIKTOK = "TikTok: Conectado al directo. Leyendo el chat."
SEGUNDOS_WS = 20


def _claves(valores) -> set[str]:
    return {str(valor) for valor in valores or () if str(valor)}


def destino_tiktok(canales):
    tiktoks = [canal for canal in canales or ()
               if getattr(canal, "plataforma", "") == "TikTok"]
    if not tiktoks:
        raise ValueError(
            "La cuenta de Restream no tiene ningún destino de TikTok.")
    return tiktoks[0]


def armar_perfil(canal_tiktok, titulo,
                 privacidad: str = PRIVACIDAD_ESPERADA) -> perfiles.Perfil:
    return perfiles.Perfil(
        nombre=NOMBRE_PERFIL,
        canales=(int(canal_tiktok.id),),
        orientacion="vertical",
        youtube=True,
        chat="ambos",
        directo={"titulo": titulo, "privacidad": privacidad},
    )


def comparar_destinos_en_vivo(en_vivo, tiktok, youtube_conectado,
                              otros) -> tuple[bool, str]:
    """Si en vivo están justo TikTok y el YouTube manual, y nada más.

    Se acepta el id o el identificador del canal, así que quien llama pasa las
    dos formas. El YouTube manual es el único destino nuevo de la cuenta.
    """
    vivos = _claves(en_vivo)
    tiktok = _claves(tiktok)
    youtube = _claves(youtube_conectado)
    otros = _claves(otros)
    listado = ", ".join(sorted(vivos)) or "ninguno"
    if not vivos:
        return (False, "Restream no nombró ningún destino en vivo")
    if youtube & vivos:
        return (False, "el YouTube conectado de la cuenta está en vivo")
    if otros & vivos:
        return (False, "hay otros destinos de la cuenta en vivo")
    if not (vivos & tiktok):
        return (False, f"TikTok no está en vivo; en vivo: {listado}")
    if len(vivos) < 2:
        return (False, f"falta el YouTube manual; en vivo: {listado}")
    if len(vivos) > 2:
        return (False, f"hay destinos de más; en vivo: {listado}")
    if not (vivos - tiktok):
        return (False, f"no se ve el YouTube manual; en vivo: {listado}")
    return (True, f"en vivo: {listado}")


def destinos_a_restaurar(antes, actuales) -> list[tuple[int, bool]]:
    cambios = []
    for canal in actuales or ():
        identificador = getattr(canal, "id", None)
        if identificador not in (antes or {}):
            continue
        previo = bool(antes[identificador])
        if bool(getattr(canal, "activo", True)) != previo:
            cambios.append((identificador, previo))
    return cambios


def manuales_nuevos(antes, actuales) -> list[int]:
    previos = {getattr(canal, "id", None) for canal in antes or ()}
    return [canal.id for canal in actuales or ()
            if getattr(canal, "id", None) not in previos
            and perfiles.es_manual_youtube(canal)]


def chats_conectados(anuncios) -> tuple[bool, str]:
    lineas = (anuncios or "").splitlines()
    youtube = any(CHAT_YOUTUBE in linea and CHAT_TIKTOK not in linea
                  for linea in lineas)
    tiktok = any(CHAT_TIKTOK in linea for linea in lineas)
    if youtube and tiktok:
        return (True, "YouTube y TikTok conectados")
    faltan = [nombre for nombre, presente in
              (("YouTube", youtube), ("TikTok", tiktok)) if not presente]
    return (False, "falta conectar: " + ", ".join(faltan))


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



def comprobar_chats(estado, anotar, timeout) -> bool:
    marca = len(_leer_anuncios(estado["ruta_anuncios"]))
    fin = time.time() + timeout
    while True:
        bien, detalle = chats_conectados(
            _leer_anuncios(estado["ruta_anuncios"])[marca:])
        if bien or time.time() >= fin:
            break
        time.sleep(1)
    anotar("chats conectados", bien, detalle)
    if not bien:
        return False
    try:
        id_chat = _live_chat_id(estado["cliente"], estado["id_video"])
    except Exception as exc:
        anotar("comentarios enviados", False, f"no se pudo leer el liveChatId: {exc}")
        return False
    if not id_chat:
        anotar("comentarios enviados", False, "la API no devolvió liveChatId")
        return False
    try:
        for comentario in COMENTARIOS_PRUEBA:
            estado["cliente"].enviar_mensaje_live(id_chat, comentario)
        _guardar_token_si_renovo(estado["cliente"], estado["creds"])
    except Exception as exc:
        anotar("comentarios enviados", False, str(exc))
        return False
    anotar("comentarios enviados", True, f"{len(COMENTARIOS_PRUEBA)} al chat de YouTube")
    faltante, leidos = _comentario_faltante(
        estado["ruta_chat"], COMENTARIOS_PRUEBA, 30)
    if faltante is not None:
        anotar("comentarios en la app", False,
               f"«{faltante}» no apareció ({_detalle_lista_chat(leidos)})")
        return False
    anotar("comentarios en la app", True, "los tres están en la lista del chat")
    return True


def buscar_por_titulo(estado) -> None:
    if estado.get("id_video") or estado.get("finalizado") or not (
            estado.get("salio_al_aire") or estado.get("pulso_transmitir")):
        return
    try:
        cliente, creds = _cliente_youtube()
        hallado, titulo, privacidad = _buscar_video_por_titulo(
            cliente, estado.get("titulo") or "")
        _guardar_token_si_renovo(cliente, creds)
    except Exception:
        return
    if hallado and es_borrable(titulo, privacidad):
        estado["id_video"] = hallado
        estado.setdefault("enlace_manual",
                          "https://www.youtube.com/watch?v=" + hallado)


def paso_detener_obs(estado, anotar) -> None:
    gestor = estado.get("gestor_obs")
    if gestor is None:
        anotar("detener OBS", True, "OBS no se conectó")
        return
    try:
        actual = gestor.estado_transmision() or {}
        if actual.get("outputActive"):
            gestor.detener_transmision()
            anotar("detener OBS", True, "salida detenida")
        else:
            anotar("detener OBS", True, "ya estaba detenida")
    except Exception as exc:
        anotar("detener OBS", False, str(exc))


def _aplicar(accion, cambios, anotar, nombre, exito) -> None:
    errores = []
    for cambio in cambios:
        try:
            accion(*cambio)
        except Exception as exc:
            errores.append(f"{cambio[0]}: {exc}")
    anotar(nombre, not errores, "; ".join(errores) or exito)


def _canales(anotar, cuenta_mod, nombre):
    try:
        return cuenta_mod.canales()
    except Exception as exc:
        anotar(nombre, False, f"no se pudieron leer: {exc}")
        return None


def paso_restaurar_destinos(estado, anotar, cuenta_mod) -> None:
    antes = estado.get("antes") or {}
    if not antes:
        anotar("destinos de Restream", True, "no se llegó a leer la cuenta")
        return
    actuales = _canales(anotar, cuenta_mod, "destinos de Restream")
    if actuales is None:
        return
    cambios = destinos_a_restaurar(antes, actuales)
    if estado.get("finalizado"):
        anotar("la app devolvió los destinos", not cambios,
               f"quedaron cambiados: {', '.join(str(c[0]) for c in cambios)}"
               if cambios else "sin cambios")
    if not cambios:
        anotar("destinos de Restream", True, "no había nada que restaurar")
        return
    _aplicar(cuenta_mod.activar_canal, cambios, anotar, "destinos de Restream",
             "se devolvieron a su estado")


def paso_borrar_manual(estado, anotar, cuenta_mod) -> None:
    antes = estado.get("canales_antes")
    if antes is None:
        anotar("destino manual de YouTube", True, "no se llegó a leer la cuenta")
        return
    actuales = _canales(anotar, cuenta_mod, "destino manual de YouTube")
    if actuales is None:
        return
    sobrantes = manuales_nuevos(antes, actuales)
    if estado.get("finalizado"):
        anotar("la app borró el destino manual", not sobrantes,
               f"quedó {', '.join(map(str, sobrantes))}" if sobrantes
               else "sin sobrantes")
    if not sobrantes:
        anotar("destino manual de YouTube", True, "no había nada que borrar")
        return
    _aplicar(cuenta_mod.eliminar_canal, [(i,) for i in sobrantes], anotar,
             "destino manual de YouTube", f"borrado {', '.join(map(str, sobrantes))}")


def paso_borrar_video(estado, anotar) -> None:
    buscar_por_titulo(estado)
    id_video = estado.get("id_video") or ""
    if not id_video:
        if estado.get("enlace_manual"):
            anotar("vídeo de YouTube", False, f"sin borrar: {estado['enlace_manual']}")
        else:
            anotar("vídeo de YouTube", True, "no se creó ninguno")
        return
    try:
        cliente, creds = _cliente_youtube()
    except Exception as exc:
        anotar("vídeo de YouTube", False, f"sin cliente API: {exc}")
        return
    if not estado.get("finalizado"):
        bien, detalle = _detener_y_finalizar(
            estado.get("gestor_obs"), cliente, creds, id_video)
        if bien:
            estado["finalizado"] = True
        anotar("finalizar el directo por API", bien, detalle)
    a_mano = estado.get("enlace_manual") or id_video
    try:
        borrado, motivo = _borrar_video(cliente, creds, id_video)
    except Exception as exc:
        anotar("borrar el vídeo", False, f"{exc}; a mano: {a_mano}")
        return
    if not borrado:
        anotar("borrar el vídeo", False, f"{motivo}; a mano: {a_mano}")
        return
    anotar("borrar el vídeo", True, f"id {id_video}")
    estado["borrado_id"] = id_video
    estado["id_video"] = ""
    estado["enlace_manual"] = ""


def paso_quitar_escena(estado, anotar) -> None:
    escena = estado.get("escena_prueba")
    gestor = estado.get("gestor_obs")
    if not escena or gestor is None:
        anotar("quitar la escena de prueba", True, "no se llegó a armar")
        return
    _quitar_fuente(gestor, escena, FUENTE_CAMARA, borrar_entrada=True)
    _quitar_fuente(gestor, escena, FUENTE_APLICACION, borrar_entrada=True)
    if estado.get("creo_panel"):
        from guyrapu.obs.obs_panel import NOMBRE_FUENTE
        _quitar_fuente(gestor, escena, NOMBRE_FUENTE)
    anotar("quitar la escena de prueba", True, "capturas y panel fuera de la escena")


def paso_cerrar_app(estado, anotar) -> None:
    try:
        if estado.get("principal") is not None:
            with contextlib.suppress(Exception):
                estado["principal"].close()
                contestar_salir_si_aparece(segundos=8.0)
                time.sleep(8)
        if estado.get("app") is not None and estado["app"].poll() is None:
            with contextlib.suppress(Exception):
                estado["app"].kill()
        if estado.get("gestor_obs") is not None:
            with contextlib.suppress(Exception):
                estado["gestor_obs"].cerrar()
        if estado.get("estaba_obs") is False and _obs_en_ejecucion():
            _cerrar_obs()
        anotar("cerrar la app y OBS", True, "app cerrada")
    except Exception as exc:
        anotar("cerrar la app y OBS", False, str(exc))


def restaurar_archivos(estado, anotar) -> None:
    respaldos = estado.get("respaldos") or {}
    problemas = []
    for clave, ruta in (estado.get("rutas") or {}).items():
        respaldo = respaldos.get(clave)
        try:
            if respaldo:
                shutil.copy2(respaldo, ruta)
            elif clave == "perfiles" and estado.get("perfil_guardado"):
                Path(ruta).unlink(missing_ok=True)
        except OSError as exc:
            problemas.append(f"{clave}: {exc}")
        if respaldo:
            with contextlib.suppress(OSError):
                os.remove(respaldo)
    anotar("restaurar archivos", not problemas,
           "; ".join(problemas) or "config.ini, sounds.ini y "
           "perfiles_restream.json como estaban")


def limpiar(estado, anotar, cuenta_mod) -> None:
    pasos = (
        lambda: paso_detener_obs(estado, anotar),
        lambda: paso_restaurar_destinos(estado, anotar, cuenta_mod),
        lambda: paso_borrar_manual(estado, anotar, cuenta_mod),
        lambda: paso_borrar_video(estado, anotar),
        lambda: paso_quitar_escena(estado, anotar),
        lambda: _cerrar_ventanas_prueba(estado.get("ventanas_prueba") or []),
        lambda: paso_cerrar_app(estado, anotar),
        lambda: restaurar_archivos(estado, anotar),
    )
    for paso in pasos:
        try:
            paso()
        except Exception as exc:
            anotar("limpieza", False, f"falló un paso: {exc}")
    if estado.get("tmpdir"):
        shutil.rmtree(estado["tmpdir"], ignore_errors=True)


def imprimir(pasos) -> None:
    for nombre, bien, detalle in pasos:
        linea = f"{nombre}: {'bien' if bien else 'falló'}"
        if detalle:
            linea += f" ({detalle})"
        print(linea)
