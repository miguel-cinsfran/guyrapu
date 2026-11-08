"""Tachado de secretos en los textos que la app escribe en sus registros.

Su única razón para cambiar es qué se considera un secreto en un texto que
la app escribe en sus registros. Es puro y sin wx. Se aplica en el formato
de cada manejador, así cubre también el traceback y lo que se agregue
después.
"""

from __future__ import annotations

import logging
import re

TACHADO = "[tachado]"

_NOMBRES = (
    r"access_token|refresh_token|id_token|client_secret|api_key|stream_key"
    r"|accessToken|refreshToken|clientSecret|apiKey|streamKey"
    r"|token|key|password"
)

_RE_CAMPO = re.compile(
    r'(["\'](?:' + _NOMBRES + r')["\']\s*:\s*)(["\'])(.*?)\2',
    re.IGNORECASE)
_RE_PARAMETRO = re.compile(
    r'([?&\s]|^)(' + _NOMBRES + r')=([^&\s"\']*)',
    re.IGNORECASE)
_RE_BEARER = re.compile(r"(Bearer\s+)\S+", re.IGNORECASE)
_RE_XI_API_KEY = re.compile(r"(xi-api-key:\s*)\S+", re.IGNORECASE)
_RE_RTMP = re.compile(r"(rtmps?://\S*/)([^\s/]+)")
_RE_JWT = re.compile(r"eyJ[A-Za-z0-9_-]*\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+")
_RE_YA29 = re.compile(r"ya29\.[A-Za-z0-9._-]+")
_RE_REFRESH = re.compile(r"1//[A-Za-z0-9_-]+")
_RE_AIZA = re.compile(r"AIza[A-Za-z0-9_-]{35}")


def _ocultar_campos(texto: str) -> str:
    return _RE_CAMPO.sub(lambda m: m.group(1) + m.group(2) + TACHADO
                         + m.group(2), texto)


def _ocultar_parametros(texto: str) -> str:
    return _RE_PARAMETRO.sub(lambda m: f"{m.group(1)}{m.group(2)}={TACHADO}",
                             texto)


def tachar(texto: str) -> str:
    """Reemplaza cada valor secreto por `[tachado]`, conservando el nombre."""
    if not texto:
        return texto
    texto = _ocultar_campos(texto)
    texto = _ocultar_parametros(texto)
    texto = _RE_BEARER.sub(rf"\1{TACHADO}", texto)
    texto = _RE_XI_API_KEY.sub(rf"\1{TACHADO}", texto)
    texto = _RE_RTMP.sub(rf"\1{TACHADO}", texto)
    texto = _RE_JWT.sub(TACHADO, texto)
    texto = _RE_YA29.sub(TACHADO, texto)
    texto = _RE_REFRESH.sub(TACHADO, texto)
    return _RE_AIZA.sub(TACHADO, texto)


class FormatoTachado(logging.Formatter):
    """Formato de registro que tacha los secretos, traceback incluido."""

    def format(self, record: logging.LogRecord) -> str:
        return tachar(super().format(record))
