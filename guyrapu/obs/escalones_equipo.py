# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Qué ajustes aguantan una prueba del equipo y cuáles se prueban después.

Su única razón para cambiar es qué se considera aguantar y qué se baja
después. Sin wx: las descripciones también las usan los cuadros del panel.
"""

from __future__ import annotations

from dataclasses import replace

from guyrapu.core.idioma import _
from guyrapu.obs import ajustes_perfil
from guyrapu.obs import textos_perfil

UMBRAL = 0.02
_GPU = ("nvenc", "qsv", "amd")


def aguanta(perdidos_dibujar, totales_dibujar, perdidos_codificar,
            totales_codificar) -> bool:
    """Verdadero si cada porcentaje es de 2 % o menos y hubo fotogramas."""
    try:
        dibujar = max(0, int(perdidos_dibujar))
        total_dibujar = int(totales_dibujar)
        codificar = max(0, int(perdidos_codificar))
        total_codificar = int(totales_codificar)
    except (TypeError, ValueError):
        return False
    if total_dibujar <= 0 or total_codificar <= 0:
        return False
    return (dibujar <= total_dibujar * UMBRAL
            and codificar <= total_codificar * UMBRAL)


def _mejor_grafica(disponibles) -> str:
    vistos = [nombre for nombre in (disponibles or ()) if nombre in _GPU]
    return ajustes_perfil.mejor_codificador(vistos)


def _en_vertical(ajustes) -> bool:
    return (ajustes.alto_lienzo > ajustes.ancho_lienzo
            or ajustes.alto_salida > ajustes.ancho_salida)


def siguiente(ajustes, disponibles):
    """Los ajustes del escalón siguiente, o None si no queda ninguno."""
    if ajustes.codificador == "x264":
        grafica = _mejor_grafica(disponibles)
        if grafica in _GPU:
            return replace(ajustes, codificador=grafica,
                           preset=ajustes_perfil.preset_intermedio(grafica))
    if ajustes.fps > 30:
        return replace(ajustes, fps=30)
    if ajustes.alto_salida > 720:
        if _en_vertical(ajustes):
            salida = (720, 1280)
        else:
            salida = (1280, 720)
        return replace(ajustes, ancho_salida=salida[0],
                       alto_salida=salida[1])
    return None


def escalones(ajustes, disponibles) -> tuple:
    """El escalón pedido y los que le siguen, sin repetir ninguno."""
    pasos = []
    actual = ajustes
    while actual is not None and len(pasos) < 8:
        pasos.append(actual)
        actual = siguiente(actual, disponibles)
    return tuple(pasos)


def describir(ajustes) -> str:
    """Los ajustes en una frase, para el cuadro previo y cada escalón."""
    return _(
        "codificador {codificador}, preset {preset}, {fps} fotogramas por "
        "segundo y salida de {ancho} por {alto}").format(
            codificador=textos_perfil.decir_codificador(ajustes.codificador),
            preset=textos_perfil.decir_preset(
                ajustes.codificador, ajustes.preset),
            fps=ajustes.fps,
            ancho=ajustes.ancho_salida,
            alto=ajustes.alto_salida)


def diferencias(antes, despues) -> str:
    """Qué cambió entre dos ajustes, en frases para el cuadro de resultado."""
    frases = []
    if antes.codificador != despues.codificador:
        frases.append(_("Codificador: {antes} a {despues}.").format(
            antes=textos_perfil.decir_codificador(antes.codificador),
            despues=textos_perfil.decir_codificador(despues.codificador)))
    if antes.fps != despues.fps:
        frases.append(_("Fotogramas por segundo: {antes} a {despues}.").format(
            antes=antes.fps, despues=despues.fps))
    if (antes.ancho_salida, antes.alto_salida) != (
            despues.ancho_salida, despues.alto_salida):
        frases.append(_("Salida: {ancho} por {alto} a {nuevo_ancho} por "
                        "{nuevo_alto}.").format(
                            ancho=antes.ancho_salida,
                            alto=antes.alto_salida,
                            nuevo_ancho=despues.ancho_salida,
                            nuevo_alto=despues.alto_salida))
    if not frases:
        return _("Sin cambios.")
    return " ".join(frases)
