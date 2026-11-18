# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Qué ajuste de OBS arregla una captura que la cortina de NVDA deja negra.

La cortina de pantalla de NVDA ennegrece la captura por DXGI. El método 2
de una captura de pantalla es la captura de Windows 10 (WGC), que sí la
atraviesa. Cambiarlo con `SetInputSettings` rehace la captura dentro de la
misma fuente.
"""

from __future__ import annotations

_METODO_WINDOWS_10 = 2


def cambiar(cliente, nombres, parada=None) -> None:
    """Pone el método Windows 10 en cada captura, sin pisar sus otros ajustes."""
    for nombre in nombres:
        cliente.pedir("SetInputSettings",
                      {"inputName": nombre,
                       "inputSettings": {"method": _METODO_WINDOWS_10},
                       "overlay": True}, parada=parada)
