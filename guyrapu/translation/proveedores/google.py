# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""El proveedor de traducción de Google, sin clave.

Habla con la dirección de lote, que devuelve el idioma de origen de cada
texto, y si esa llamada falla traduce de a uno. Su única razón para
cambiar es hablar con Google y leer su respuesta.
"""

from __future__ import annotations

import httpx

from guyrapu.core.idioma import N_, _
from guyrapu.translation.proveedores.base import (
    ErrorTraduccion,
    Proveedor,
    Traduccion,
)

URL_LOTE = "https://clients5.google.com/translate_a/t"
URL_SUELTA = "https://translate.googleapis.com/translate_a/single"

_FALLOS = (httpx.HTTPError, ValueError, TypeError, IndexError, KeyError)


def traducir(textos, destino, plazo, cliente=None):
    """Traduce el lote y devuelve una Traduccion por texto, en su orden."""
    if not textos:
        return []
    propio = cliente is None
    cliente = cliente or httpx.Client()
    try:
        try:
            return _por_lote(cliente, textos, destino, plazo)
        except _FALLOS:
            try:
                return [_de_a_uno(cliente, texto, destino, plazo)
                        for texto in textos]
            except _FALLOS:
                raise ErrorTraduccion(
                    _("No se pudo traducir. Se lee el mensaje original.")
                ) from None
    finally:
        if propio:
            cliente.close()


def _por_lote(cliente, textos, destino, plazo):
    respuesta = cliente.get(URL_LOTE, params={
        "client": "dict-chrome-ex",
        "sl": "auto",
        "tl": destino,
        "q": textos,
    }, timeout=plazo)
    respuesta.raise_for_status()
    traducciones = [Traduccion(texto, origen)
                    for texto, origen in respuesta.json()]
    if len(traducciones) != len(textos):
        raise ValueError("el lote no trae una traducción por texto")
    return traducciones


def _de_a_uno(cliente, texto, destino, plazo):
    respuesta = cliente.get(URL_SUELTA, params={
        "client": "gtx",
        "sl": "auto",
        "tl": destino,
        "dt": "t",
        "q": texto,
    }, timeout=plazo)
    respuesta.raise_for_status()
    datos = respuesta.json()
    return Traduccion("".join(parte[0] for parte in datos[0]), datos[2])


PROVEEDOR_GOOGLE = Proveedor(
    id="google",
    nombre=N_("Google, sin clave"),
    pide_clave=False,
    traducir=traducir,
)
