# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Las acciones de lo que sale en el vídeo.

Un solo camino por acción: el menú Interacción y los atajos globales llaman
acá. La capa del vídeo conserva el estado de la cola entre una acción y la
siguiente.
"""

from __future__ import annotations

from guyrapu.core.idioma import _
from guyrapu.interaction.estado_interaccion import texto as texto_estado
from guyrapu.ui import (
    comando_mensajes_automaticos, comandos_en_vivo, encuesta_en_vivo,
    preguntas_en_vivo)
from guyrapu.ui.accesibilidad import anunciar, anunciar_con_sonido


def _capa(frame):
    from guyrapu.ui import gui_envio_chat
    return gui_envio_chat.capa_de_video(frame)


def _marcar(frame, nombre, valor):
    item = getattr(frame, nombre, None)
    if item is not None:
        item.Check(bool(valor))


def alternar_pausa(frame):
    """Pausa o reanuda la cola y dice el estado nuevo."""
    capa = _capa(frame)
    pausado = not capa.estado()["pausado"]
    if pausado:
        capa.pausar()
    else:
        capa.reanudar()
    _marcar(frame, "mi_video_pausar", pausado)
    anunciar_con_sonido(
        _("Cola del vídeo en pausa") if pausado
        else _("Cola del vídeo reanudada"),
        "video_pausa" if pausado else "video_reanudar")


def saltar(frame):
    """Omite lo que se ve en el vídeo, o dice que no había nada."""
    if _capa(frame).saltar():
        anunciar_con_sonido(_("Mensaje del vídeo omitido"), "listo")
    else:
        anunciar_con_sonido(_("Nada en el vídeo"), "listo")


def vaciar(frame):
    """Vacía lo pendiente, o dice que no había nada."""
    if _capa(frame).vaciar():
        anunciar_con_sonido(_("Cola del vídeo vacía"), "listo")
    else:
        anunciar_con_sonido(_("Nada en el vídeo"), "listo")


def alternar_silencio(frame):
    """Silencia o activa el sonido de los medios y dice el estado nuevo."""
    capa = _capa(frame)
    silenciado = not capa.estado()["silenciado"]
    capa.silenciar(silenciado)
    _marcar(frame, "mi_video_silenciar", silenciado)
    anunciar_con_sonido(
        _("Medios silenciados") if silenciado else _("Medios activados"),
        "video_silenciar" if silenciado else "video_audio")


def alternar_panico(frame):
    """Activa o desactiva el modo pánico y dice el estado nuevo."""
    capa = _capa(frame)
    activo = not capa.estado()["panico"]
    capa.panico(activo)
    _marcar(frame, "mi_video_panico", activo)
    anunciar_con_sonido(
        _("Modo pánico activado") if activo
        else _("Modo pánico desactivado"),
        "video_panico" if activo else "video_panico_fin")


def alternar_comandos(frame):
    """Pausa o reanuda todos los comandos y dice el estado nuevo."""
    pausados = comandos_en_vivo._en_vivo(frame).alternar_pausa()
    _marcar(frame, "mi_comandos_pausar", pausados)
    anunciar_con_sonido(
        _("Comandos en pausa") if pausados else _("Comandos reanudados"),
        "comandos_pausa" if pausados else "comandos_reanudar")


def alternar_mensajes(frame):
    """Prende o apaga los mensajes automáticos con su comando."""
    comando_mensajes_automaticos.alternar(frame)


def cerrar_encuesta(frame):
    """Cierra la encuesta abierta, o dice que no hay ninguna."""
    if not encuesta_en_vivo.cerrar(frame):
        anunciar_con_sonido(_("No hay ninguna encuesta abierta"), "listo")


def pregunta_siguiente(frame):
    """Lee la pregunta más vieja pendiente y cuántas quedan."""
    pregunta = preguntas_en_vivo.siguiente(frame)
    if pregunta is None:
        anunciar(_("No hay preguntas."))
        return
    quedan = len(preguntas_en_vivo.pendientes(frame)) - 1
    anunciar(_("{autor} pregunta: {texto}. Quedan {n}.").format(
        autor=pregunta.autor, texto=pregunta.texto, n=quedan))


def estado_interaccion(frame):
    """Anuncia cómo va la interacción del directo."""
    snap = frame._snapshot_sesion()
    anunciar(texto_estado(
        snap.encuesta, snap.batalla, snap.meta, snap.video,
        len(preguntas_en_vivo.pendientes(frame))))
