# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Lo puro de la pieza de listas: acciones, teclas y fila elegida.

Una sola razón para cambiar: qué acciones van encendidas y qué fila queda
elegida al poner la lista al día. No abre ventanas.
"""

from __future__ import annotations

import dataclasses
from typing import Callable

import wx

from guyrapu.core.idioma import _

_TECLAS = {
    (wx.WXK_RETURN, wx.MOD_NONE): "intro",
    (wx.WXK_NUMPAD_ENTER, wx.MOD_NONE): "intro",
    (wx.WXK_RETURN, wx.MOD_SHIFT): "mayus+intro",
    (wx.WXK_NUMPAD_ENTER, wx.MOD_SHIFT): "mayus+intro",
    (wx.WXK_RETURN, wx.MOD_CONTROL): "ctrl+intro",
    (wx.WXK_NUMPAD_ENTER, wx.MOD_CONTROL): "ctrl+intro",
    (wx.WXK_UP, wx.MOD_ALT): "alt+flecha_arriba",
    (wx.WXK_DOWN, wx.MOD_ALT): "alt+flecha_abajo",
}

# F2 y Suprimir responden con cualquier modificador, como antes.
_TECLAS_CON_CUALQUIER_MODIFICADOR = {
    wx.WXK_F2: "f2",
    wx.WXK_DELETE: "suprimir",
    wx.WXK_NUMPAD_DELETE: "suprimir",
}

_TECLAS_CON_CONTROL = {
    ord("C"): "ctrl+c",
    ord("c"): "ctrl+c",
    ord("D"): "ctrl+d",
    ord("d"): "ctrl+d",
}


@dataclasses.dataclass(frozen=True)
class Accion:
    """Una acción de la lista, con la etiqueta del botón y su tecla."""

    clave: str
    etiqueta: str
    manejador: Callable[[], None]
    tecla: str | None = None
    necesita_elemento: bool = True
    varios: bool = False
    motivo: Callable[[], str] | None = None
    motivo_indices: Callable[[list[int]], str] | None = None
    opciones: (Callable[[], list[tuple[str, Callable[[], None]]]]
               | None) = None


def _tecla_nombrada(codigo, modificadores) -> str | None:
    """El nombre de la tecla, o None si esa pulsación no es una acción."""
    if codigo in _TECLAS_CON_CONTROL:
        if (modificadores & wx.MOD_CONTROL
                and not modificadores & (wx.MOD_ALT | wx.MOD_SHIFT)):
            return _TECLAS_CON_CONTROL[codigo]
        return None
    nombre = _TECLAS.get((codigo, modificadores))
    if nombre is not None:
        return nombre
    return _TECLAS_CON_CUALQUIER_MODIFICADOR.get(codigo)


def clave_de_tecla(codigo: int, modificadores: int, acciones) -> str | None:
    """La clave de la acción para esa tecla, "menu", o None si no le toca."""
    if (codigo == wx.WXK_WINDOWS_MENU
            or (codigo == wx.WXK_F10 and modificadores & wx.MOD_SHIFT)):
        return "menu"
    tecla = _tecla_nombrada(codigo, modificadores)
    if tecla is None:
        return None
    for accion in acciones:
        if accion.tecla == tecla:
            return accion.clave
    return None


def acciones_encendidas(acciones, elegidas: int) -> dict[str, bool]:
    """Qué acciones van encendidas según cuántas filas están elegidas."""
    return {accion.clave: (not accion.necesita_elemento
                           or elegidas == 1
                           or (elegidas > 1 and accion.varios))
            for accion in acciones}


def motivo_de(accion, indices) -> str:
    """Por qué la acción no aplica a esas filas, o "" si aplica."""
    indices = list(indices)
    propio = ""
    if accion.motivo_indices is not None:
        propio = accion.motivo_indices(indices)
    elif accion.motivo is not None:
        propio = accion.motivo()
    if propio:
        return propio
    if len(indices) > 1 and accion.necesita_elemento and not accion.varios:
        return _("Elige un solo elemento para esta acción")
    return ""


def _con_apariciones(claves):
    """Cada clave con su número de aparición, para que todas sean únicas."""
    vistos = {}
    salida = []
    for clave in claves:
        vez = vistos.get(clave, 0)
        salida.append((clave, vez))
        vistos[clave] = vez + 1
    return salida


def _indice_de_elegida(clave, claves, internas, elegida):
    """La aparición que corresponde a la clave pedida."""
    if clave is not None and clave[0] == elegida and clave in internas:
        return internas.index(clave), False
    return claves.index(elegida), False


def _indice_de_clave(seleccion, clave, claves, internas):
    """La aparición de la clave que ya estaba elegida."""
    if clave in internas:
        indice = internas.index(clave)
        return indice, indice != seleccion
    if clave[0] in claves:
        indice = claves.index(clave[0])
        return indice, indice != seleccion
    return min(max(seleccion, 0), len(claves) - 1), True


def _indice_restaurado(seleccion, clave, claves, internas, elegida):
    """El índice que hay que elegir y si hace falta forzar la selección."""
    if elegida is not None and elegida in claves:
        return _indice_de_elegida(clave, claves, internas, elegida)
    if not claves:
        return 0, False
    if clave is not None:
        return _indice_de_clave(seleccion, clave, claves, internas)
    return min(max(seleccion, 0), len(claves) - 1), True
