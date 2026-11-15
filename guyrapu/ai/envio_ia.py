# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Envío real de pedidos de IA, sin reintentos.

Lo llama un hilo, no el de la interfaz.
"""

from guyrapu.ai import protocolos
from guyrapu.core import red_httpx


def _publicar(cliente, pedido, clave, tiempo_espera):
    try:
        respuesta = cliente.post(
            pedido.url, headers=pedido.cabeceras, json=pedido.cuerpo,
            timeout=tiempo_espera)
    except red_httpx.TiempoAgotado as error:
        raise protocolos.ErrorIA(
            protocolos.TIEMPO_AGOTADO, str(error)[:300]) from error
    except red_httpx.ErrorTransporte as error:
        raise protocolos.ErrorIA(
            protocolos.SIN_RED, str(error)[:300]) from error
    try:
        return protocolos.leer_respuesta(
            pedido.protocolo, respuesta.status_code, respuesta.text)
    except protocolos.ErrorIA as error:
        if clave and error.detalle and clave in error.detalle:
            error.detalle = error.detalle.replace(clave, "<clave>")
            error.args = (f"{error.tipo}: {error.detalle}",)
        raise


def enviar(pedido, clave, tiempo_espera, cliente=None):
    if cliente is None:
        with red_httpx.cliente() as propio:
            return _publicar(propio, pedido, clave, tiempo_espera)
    return _publicar(cliente, pedido, clave, tiempo_espera)
