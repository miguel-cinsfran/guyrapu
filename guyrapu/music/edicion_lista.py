# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Las canciones de la lista que se edita, sin interfaz ni wx.

Única razón para cambiar: qué canciones tiene la lista y en qué orden. Dos
canciones son la misma cuando coinciden por `origen`, así una lista nunca
guarda repetidas.
"""

from __future__ import annotations


class ListaEnEdicion:
    """La lista mutable, en orden, sin canciones repetidas por origen."""

    def __init__(self, temas=()):
        self._temas = []
        self._origenes = set()
        for tema in temas or ():
            if tema.origen in self._origenes:
                continue
            self._origenes.add(tema.origen)
            self._temas.append(tema)

    @property
    def temas(self):
        """Los temas, en el orden de la lista."""
        return tuple(self._temas)

    def contiene(self, tema):
        """Si esa canción ya está en la lista."""
        return tema.origen in self._origenes

    def agregar(self, tema):
        """La agrega al final; devuelve False si ya estaba."""
        if tema.origen in self._origenes:
            return False
        self._origenes.add(tema.origen)
        self._temas.append(tema)
        return True

    def quitar(self, tema):
        """Quita esa canción y devuelve el índice que tenía, o None."""
        for indice, candidato in enumerate(self._temas):
            if candidato.origen == tema.origen:
                del self._temas[indice]
                self._origenes.discard(tema.origen)
                return indice
        return None

    def quitar_en(self, indice):
        """Quita el tema de esa posición y lo devuelve, o None."""
        if not isinstance(indice, int) or isinstance(indice, bool):
            return None
        if indice < 0 or indice >= len(self._temas):
            return None
        tema = self._temas.pop(indice)
        self._origenes.discard(tema.origen)
        return tema

    def mover(self, indice, paso):
        """Mueve un lugar y devuelve el índice nuevo; en el borde, el mismo."""
        if not isinstance(indice, int) or isinstance(indice, bool):
            return indice
        if indice < 0 or indice >= len(self._temas):
            return indice
        destino = max(0, min(len(self._temas) - 1, indice + paso))
        if destino == indice:
            return indice
        tema = self._temas.pop(indice)
        self._temas.insert(destino, tema)
        return destino
