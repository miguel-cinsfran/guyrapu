# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Qué parte del texto del público puede mostrarse.

Puro y sin captura. Única razón para cambiar: qué palabras del público se
tapan y cuándo un texto es casi todo símbolos.
"""

from __future__ import annotations

import json

from guyrapu.core import archivos
from guyrapu.interaction.texto import normalizar

TAPADO = "***"
MINIMO_SIMBOLOS = 8
PROPORCION_SIMBOLOS = 0.6


def cargar(ruta) -> list[str]:
    """Carga las palabras y devuelve una lista aunque el archivo esté roto."""
    try:
        with open(ruta, "r", encoding="utf-8") as archivo:
            datos = json.load(archivo)
        if not isinstance(datos, list):
            return []
        return [str(palabra).strip() for palabra in datos
                if str(palabra).strip()]
    except Exception:
        return []


def guardar(ruta, palabras) -> None:
    """Guarda las palabras mediante un temporal para conservar el anterior."""
    archivos.escribir_json_atomico(
        ruta, [str(palabra).strip() for palabra in palabras
               if str(palabra).strip()], indent=2)


def _palabras(texto) -> list[str]:
    return [parte for parte in
            (normalizar(palabra) for palabra in (texto or "").split())
            if parte]


def _tramos(texto) -> list[tuple[int, int, str]]:
    """Cada palabra del texto con su tramo y su forma normalizada."""
    tramos = []
    inicio = None
    for indice, caracter in enumerate(texto):
        if caracter.isalnum():
            if inicio is None:
                inicio = indice
        elif inicio is not None:
            tramos.append((inicio, indice,
                           normalizar(texto[inicio:indice])))
            inicio = None
    if inicio is not None:
        tramos.append((inicio, len(texto), normalizar(texto[inicio:])))
    return tramos


def _coinciden(tramos, posicion, frase) -> bool:
    return all(tramos[posicion + salto][2] == palabra
               for salto, palabra in enumerate(frase))


def tapar(texto, bloqueadas) -> str:
    """Reemplaza por `***` cada palabra o frase bloqueada del texto."""
    texto = texto or ""
    frases = [parte for parte in
              (_palabras(entrada) for entrada in bloqueadas or ()) if parte]
    if not frases:
        return texto
    tramos = _tramos(texto)
    reemplazos = []
    posicion = 0
    while posicion < len(tramos):
        for frase in frases:
            fin = posicion + len(frase)
            if fin <= len(tramos) and _coinciden(tramos, posicion, frase):
                reemplazos.append((tramos[posicion][0], tramos[fin - 1][1]))
                posicion = fin
                break
        else:
            posicion += 1
    if not reemplazos:
        return texto
    partes = []
    anterior = 0
    for inicio, fin in reemplazos:
        partes.extend((texto[anterior:inicio], TAPADO))
        anterior = fin
    partes.append(texto[anterior:])
    return "".join(partes)


def es_casi_todo_simbolos(texto) -> bool:
    """Si el texto, sin contar espacios, es 8 o más y más del 60 % símbolos."""
    visibles = [caracter for caracter in (texto or "")
                if not caracter.isspace()]
    if len(visibles) < MINIMO_SIMBOLOS:
        return False
    simbolos = sum(1 for caracter in visibles if not caracter.isalnum())
    return simbolos / len(visibles) > PROPORCION_SIMBOLOS
