# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Cómo la app habla HTTP cuando hace falta httpx, en un solo lugar.

Va aparte de `red.py` porque este lo importan muchos módulos al arrancar
y cargar httpx ahí sumaría tiempo de arranque que hoy solo paga quien usa
la IA o Restream. Sin HTTP/2: hay un defecto conocido de httpx con h2,
comentado en `main.py:552`.
"""

import httpx


TiempoAgotado = httpx.TimeoutException
ErrorTransporte = httpx.TransportError
ErrorHTTP = httpx.HTTPError


def cliente():
    return httpx.Client(http2=False)
