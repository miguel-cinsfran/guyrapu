# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""La memoria en memoria de lo ya traducido, por texto e idioma destino.

Su única razón para cambiar es qué traducción se recuerda. Nunca va a
disco y guarda las entradas más recientes que su tope.
"""

from __future__ import annotations

from collections import OrderedDict


class Memoria:
    """Lo ya traducido, con la clave normalizada y un tope de entradas."""

    TOPE = 500

    def __init__(self):
        self._guardadas = OrderedDict()

    def guardar(self, texto, destino, traduccion):
        """Recuerda la traducción y descarta la entrada más vieja si sobra."""
        clave = (destino, _clave(texto))
        self._guardadas[clave] = traduccion
        self._guardadas.move_to_end(clave)
        while len(self._guardadas) > self.TOPE:
            self._guardadas.popitem(last=False)

    def obtener(self, texto, destino):
        """La traducción recordada, o None si no está."""
        return self._guardadas.get((destino, _clave(texto)))


def _clave(texto):
    return texto.strip().lower()
