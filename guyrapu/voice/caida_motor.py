# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Cuándo avisar que un motor de voz local falla y el mensaje cae a Windows.

`CaidaMotor` guarda la marca de la racha. El worker le pasa el nombre ya
traducido del motor; la clase devuelve el aviso la primera vez y calla las
siguientes hasta que un mensaje leído bien cierre la racha.
"""

from __future__ import annotations

from guyrapu.core.idioma import _


class CaidaMotor:
    """Racha de fallos de un motor local."""

    def __init__(self):
        self._aviso_dado = False

    def fallo(self, nombre):
        """Devuelve el aviso la primera vez de la racha, o None."""
        if self._aviso_dado:
            return None
        self._aviso_dado = True
        return _("{nombre} no responde: se usa la voz de Windows.").format(
            nombre=nombre)

    def exito(self) -> None:
        """Un mensaje leído bien cierra la racha."""
        self._aviso_dado = False
