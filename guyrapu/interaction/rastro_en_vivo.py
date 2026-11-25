# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Lo que el directo decide y lo que hacen los comandos y el vídeo, en el registro.

Puro, sin wx ni ventanas. Cada línea empieza con una etiqueta fija y sigue con
`clave=valor`, para leerla con grep y cruzarla con la hora de los eventos. Los
valores que pueden llevar espacios van entre comillas. Las funciones reciben
solo los datos que nombran, nunca un autor ni un texto.
"""

from __future__ import annotations

from guyrapu.core import diagnostico

logger = diagnostico.obtener_logger(__name__)


def _comillas(valor):
    texto = str(valor).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{texto}"'


def _destino(al_video, al_chat):
    """El destino compartido por las alertas y los comandos."""
    if al_video and al_chat:
        return "ambos"
    if al_video:
        return "video"
    if al_chat:
        return "chat"
    return "ninguno"


def escribir(linea):
    """Anota una línea en el registro detallado, si la hay."""
    if linea:
        logger.debug("%s", linea)


def evento(tipo, cantidad, motivo="", mensaje=False):
    """La línea de un evento que llega a las alertas.

    Un mensaje de chat solo deja línea si hubo una alerta o un motivo.
    """
    if mensaje and not cantidad and not motivo:
        return ""
    return (f"ALERTA_EVENTO tipo={tipo} alertas={cantidad} "
            f"motivo={_comillas(motivo)}")


def alerta(nombre, tipo, al_video, al_chat, sin_tarjeta_medio=False):
    """La línea de una alerta que coincide y el destino que le tocó."""
    linea = (f"ALERTA nombre={_comillas(nombre)} evento={tipo} "
             f"destino={_destino(al_video, al_chat)}")
    if sin_tarjeta_medio:
        linea += " sin_tarjeta_medio=si"
    return linea


def meta(nombre, anterior, nuevo, objetivo):
    """La línea del avance de una meta."""
    return (f"META nombre={_comillas(nombre)} anterior={anterior} "
            f"nuevo={nuevo} objetivo={objetivo}")


def meta_cumplida(nombre):
    """La línea de una meta que se acaba de cumplir."""
    return f"META_CUMPLIDA nombre={_comillas(nombre)}"


def comando(nombre, motivo="", al_video=False, al_chat=False):
    """La línea de un comando del chat, con su resultado y su destino."""
    if motivo:
        return (f"COMANDO nombre={_comillas(nombre)} respondio=no "
                f"motivo={_comillas(motivo)}")
    return (f"COMANDO nombre={_comillas(nombre)} respondio=si "
            f"destino={_destino(al_video, al_chat)}")


def pedido_musica(aceptado, destino="", motivo=""):
    """La línea de un pedido de música resuelto, con su resultado."""
    if aceptado:
        return f"PEDIDO_MUSICA aceptado=si destino={destino}"
    return f"PEDIDO_MUSICA aceptado=no motivo={_comillas(motivo)}"


def video_cola(tipo, nombre, aceptada, pendientes):
    """La línea de una pieza que se suma a la cola del vídeo."""
    return (f"VIDEO_COLA tipo={tipo} nombre={_comillas(nombre or '-')} "
            f"aceptada={'si' if aceptada else 'no'} pendientes={pendientes}")


def video_mostrada(tipo, nombre):
    """La línea de una pieza que se mostró en el vídeo."""
    return f"VIDEO_MOSTRADA tipo={tipo} nombre={_comillas(nombre or '-')}"


def video_fallo(tipo, nombre, error):
    """La línea de una pieza que no se pudo mostrar."""
    return (f"VIDEO_FALLO tipo={tipo} nombre={_comillas(nombre or '-')} "
            f"error={_comillas(error)}")


def video_descartada(tipo, nombre, segundos):
    """La línea de una pieza que se descartó por esperar demasiado."""
    return (f"VIDEO_DESCARTADA tipo={tipo} nombre={_comillas(nombre or '-')} "
            f"segundos={segundos:g}")


def video_estado(pausado, silenciado, panico):
    """La línea con el estado nuevo de pausa, silencio y pánico."""
    return (f"VIDEO_ESTADO pausado={pausado} "
            f"silenciado={silenciado} panico={panico}")
