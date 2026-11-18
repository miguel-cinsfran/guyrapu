# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Decisiones y textos accesibles sobre mensajes descartados."""

from guyrapu.core.idioma import _


UMBRAL_AVISO = 3


def hay_que_avisar(descartados: int, ya_avisado: bool,
                    umbral: int = UMBRAL_AVISO) -> bool:
    """Indica si esta sesión debe anunciar los descartes."""
    return descartados >= umbral and not ya_avisado


def frase_aviso() -> str:
    """Devuelve el aviso que se interrumpe para no ocultar los descartes."""
    # Traductores: aviso que se anuncia cuando se descartan mensajes. F10 es un
    # atajo de teclado fijo y no se traduce.
    return _("La lectura va con retraso y se están descartando mensajes. "
             "Están en la lista del chat. Para seguir el ritmo, sube la "
             "velocidad de la voz con F10.")


def frase_estado(descartados: int) -> str:
    """Devuelve el componente de estado, vacío si no hubo descartes."""
    if descartados <= 0:
        return ""
    # Traductores: componente del estado F2. {descartados} es cuántos mensajes se descartaron.
    return _("Mensajes descartados: {descartados}").format(descartados=descartados)
