# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Medidas geométricas de las ventanas de la galería, sin wx ni ventanas."""

from __future__ import annotations


def ancho(rect):
    return rect[2]


def alto(rect):
    return rect[3]


def derecha(rect):
    return rect[0] + rect[2]


def abajo(rect):
    return rect[1] + rect[3]


def area(rect):
    return max(0, rect[2]) * max(0, rect[3])


def visibles(controles):
    return [c for c in controles if c["visible"]]


def controles_medibles(controles, tamano):
    """El árbol menos la ventana de nivel superior, que no es un control.

    La galería escribe primero la ventana y su rectángulo es el tamaño total.
    Sus hijos directos siguen teniendo `padre` nulo y se comparan contra
    `[0, 0, *cliente]`, no contra la ventana.
    """
    if (controles and controles[0]["padre"] is None
            and controles[0]["rect"] == [0, 0, *tamano]):
        return list(controles[1:])
    return list(controles)


def area_interseccion(a, b):
    comun_x = min(derecha(a), derecha(b)) - max(a[0], b[0])
    comun_y = min(abajo(a), abajo(b)) - max(a[1], b[1])
    return max(0, comun_x) * max(0, comun_y)


def cabe_dentro(rect, contenedor):
    return (rect[0] >= contenedor[0] and rect[1] >= contenedor[1]
            and derecha(rect) <= derecha(contenedor)
            and abajo(rect) <= abajo(contenedor))


# Viven fuera del área cliente: no se recortan contra ella ni dejan margen.
BARRAS_FUERA_DEL_CLIENTE = frozenset((
    "wxStatusBar", "wxToolBar", "wxMenuBar"))


def medibles_de(ventana):
    """Controles medibles de una ventana: sin la raíz ni las barras."""
    controles = controles_medibles(ventana["controles"], ventana["tamano"])
    return [c for c in visibles(controles)
            if c["clase"] not in BARRAS_FUERA_DEL_CLIENTE]


def hermanos(controles):
    grupos = {}
    for c in visibles(controles):
        grupos.setdefault(c["padre"], []).append(c)
    return grupos


def hermanos_por_clase(controles):
    """Hermanos agrupados por clase, además de por padre.

    Un texto y un campo difieren uno o dos píxeles por el borde nativo del
    campo: eso no es una desalineación de quien diseñó la ventana.
    """
    grupos = {}
    for c in visibles(controles):
        grupos.setdefault((c["padre"], c["clase"]), []).append(c)
    return grupos


def columnas(controles):
    grupos = {}
    for c in visibles(controles):
        grupos.setdefault(c["rect"][0], []).append(c)
    for grupo in grupos.values():
        grupo.sort(key=lambda c: c["rect"][1])
    return grupos


def huecos(columna):
    return [siguiente["rect"][1] - abajo(anterior["rect"])
            for anterior, siguiente in zip(columna, columna[1:])]


def apilados(a, b):
    return abajo(a) <= b[1] or abajo(b) <= a[1]


def envolvente(controles):
    if not controles:
        return None
    izquierda = min(c["rect"][0] for c in controles)
    arriba = min(c["rect"][1] for c in controles)
    return [izquierda, arriba,
            max(derecha(c["rect"]) for c in controles) - izquierda,
            max(abajo(c["rect"]) for c in controles) - arriba]


def margen_exterior(controles, cliente):
    if not controles:
        return None
    return min(min(c["rect"][0], c["rect"][1],
                   cliente[0] - derecha(c["rect"]),
                   cliente[1] - abajo(c["rect"])) for c in controles)


def texto_cabe(control, relleno):
    return control["texto_px"][0] + relleno <= control["rect"][2]
