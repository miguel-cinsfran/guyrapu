# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Cómo se conectan los chats de un directo por Restream.

El chat principal es el de YouTube y se conecta en el hilo de la interfaz.
Con «YouTube y TikTok», después de conectarlo se espera a que TikTok muestre
el directo y se conecta su chat como adicional. La espera corre en su propio
hilo y la corta el fin de la supervisión.
"""

from __future__ import annotations

import threading

from guyrapu.capture import tiktok_vivo
from guyrapu.core import diagnostico
from guyrapu.core.idioma import _

logger = diagnostico.obtener_logger(__name__)

# El supervisor espera a TikTok hasta este límite; el chat adicional usa lo
# mismo para no alargar la espera.
CADA_TIKTOK = 5.0
LIMITE_TIKTOK = 120.0

_PARADA = threading.Event()


def reiniciar_espera() -> None:
    _PARADA.clear()


def parar_espera() -> None:
    _PARADA.set()


def _en_interfaz(frame, funcion, *args):
    if not getattr(frame, "_alive", True):
        return
    from guyrapu.ui import gui as _gui
    _gui.wx.CallAfter(funcion, *args)


def conectar_chat(frame, youtube=False, guardados=None, tiktok="",
                  pedido=False, al_anunciar=None,
                  esperar_en_vivo=tiktok_vivo.esperar_en_vivo,
                  crear_hilo=diagnostico.crear_hilo):
    reiniciar_espera()

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
            try:
                frame.txt_url.SetValue(url)
            except Exception as error:
                logger.debug("no se pudo mostrar la dirección: %s", error)
            frame.sesion.conexion_propia = True
            frame._on_conectar(None)
            if pedido:
                _tras_conectar(frame, tiktok, al_anunciar, esperar_en_vivo,
                               crear_hilo)
        _en_interfaz(frame, _conectar)
    return al_conectar_chat


def _tras_conectar(frame, tiktok, al_anunciar, esperar_en_vivo, crear_hilo):
    if not tiktok:
        _avisar(al_anunciar, _("No se encontró el usuario de TikTok del "
                               "perfil: conecta el chat de TikTok a mano."),
                "error")
        return
    _avisar(al_anunciar, _("Esperando a que TikTok muestre el directo para "
                           "leer su chat."))
    crear_hilo(
        lambda: _esperar_tiktok(frame, tiktok, al_anunciar, esperar_en_vivo),
        "EsperarChatTikTok").start()


def _esperar_tiktok(frame, usuario, al_anunciar, esperar_en_vivo):
    resultado = esperar_en_vivo(usuario, _PARADA, cada=CADA_TIKTOK,
                                limite=LIMITE_TIKTOK)
    if _PARADA.is_set():
        return
    if not resultado.en_vivo:
        frase, sonido = tiktok_vivo.aviso_espera(resultado, usuario)
        _en_interfaz(frame, _avisar, al_anunciar, frase, sonido, True)
        return
    _en_interfaz(frame, _conectar_adicional, frame, usuario)


def _conectar_adicional(frame, usuario):
    if not getattr(frame, "_alive", True):
        return
    if _PARADA.is_set():
        return
    if not (frame._conectado and not frame.sesion.es_tiktok):
        return
    frame.conectar_chat_adicional(tiktok_vivo.url_directo(usuario))


def _avisar(al_anunciar, frase, sonido=None, importante=False):
    if al_anunciar is not None:
        al_anunciar(frase, sonido, importante)
