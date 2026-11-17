# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Las opciones de un estilo que se eligen de una lista y su valor guardado.

Sin ventana propia. Su única razón para cambiar es qué opciones ofrecen los
desplegables de un estilo y cómo se traduce cada elección al valor que se
guarda en el estilo.
"""

from __future__ import annotations

import wx

from guyrapu.core.idioma import N_, _
from guyrapu.interaction import animacion
from guyrapu.obs import estilos_aviso, fuentes_windows
from guyrapu.ui.accesibilidad import nombre_accesible
from guyrapu.ui.preferencias_comun import nombre_de_etiqueta

_ALINEACIONES = (
    ("izquierda", N_("Izquierda")),
    ("centro", N_("Centro")),
    ("derecha", N_("Derecha")),
)


def opciones_alineacion():
    return [(clave, _(nombre)) for clave, nombre in _ALINEACIONES]


def opciones_zona():
    return [(clave, _(nombre)) for clave, nombre in estilos_aviso.ZONAS]


def opciones_entrada():
    return [(clave, _(nombre)) for clave, nombre in animacion.ENTRADAS]


def opciones_salida():
    return [(clave, _(nombre)) for clave, nombre in animacion.SALIDAS]


class Fuente:
    """El desplegable de familias y la que se conserva si no se cambia."""

    def __init__(self, panel, rotulo, fuente):
        self.original = str(fuente)
        instaladas = fuentes_windows.familias()
        self.faltante = not any(
            self.original.casefold() == nombre.casefold()
            for nombre in instaladas)
        if self.faltante:
            instaladas = [f"{self.original} (no instalada)"] + instaladas
        self.control = wx.Choice(
            panel, choices=instaladas, name=nombre_de_etiqueta(rotulo))
        nombre_accesible(self.control, self.control.GetName())
        indice = 0 if self.faltante else next(
            posicion for posicion, nombre in enumerate(instaladas)
            if nombre.casefold() == self.original.casefold())
        self.control.SetSelection(indice)

    def valor(self) -> str:
        indice = self.control.GetSelection()
        if self.faltante and indice == 0:
            return self.original
        if 0 <= indice < self.control.GetCount():
            return self.control.GetString(indice)
        return self.original


class Color:
    """El desplegable con los colores por nombre y el personalizado."""

    def __init__(self, panel, rotulo, codigo):
        self.codigo = str(codigo).upper()
        self.especial = all(
            valor != self.codigo for _nombre, valor in estilos_aviso.COLORES)
        opciones = [_(nombre) for nombre, _valor in estilos_aviso.COLORES]
        if self.especial:
            opciones.insert(0, _("Personalizado ({codigo})").format(
                codigo=self.codigo))
        self.control = wx.Choice(
            panel, choices=opciones, name=nombre_de_etiqueta(rotulo))
        nombre_accesible(self.control, self.control.GetName())
        self.control.SetSelection(0 if self.especial else self._indice())

    def _indice(self) -> int:
        for posicion, (_nombre, valor) in enumerate(estilos_aviso.COLORES):
            if valor == self.codigo:
                return posicion
        return 0

    def valor(self) -> str:
        seleccion = self.control.GetSelection()
        if self.especial:
            if seleccion <= 0:
                return self.codigo
            seleccion -= 1
        if 0 <= seleccion < len(estilos_aviso.COLORES):
            return estilos_aviso.COLORES[seleccion][1]
        return self.codigo
