# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Cierre de la ventana principal.

Única razón para cambiar: cómo se cierra la app. Las funciones reciben el
marco, como `gui_construccion.construir(frame)`.
"""

from __future__ import annotations

import time

import wx

from guyrapu.core import apagado
from guyrapu.core import diagnostico
from guyrapu.core import paths
from guyrapu.core.idioma import _
from guyrapu.downloads.descargas import gestor
from guyrapu.obs import overlay_servidor
from guyrapu.ui import confirmar
from guyrapu.ui.accesibilidad import anunciar
from guyrapu.ui.confirmar_salida import (
    descargas_sin_terminar, mensaje_confirmar_salida, mensaje_con_descargas)
from guyrapu.voice import sound_player as _snd
from guyrapu.youtube import finalizar_aparte, fin_pendiente

logger = diagnostico.obtener_logger(__name__)


def _puede_vetar(event) -> bool:
    return callable(getattr(event, "CanVeto", None)) and event.CanVeto()


def on_close(frame, event):
    if frame._apagando:
        return
    if not getattr(frame, "_cerrar_sin_preguntar", False):
        if not preguntar_salida(frame, event):
            return
    if _puede_vetar(event) and fin_pendiente.leer(paths.fin_pendiente()):
        # Traductores: aviso al salir con un directo de YouTube sin finalizar.
        confirmar.avisar(
            frame,
            _("El directo de YouTube sigue abierto porque no hay conexión. "
              "Guyrapu lo finalizará solo cuando vuelva la conexión, aunque "
              "la aplicación esté cerrada."),
            _("Directo sin finalizar"), _("Aceptar"))
    apagar(frame)


def preguntar_salida(frame, event) -> bool:
    supervisor = getattr(frame, "_supervisor", None)
    mensaje = mensaje_confirmar_salida(
        (getattr(frame, "_config", None) or {}).get(
            "confirmar_salida", True),
        bool(getattr(frame, "_conectado", False)),
        bool(supervisor is not None and supervisor.activo),
        bool(getattr(frame, "_obs_transmitiendo", False)))
    try:
        mensaje = mensaje_con_descargas(
            mensaje, descargas_sin_terminar(gestor().lista()))
    except Exception as error:
        logger.debug("no se pudo leer las descargas al salir: %s", error)
    if mensaje is None or not _puede_vetar(event):
        return True
    # Traductores: título del cuadro para salir.
    if not confirmar.preguntar(
            frame, mensaje, _("Salir"), _("&Salir"),
            _("&Cancelar"), predeterminado_si=False,
            centrar=True):
        event.Veto()
        return False
    return True


def _abandonar_supervisor(frame):
    supervisor = getattr(frame, "_supervisor", None)
    if supervisor is not None and supervisor.activo:
        try:
            supervisor.abandonar()
        except Exception as error:
            logger.debug("no se pudo abandonar la supervisión: %s", error)
        frame._supervisor = None


def apagar(frame):
    frame._apagando = True
    frame._alive = False
    if fin_pendiente.leer(paths.fin_pendiente()):
        finalizar_aparte.lanzar()
    diagnostico.registrar_cierre_pedido(frame._diagnostico_parada)
    actualizar_vigilante_obs_cierre(frame)
    _abandonar_supervisor(frame)
    try:    frame._timer.Stop()
    except Exception as error: logger.debug("no se pudo detener el temporizador: %s", error)
    try:    frame._diagnostico_timer.Stop()
    except Exception as error: logger.debug("no se pudo detener el diagnóstico: %s", error)
    frame.chat_vivo.descartar()
    hilos_previos = diagnostico.hilos_vivos_de_la_aplicacion()
    if apagado.hilos_captura_vivos(hilos_previos):
        # Traductores: aviso mientras se cierra la app.
        anunciar(_("Cerrando"))
    try:    frame.Hide()
    except Exception as error: logger.debug("no se pudo ocultar la ventana: %s", error)
    if frame.on_desconectar_cb:
        try:    frame.on_desconectar_cb()
        except Exception as error: logger.debug("no se pudo desconectar: %s", error)
    frame._parada.set()
    overlay_servidor.apagar()
    try:
        frame._rep_panel.detener_todo()
    except Exception as error: logger.debug("no se pudo detener el panel: %s", error)
    try:
        frame._musica.cerrar()
    except Exception as error: logger.debug("no se pudo cerrar la música: %s", error)
    try:
        frame._recientes.cerrar()
    except Exception as error: logger.debug("no se pudo cerrar los recientes: %s", error)
    try:
        # Interrumpir lo que se esté leyendo (purga) antes de parar, para que
        # el cierre sea inmediato y no termine el mensaje en curso.
        frame._worker.detener_actual()
        frame._worker.detener()
    except Exception as error: logger.debug("no se pudo detener la voz: %s", error)
    try:    _snd.cerrar()
    except Exception as error: logger.debug("no se pudo cerrar los sonidos: %s", error)
    frame._cierre_inicio = time.monotonic()
    frame._cierre_tope = apagado.TOPE_ESPERA_CIERRE
    comprobar_cierre(frame)


def actualizar_vigilante_obs_cierre(frame):
    vigilante = getattr(frame, "_obs_vigilante", None)
    if vigilante is not None:
        vigilante.detener()
        frame._obs_vigilante = None


def comprobar_cierre(frame):
    nombres = diagnostico.hilos_vivos_de_la_aplicacion()
    transcurrido = time.monotonic() - frame._cierre_inicio
    if apagado.hay_que_seguir_esperando(nombres, transcurrido, frame._cierre_tope):
        wx.CallLater(200, comprobar_cierre, frame)
        return
    diagnostico.logger.log(apagado.nivel_registro_cierre(nombres),
        "%s", apagado.componer_resultado_cierre(nombres, frame._cierre_tope))
    if not nombres:
        diagnostico.registrar_cierre_fallos()
    frame.Destroy()
