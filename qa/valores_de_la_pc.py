# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Qué valores dependen de la PC y con qué marcador se escriben.

Declara una sola vez de dónde salen esos valores, cómo se aplica su marcador
y cómo se calculan todos juntos. Sumar otro valor es sumar su entrada.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple

from guyrapu.core import atajos, tecla_fisica
from guyrapu.voice import motores

logger = logging.getLogger(__name__)

CARPETA_APP = Path(__file__).resolve().parents[1]


class Entrada(NamedTuple):
    """De dónde salen los valores de esta PC y cómo se escriben en la línea."""

    valores: Callable[[], list[tuple[str, str]]]
    aplicar: Callable[[str, list[tuple[str, str]]], str]


def aplicar_texto(texto, pares):
    """Escribe el marcador de cada valor, primero el más largo."""
    for valor, marcador in sorted(pares, key=lambda par: len(par[0]),
                                  reverse=True):
        if valor:
            texto = texto.replace(valor, marcador)
    return texto


def aplicar_carpeta(texto, pares):
    """Escribe <carpeta de la app> la raíz del árbol que cambia por PC.

    Windows no distingue mayúsculas en las rutas y la transcripción muestra
    las barras dobladas por `repr`, así que el patrón admite una o dos barras
    y compara sin mirar el caso. Medido el 24/11/2026.
    """
    for valor, marcador in pares:
        patron = re.escape(valor).replace(r"\\", r"\\{1,2}")
        texto = re.sub(patron, marcador, texto, flags=re.IGNORECASE)
    return texto


_COMBINACION = re.compile(r"[^\s,;()\"]+(?:\+[^\s,;()\"]+)+")


def aplicar_teclas(texto, pares):
    """Escribe el marcador de la tecla física solo dentro de combinaciones."""
    return _COMBINACION.sub(
        lambda combinacion: aplicar_texto(combinacion.group(), pares), texto)


def valores_carpeta():
    return [(str(CARPETA_APP), "<carpeta de la app>")]


def valores_voces():
    pares = []
    for motor in ("sapi", "onecore"):
        try:
            nombres = motores.listar_voces(motor)
        except Exception as exc:
            logger.warning("no se pudieron listar las voces de %s: %s",
                           motor, exc)
            continue
        pares.extend((nombre, "<voz de Windows>") for nombre in nombres)
    return pares


def valores_teclas():
    pares = []
    for valores in (atajos.ATAJOS_FIJOS_DEFAULTS, atajos.ATAJOS_DEFAULTS):
        for valor in valores.values():
            for parte in valor.split("+"):
                if (len(parte) == 4 and parte.startswith("sc")
                        and all(c in "0123456789abcdef" for c in parte[2:])):
                    caracter = tecla_fisica.texto_tecla(int(parte[2:], 16))
                    if caracter:
                        pares.append((caracter, f"<tecla {parte}>"))
    return pares


# Lo que cambia por PC se declara acá una sola vez: de dónde salen los
# valores de esta PC y qué marcador llevan. Sumar otro valor es sumar su
# entrada.
ENTRADAS = (
    Entrada(valores_carpeta, aplicar_carpeta),
    Entrada(valores_voces, aplicar_texto),
    Entrada(valores_teclas, aplicar_teclas),
)


def normalizar(texto, valores):
    if not isinstance(texto, str):
        return texto
    for entrada, pares in zip(ENTRADAS, valores):
        texto = entrada.aplicar(texto, pares)
    return texto


def calcular():
    """Los valores de esta PC, listos para aplicar en una sola corrida."""
    return [entrada.valores() for entrada in ENTRADAS]
