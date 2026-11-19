# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""El fotograma del reproductor como captura para la IA.

Da una opción más para el cuadro Agregar captura y decide, según la
opción elegida, si la imagen sale del reproductor o de OBS. Así el cuadro
y la consulta rápida comparten los textos sin importarse entre sí.
"""

from __future__ import annotations

from guyrapu.core.idioma import N_, _
from guyrapu.obs import obs_captura_ia
from guyrapu.player import fotograma_video

# Traductores: aviso al pedir la consulta sin OBS y sin imagen en el reproductor.
TEXTO_SIN_VIDEO = N_("OBS no está abierto y el reproductor no muestra vídeo.")
# Traductores: aviso cuando libVLC no entrega el fotograma pedido.
TEXTO_FOTOGRAMA_FALLIDO = N_("No se pudo capturar el fotograma del vídeo.")
# Traductores: nombre de la captura en la conversación que hereda la ventana de IA.
ETIQUETA_FOTOGRAMA = N_("Fotograma del vídeo")


def opcion_fotograma() -> obs_captura_ia.OpcionCaptura:
    """La opción del reproductor, con el nombre que oye el usuario."""
    etiqueta = _(ETIQUETA_FOTOGRAMA)
    return obs_captura_ia.OpcionCaptura(etiqueta, etiqueta, 0, 0)


def es_fotograma(opcion) -> bool:
    """Si la opción viene del reproductor y no de OBS."""
    return opcion.fuente == _(ETIQUETA_FOTOGRAMA)


def con_fotograma(opciones, reproductor) -> tuple:
    """Agrega el fotograma al final solo si el reproductor muestra vídeo."""
    opciones = tuple(opciones)
    if not fotograma_video.muestra_video(reproductor):
        return opciones
    return opciones + (opcion_fotograma(),)


def capturar(cliente, opcion, reproductor) -> obs_captura_ia.Captura:
    """Captura del reproductor si es el fotograma, si no captura de OBS."""
    if not es_fotograma(opcion):
        return obs_captura_ia.capturar(cliente, opcion)
    try:
        jpeg, ancho, alto = fotograma_video.capturar(reproductor)
    except fotograma_video.FotogramaFallido as error:
        raise obs_captura_ia.CapturaFallida(
            _(TEXTO_FOTOGRAMA_FALLIDO)) from error
    return obs_captura_ia.Captura(jpeg, ancho, alto, None)


def vista_previa(cliente, opcion, reproductor) -> bytes:
    """JPEG chico de la opción para la subventana con resto visual."""
    if not es_fotograma(opcion):
        return obs_captura_ia.vista_previa(cliente, opcion)
    return capturar(cliente, opcion, reproductor).jpeg
