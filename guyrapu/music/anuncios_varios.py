# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Avisos de la música cuando una acción se hace con varias canciones.

Vive aparte de `anuncios`, que está en el tope de líneas: son los textos que
responden a una acción de la ventana de música sobre varias filas a la vez.
"""

from __future__ import annotations

from guyrapu.core.idioma import ngettext
from guyrapu.music import anuncios


def aviso_eliminados_de_cola(cantidad) -> anuncios.Aviso:
    """Cuántas canciones salieron de la cola de una sola vez."""
    texto = ngettext(
        "{n} canción eliminada de la cola",
        "{n} canciones eliminadas de la cola", cantidad).format(n=cantidad)
    return anuncios.Aviso(texto)


def aviso_eliminados_de_lista(cantidad) -> anuncios.Aviso:
    """Cuántas canciones salieron de una lista propia de una sola vez."""
    texto = ngettext(
        "{n} canción eliminada de la lista",
        "{n} canciones eliminadas de la lista", cantidad).format(n=cantidad)
    return anuncios.Aviso(texto, importante=True)


def aviso_agregados_a_lista(cantidad, nombre) -> anuncios.Aviso:
    """Cuántas canciones se sumaron a una lista propia de una sola vez."""
    texto = ngettext(
        "{n} canción agregada a la lista {nombre}",
        "{n} canciones agregadas a la lista {nombre}", cantidad).format(
            n=cantidad, nombre=nombre)
    return anuncios.Aviso(texto, importante=True)
