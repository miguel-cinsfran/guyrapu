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


def area_solape(a, b):
    """Área que se pisan dos hermanos.

    La caja de grupo es hermana de los controles que encierra y los contiene
    enteros, así que no cuenta como solape con ellos.
    """
    if (a["clase"] == "wxStaticBox" and b["clase"] != "wxStaticBox"
            and cabe_dentro(b["rect"], a["rect"])):
        return 0
    if (b["clase"] == "wxStaticBox" and a["clase"] != "wxStaticBox"
            and cabe_dentro(a["rect"], b["rect"])):
        return 0
    return area_interseccion(a["rect"], b["rect"])


# Viven fuera del área cliente: no se recortan contra ella ni dejan margen.
BARRAS_FUERA_DEL_CLIENTE = frozenset((
    "wxStatusBar", "wxToolBar", "wxMenuBar"))

# Sus hijos son piezas internas y el borde nativo las saca unos píxeles del
# padre. El control compuesto sí se mide. Medido el 20/11/2026.
CONTENEDORES = frozenset((
    "wxPanel", "wxFrame", "wxDialog", "wxWindow", "wxScrolledWindow",
    "wxScrolledCanvas", "wxStaticBox", "wxRadioBox",
    "wxNotebook", "wxListbook", "wxTreebook", "wxChoicebook",
    "wxAuiNotebook",
))

# La lista de pestañas o categorías de un libro es una pieza interna aunque
# el libro sea un contenedor. Medido el 20/11/2026.
LIBROS = frozenset((
    "wxNotebook", "wxListbook", "wxTreebook", "wxChoicebook",
    "wxAuiNotebook",
))
LISTAS_DE_LIBRO = frozenset((
    "wxListView", "wxListCtrl", "wxTreeCtrl", "wxChoice", "wxListBox",
))

# Lo que cuelga de estos se ve al desplazar: no está recortado y no guarda
# una distancia fija al borde del área cliente. Medido el 20/11/2026.
CONTENEDORES_CON_DESPLAZAMIENTO = frozenset((
    "wxScrolledWindow", "wxScrolledCanvas",
))


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


def _por_id(controles):
    return {c["id"]: c for c in controles}


def _padre(control, por_id):
    if control["padre"] is None:
        return None
    return por_id.get(control["padre"])


def es_pieza_interna(control, por_id):
    """Si el control es parte de un compuesto y no un control suelto."""
    padre = _padre(control, por_id)
    if padre is None:
        return False
    if padre["clase"] not in CONTENEDORES:
        return True
    return (padre["clase"] in LIBROS
            and control["clase"] in LISTAS_DE_LIBRO)


def contenedor_medible(control, por_id, cliente):
    """El rectángulo que limita al control, o None si algún ancestro se desplaza."""
    padre = _padre(control, por_id)
    if padre is None:
        return [0, 0, *cliente]
    actual = padre
    while actual is not None:
        if actual["clase"] in CONTENEDORES_CON_DESPLAZAMIENTO:
            return None
        actual = _padre(actual, por_id)
    return padre["rect"]


def para_recorte(ventana):
    """Medibles de recorte y su índice por id, sin piezas internas."""
    medibles = medibles_de(ventana)
    por_id = _por_id(medibles)
    utiles = [c for c in medibles if not es_pieza_interna(c, por_id)]
    return utiles, por_id


def para_solape(ventana):
    """Controles de solape, sin las piezas internas de los compuestos."""
    controles = controles_medibles(ventana["controles"], ventana["tamano"])
    por_id = _por_id(controles)
    return [c for c in controles if not es_pieza_interna(c, por_id)]


def para_margen(ventana):
    """Controles de margen, sin los que cuelgan de un padre que se desplaza."""
    medibles = medibles_de(ventana)
    por_id = _por_id(medibles)
    cliente = ventana["cliente"]
    return [c for c in medibles
            if contenedor_medible(c, por_id, cliente) is not None]


def texto_cabe(control, relleno):
    return control["texto_px"][0] + relleno <= control["rect"][2]
