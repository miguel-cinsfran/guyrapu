# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Confirmación previa a salir al aire."""

from __future__ import annotations

from guyrapu.core.idioma import N_, _
from guyrapu.restream import destinos_de_mas
from guyrapu.ui import confirmar
from guyrapu.voice import sound_player


_ETIQUETA_TRANSMITIR = N_("&Transmitir")


def confirmar_finalizar(padre) -> bool:
    """Pide confirmar el fin del directo, con el texto de siempre."""
    return confirmar.preguntar(
        padre,
        _("¿Finalizar el directo? Quienes te están viendo dejarán de verte."),
        _("Finalizar directo"), _("&Finalizar directo"),
        _("&Seguir transmitiendo"), predeterminado_si=False)


def _frase_con_destinos(revision, destinos):
    """La frase de la revisión, con el aviso de destinos de más primero."""
    from guyrapu.obs import obs_prevuelo
    frase = obs_prevuelo.frase_revision(revision)
    if not destinos:
        return frase
    return destinos_de_mas.mensaje(destinos) + "\n\n" + frase


def confirmar_transmision(padre, revision, destinos=()) -> bool:
    """Pide confirmar el inicio del directo con la revisión a la vista.

    Mismo texto, título, etiquetas y regla de cancelación por defecto
    que la ventana Transmisión: si la revisión trae problemas o hay
    destinos de más, el foco arranca en Cancelar. Con destinos, su
    mensaje va primero y suena su aviso.
    """
    frase = _frase_con_destinos(revision, destinos)
    problemas = bool(getattr(revision, "problemas", ())) or bool(destinos)
    if destinos:
        sound_player.reproducir("destinos_de_mas")
    return confirmar.preguntar(
        padre, frase, _("Antes de transmitir"), _(_ETIQUETA_TRANSMITIR),
        _("&Cancelar"), icono=confirmar.ICON_INFORMATION,
        predeterminado_si=not problemas)
