# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Cómo se conectan los chats de un directo por Restream.

El chat principal es el de YouTube y se conecta en el hilo de la interfaz.
Con «YouTube y TikTok», la búsqueda del directo de TikTok arranca junto con
la supervisión y, apenas el chat principal está conectado, se conecta su
chat como adicional. La búsqueda y la vigilancia del adicional corren en su
propio hilo hasta el fin de la supervisión.
"""

from __future__ import annotations

import threading
import time

from guyrapu.capture import chat_adicional, tiktok_vivo
from guyrapu.core import diagnostico
from guyrapu.core.idioma import _
from guyrapu.voice import sound_player as _snd

logger = diagnostico.obtener_logger(__name__)

# La primera búsqueda del directo de TikTok consulta cada CADA_TIKTOK hasta
# LIMITE_TIKTOK. Después del primer aviso se consulta cada CADA_TIKTOK_LENTO
# mientras dure la transmisión.
CADA_TIKTOK = 5.0
LIMITE_TIKTOK = 120.0
CADA_TIKTOK_LENTO = 30.0

# Mientras el chat principal termina de conectarse, el adicional lo mira cada
# CADA_CONEXION, sin plazo.
CADA_CONEXION = 1.0

# Si el adicional se apaga antes de DURACION_ESTABLE, cuenta como desconexión
# rápida. A la tercera desconexión rápida seguida se deja de reconectar.
DURACION_ESTABLE = 60.0
DESCONEXIONES_SEGUIDAS = 3

_PARADA = threading.Event()
_reloj = time.monotonic


def reiniciar_espera() -> None:
    _PARADA.clear()


def parar_espera() -> None:
    _PARADA.set()


def _en_interfaz(frame, funcion, *args):
    if not getattr(frame, "_alive", True):
        return
    from guyrapu.ui import gui as _gui
    _gui.wx.CallAfter(funcion, *args)


def _dormir(segundos) -> None:
    _PARADA.wait(segundos)


def _sigue(frame) -> bool:
    return not _PARADA.is_set() and getattr(frame, "_alive", True)


def _lanzar_busqueda(frame, usuario, al_anunciar, esperar_en_vivo, crear_hilo):
    crear_hilo(
        lambda: _esperar_tiktok(frame, usuario, al_anunciar, esperar_en_vivo),
        "EsperarChatTikTok").start()


def _mostrar_url(frame, url):
    try:
        frame.txt_url.SetValue(url)
    except Exception as error:
        logger.debug("no se pudo mostrar la dirección: %s", error)


def conectar_chat(frame, youtube=False, guardados=None, tiktok="",
                  pedido=False, al_anunciar=None,
                  esperar_en_vivo=tiktok_vivo.esperar_en_vivo,
                  crear_hilo=diagnostico.crear_hilo):
    reiniciar_espera()
    if pedido and tiktok:
        _lanzar_busqueda(frame, tiktok, al_anunciar, esperar_en_vivo,
                         crear_hilo)

    def al_conectar_chat(url):
        from guyrapu.ui import gui as _gui

        def _conectar():
            if not getattr(frame, "_alive", True):
                return
            if youtube:
                from guyrapu.ui import inicio_youtube
                if inicio_youtube.sin_chat(frame, guardados or {}, url):
                    return
            if frame._conectado or frame._conectando:
                _gui.anunciar(
                    _("El chat ya estaba conectado y no se cambió."))
                return
            _mostrar_url(frame, url)
            frame.sesion.conexion_propia = True
            frame._on_conectar(None)
            if pedido and not tiktok:
                _aviso_sin_usuario(al_anunciar)
        _en_interfaz(frame, _conectar)
    return al_conectar_chat


def _aviso_sin_usuario(al_anunciar):
    _avisar(al_anunciar, _("El chat de TikTok no se va a leer porque el "
                           "perfil de Restream no tiene usuario de TikTok."),
            "error")


def _esperar_tiktok(frame, usuario, al_anunciar, esperar_en_vivo):
    primera_busqueda = True
    primera_conexion = True
    desconexiones_seguidas = 0
    avisado = False
    while _sigue(frame):
        resultado = _buscar_tiktok(usuario, esperar_en_vivo, primera_busqueda)
        primera_busqueda = False
        if _PARADA.is_set():
            return
        if not resultado.en_vivo:
            if not avisado:
                avisado = True
                frase, sonido = tiktok_vivo.aviso_espera(resultado, usuario)
                _en_interfaz(frame, _avisar, al_anunciar, frase, sonido)
            continue
        if not _conectar_adicional(frame, usuario, al_anunciar,
                                   not primera_conexion):
            return
        primera_conexion = False
        inicio = _reloj()
        if not _vigilar_adicional(frame):
            return
        if not _sigue(frame):
            return
        desconexiones_seguidas = _contar_desconexion(inicio, desconexiones_seguidas)
        if desconexiones_seguidas >= DESCONEXIONES_SEGUIDAS:
            _aviso_desconexiones(frame, al_anunciar)
            return


def _buscar_tiktok(usuario, esperar_en_vivo, primera):
    if primera:
        return esperar_en_vivo(usuario, _PARADA, cada=CADA_TIKTOK,
                               limite=LIMITE_TIKTOK)
    return esperar_en_vivo(usuario, _PARADA, cada=CADA_TIKTOK_LENTO,
                           limite=CADA_TIKTOK_LENTO)


def _conectar_adicional(frame, usuario, al_anunciar, reconexion):
    if not _esperar_principal(frame, usuario, al_anunciar):
        return False
    if not _sigue(frame):
        return False
    _en_interfaz(frame, _pedir_adicional, frame, usuario, reconexion)
    return True


def _pedir_adicional(frame, usuario, reconexion):
    if reconexion:
        _sonar("chat_reconectado")
    frame.conectar_chat_adicional(tiktok_vivo.url_directo(usuario))


def _sonar(sonido):
    _snd.reproducir(sonido)


def _contar_desconexion(inicio, desconexiones_seguidas):
    if _reloj() - inicio >= DURACION_ESTABLE:
        return 0
    return desconexiones_seguidas + 1


def _aviso_desconexiones(frame, al_anunciar):
    _en_interfaz(frame, _avisar, al_anunciar,
                 _("El chat de TikTok se dejó de reconectar porque se "
                   "desconectaba enseguida."),
                 "transmision_problema")


def _esperar_principal(frame, usuario, al_anunciar):
    while _sigue(frame):
        estado = _leer_estado(frame)
        if not _sigue(frame):
            return False
        if estado is not None:
            conectado, _conectando, es_tiktok = estado
            if es_tiktok:
                _sin_chat(frame, usuario, al_anunciar,
                          "la sesión es de TikTok")
                return False
            if conectado:
                return True
        _dormir(CADA_CONEXION)
    return False


def _vigilar_adicional(frame):
    while _sigue(frame):
        _dormir(CADA_TIKTOK)
        if not _sigue(frame):
            return False
        if not chat_adicional.activo():
            return True
    return False


def _leer_estado(frame):
    datos = {}
    listo = threading.Event()

    def _leer():
        datos["conectado"] = bool(getattr(frame, "_conectado", False))
        datos["conectando"] = bool(getattr(frame, "_conectando", False))
        datos["es_tiktok"] = bool(getattr(frame.sesion, "es_tiktok", False))
        listo.set()

    _en_interfaz(frame, _leer)
    if not listo.wait(1.0):
        return None
    return datos["conectado"], datos["conectando"], datos["es_tiktok"]


def _sin_chat(frame, usuario, al_anunciar, motivo):
    logger.warning("No se conectó el chat de TikTok: %s.", motivo)
    resultado = tiktok_vivo.ResultadoEspera(False, False)
    frase, sonido = tiktok_vivo.aviso_espera(resultado, usuario)
    _en_interfaz(frame, _avisar, al_anunciar, frase, sonido)


def _avisar(al_anunciar, frase, sonido=None, importante=False):
    if al_anunciar is not None:
        al_anunciar(frase, sonido, importante)
