# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Decisiones y piezas compartidas de la prueba de punta a punta por Restream."""

from __future__ import annotations

import contextlib
import os
import shutil
import time
from pathlib import Path

from guyrapu.restream import perfiles

from directo_real import (
    COMENTARIOS_PRUEBA, _borrar_video, _buscar_video_por_titulo,
    _cerrar_obs, _cliente_youtube, _comentario_faltante, _control,
    _detalle_lista_chat, _detener_y_finalizar, _dialogo_hijo, _gestor_obs,
    _guardar_token_si_renovo, _leer_anuncios, _live_chat_id,
    _obs_en_ejecucion, contestar_salir_si_aparece, es_borrable,
)

NOMBRE_PERFIL = "Prueba de Guyrapu"
PRIVACIDAD_ESPERADA = "unlisted"
CHAT_YOUTUBE = "Conectado al directo. Leyendo el chat."
CHAT_TIKTOK = "TikTok: Conectado al directo. Leyendo el chat."


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


def leer_log_anuncios(ruta, marca) -> str:
    try:
        datos = Path(ruta).read_bytes()[marca:]
    except OSError:
        return ""
    texto = datos.decode("utf-8", "replace")
    return "\n".join(linea for linea in texto.splitlines()
                     if "ANUNCIO " in linea)


def texto_anuncios(estado, desde=0) -> str:
    ruta_log = estado.get("ruta_log")
    return (_leer_anuncios(estado["ruta_anuncios"])[desde:] + "\n"
            + (leer_log_anuncios(ruta_log, estado.get("marca_log", 0))
               if ruta_log else ""))


def esperar_anuncio(estado, fragmentos, segundos, desde=0):
    fin = time.monotonic() + segundos
    while True:
        texto = texto_anuncios(estado, desde).lower()
        for fragmento in fragmentos:
            if fragmento.lower() in texto:
                return fragmento
        if time.monotonic() >= fin:
            return None
        time.sleep(1)


def comprobar_chats(estado, anotar, timeout) -> bool:
    marca = len(_leer_anuncios(estado["ruta_anuncios"]))
    fin = time.time() + timeout
    while True:
        bien, detalle = chats_conectados(texto_anuncios(estado, marca))
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
        try:
            gestor = _gestor_obs()
            estado["gestor_obs"] = gestor
        except Exception as exc:
            anotar("detener OBS", False, f"sin conexión a OBS: {exc}")
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
               "cambiados: " + (", ".join(str(c[0]) for c in cambios)
                                or "ninguno"))
    _aplicar(cuenta_mod.activar_canal, cambios, anotar, "destinos de Restream",
             "como estaban")


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
               "quedó " + (", ".join(map(str, sobrantes)) or "ninguno"))
    _aplicar(cuenta_mod.eliminar_canal, [(i,) for i in sobrantes], anotar,
             "destino manual de YouTube", "sin sobrantes")


def esperar_restauracion_app(estado, cuenta_mod, segundos=30, intervalo=2,
                             reloj=time.monotonic, dormir=time.sleep) -> bool:
    app = estado.get("app")
    if not estado.get("salio_al_aire") or app is None or app.poll() is not None:
        return True
    fin = reloj() + segundos
    while reloj() <= fin:
        try:
            actuales = cuenta_mod.canales()
        except Exception:
            actuales = None
        if actuales is not None and not destinos_a_restaurar(
                estado.get("antes") or {}, actuales) and not manuales_nuevos(
                estado.get("canales_antes") or [], actuales):
            return True
        dormir(intervalo)
    return False


def paso_finalizar_app(estado, anotar) -> None:
    if estado.get("salio_al_aire") or not estado.get("pulso_transmitir"):
        return
    principal = estado.get("principal")
    with contextlib.suppress(RuntimeError):
        if principal is not None:
            _control(principal, "Finalizar directo", "Button", 5).invoke()
            _control(_dialogo_hijo(principal, "Finalizar directo", 10),
                     "Finalizar directo", "Button", 5).invoke()


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
        lambda: paso_finalizar_app(estado, anotar),
        lambda: paso_detener_obs(estado, anotar),
        lambda: esperar_restauracion_app(estado, cuenta_mod),
        lambda: paso_restaurar_destinos(estado, anotar, cuenta_mod),
        lambda: paso_borrar_manual(estado, anotar, cuenta_mod),
        lambda: paso_borrar_video(estado, anotar),
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
