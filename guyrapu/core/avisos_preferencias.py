# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Avisos que deja el guardado de Preferencias.

La ventana principal los dice al recuperar el foco; acá solo se deciden.
"""

from __future__ import annotations

from guyrapu.core.idioma import _


def avisos_al_guardar(fallo_guardado: bool, motor_no_disponible: bool,
                      registro_cambiado: bool,
                      puerto_cambiado_con_panel: bool) -> list[str]:
    """Los avisos que la ventana principal dice después de guardar."""
    # Los avisos se juntan acá y los dice la ventana principal una sola vez,
    # ya con el foco de vuelta en ella: anunciarlos antes de cerrar hacía que
    # el cambio de foco los cortara entre sí.
    guardado = _("Preferencias guardadas.")
    fallo = _("Las preferencias se aplicaron, pero no se pudieron guardar "
              "en el disco. Se perderán al cerrar la aplicación.")
    avisos = [guardado if not fallo_guardado else fallo]
    if motor_no_disponible:
        avisos.append(_("El motor elegido no está disponible, se conserva el anterior."))
    if registro_cambiado:
        avisos.append(_("El cambio del registro detallado se aplica al reiniciar "
                        "la aplicación."))
    # El servidor del panel ya escucha en el puerto viejo; no se reinicia
    # solo, así que se avisa dónde se aplica.
    if puerto_cambiado_con_panel:
        avisos.append(_("El puerto del chat en el vídeo se aplica al desactivarlo y "
                        "volver a activarlo desde el panel de transmisión."))
    return avisos
