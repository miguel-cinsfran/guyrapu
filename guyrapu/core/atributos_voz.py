# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Los atributos que publican los motores de voz y cómo se dicen.

La única razón de este módulo para cambiar es sumar o cambiar un atributo
conocido. Lo que no está en la tabla no se muestra.
"""

from __future__ import annotations

from dataclasses import dataclass

from guyrapu.core.idioma import N_, _


@dataclass(frozen=True)
class Atributo:
    clave: str
    rótulo: str
    valores: dict[str, str]
    en_fila: bool


TABLA = (
    Atributo("calidad", N_("Calidad"), {
        "x_low": N_("muy baja"),
        "low": N_("baja"),
        "medium": N_("media"),
        "high": N_("alta"),
    }, True),
    Atributo("edad", N_("Edad"), {
        "Young": N_("joven"),
        "Young Adult": N_("adulto joven"),
        "Adult": N_("adulto"),
        "Middle-age": N_("mediana edad"),
        "Older Adult": N_("adulto mayor"),
    }, False),
)

_DETALLE = N_("{atributo} según {motor}: {valor}.")


def _conocidos(atributos, solo_fila):
    if not isinstance(atributos, dict):
        return []
    pares = []
    for atributo in TABLA:
        if solo_fila and not atributo.en_fila:
            continue
        valor = atributos.get(atributo.clave)
        if valor in atributo.valores:
            pares.append((atributo, valor))
    return pares


def textos_fila(atributos) -> list[str]:
    """Los atributos de fila conocidos, con su valor traducido."""
    return ["{} {}".format(_(atributo.rótulo).lower(),
                           _(atributo.valores[valor]))
            for atributo, valor in _conocidos(atributos, True)]


def lineas_detalles(atributos, motor) -> list[str]:
    """Una línea por atributo conocido, con el nombre del motor."""
    return [_(_DETALLE).format(atributo=_(atributo.rótulo), motor=motor,
                               valor=_(atributo.valores[valor]))
            for atributo, valor in _conocidos(atributos, False)]
