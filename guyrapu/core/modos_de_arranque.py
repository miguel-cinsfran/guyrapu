# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Salidas tempranas de la app, antes del registro, el mutex y las ventanas."""

from __future__ import annotations


def correr(argv):
    """Devuelve el código de salida del modo pedido, o None si es normal."""
    # Autocomprobación del paquete: la corre construir.bat sobre el exe armado.
    # Va antes que todo, sin logging, sin mutex ni ventanas.
    if argv and argv[0] == "--autocomprobar":
        from guyrapu.core import autocomprobacion
        return autocomprobacion.principal(argv[1:])
    # Modo instalador: corre dentro del exe nuevo mientras la app vieja
    # se cierra. Va primero que todo, sin logging, sin mutex ni ventanas.
    if argv and argv[0] == "--instalar-actualizacion":
        from guyrapu.core import instalador
        return instalador.principal_instalador()
    # Modo animador: reproduce los cuadros de OBS en su propio proceso,
    # también antes que todo, sin logging, sin mutex ni ventanas.
    if argv and argv[0] == "--animador":
        from guyrapu.obs import animador
        return animador.principal(argv[1:])
    return None
