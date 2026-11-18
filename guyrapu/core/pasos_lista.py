# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Cómo pasar de una lista de claves a otra con pasos mínimos, sin wx.

Razón del módulo: decidir qué filas se borran y cuáles se insertan para
dejar una lista igual a la deseada sin tocar las que no cambian de lugar.
"""

from __future__ import annotations


def pasos_para_sincronizar(actuales: list[str], deseadas: list[str]) -> list:
    """Pasos `("borrar", i)` e `("insertar", i, clave)` para convertir una
    lista de claves en la otra, sin tocar las filas que no cambian de lugar."""
    actuales = list(actuales)
    deseadas = list(deseadas)
    if actuales == deseadas:
        return []
    pasos: list = []
    simulada = list(actuales)
    deseadas_conjunto = set(deseadas)
    for i in range(len(simulada) - 1, -1, -1):
        if simulada[i] not in deseadas_conjunto:
            pasos.append(("borrar", i))
            del simulada[i]
    i = 0
    while i < len(deseadas):
        if i < len(simulada) and simulada[i] == deseadas[i]:
            i += 1
            continue
        if deseadas[i] in simulada:
            j = simulada.index(deseadas[i])
            pasos.append(("borrar", j))
            del simulada[j]
            continue
        pasos.append(("insertar", i, deseadas[i]))
        simulada.insert(i, deseadas[i])
        i += 1
    while len(simulada) > len(deseadas):
        pasos.append(("borrar", len(simulada) - 1))
        del simulada[-1]
    return pasos
