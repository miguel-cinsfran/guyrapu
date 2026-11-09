# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Qué destinos de Restream sobran para un directo de TikTok y cómo se nombran.

Puro: sin red ni wx. Recibe los canales ya leídos por quien llama.
"""

from __future__ import annotations

from guyrapu.core.idioma import _

PLATAFORMA_TIKTOK = "TikTok"


def de_mas(canales):
    """Los canales encendidos que no son de TikTok, en su orden."""
    return tuple(canal for canal in canales or ()
                 if bool(getattr(canal, "activo", False))
                 and canal.plataforma != PLATAFORMA_TIKTOK)


def mensaje(canales):
    """El texto de la pregunta, con cada destino como «plataforma (nombre)»."""
    destinos = ", ".join(f"{canal.plataforma} ({canal.nombre})"
                         for canal in canales)
    return _("Restream también va a transmitir este directo a: {destinos}. "
             "Para elegir a dónde sale, usa un perfil de Restream en "
             "Transmitir a. ¿Transmitir igual?").format(destinos=destinos)
