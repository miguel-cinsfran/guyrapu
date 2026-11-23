# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Reglas comunes de una colección con nombre, sin wx.

Las usan los mensajes automáticos y las usarán estilos, comandos y
encuestas: cómo se nombra una copia, cómo se mueve un elemento un lugar y
cómo se combina lo importado con lo que ya hay.
"""

from __future__ import annotations


def _clave(elemento) -> str:
    """El nombre comparable: sin mayúsculas ni espacios en los extremos."""
    nombre = elemento.get("nombre", "") if isinstance(elemento, dict) else elemento
    return str(nombre).strip().casefold()


def nombre_de_copia(nombre: str, existentes) -> str:
    """El primer nombre libre «<nombre> (copia)», «(copia 2)»..."""
    usados = {_clave(elemento) for elemento in existentes}
    candidato = f"{nombre} (copia)"
    numero = 2
    while _clave(candidato) in usados:
        candidato = f"{nombre} (copia {numero})"
        numero += 1
    return candidato


def mover(lista: list, indice: int, paso: int) -> int | None:
    """Mueve un lugar y devuelve el índice nuevo, o None si no se puede."""
    destino = indice + paso
    if not 0 <= indice < len(lista) or not 0 <= destino < len(lista):
        return None
    lista[indice], lista[destino] = lista[destino], lista[indice]
    return destino


def primero_nuevo(combinada: list, anteriores: set, defecto=0) -> int:
    """La posición del primer elemento que no estaba en `anteriores`, o `defecto`."""
    return next((posicion for posicion, elemento in enumerate(combinada)
                 if id(elemento) not in anteriores), defecto)


def combinar(existentes: list, nuevos: list, reemplazar: bool) -> list:
    """Combina lo importado con lo que ya hay y devuelve la lista nueva.

    Con `reemplazar`, cada nuevo ocupa el lugar del que tiene su nombre y los
    que no existen se agregan al final. Sin reemplazar, todos se agregan al
    final y el que choca recibe un nombre de copia.
    """
    resultado = list(existentes)
    for nuevo in nuevos:
        clave = _clave(nuevo)
        posicion = next((indice for indice, actual in enumerate(resultado)
                         if _clave(actual) == clave), None)
        if posicion is None:
            resultado.append(nuevo)
            continue
        if reemplazar:
            resultado[posicion] = nuevo
            continue
        copia = dict(nuevo) if isinstance(nuevo, dict) else nuevo
        if isinstance(copia, dict):
            copia["nombre"] = nombre_de_copia(copia.get("nombre", ""),
                                              resultado)
        resultado.append(copia)
    return resultado
