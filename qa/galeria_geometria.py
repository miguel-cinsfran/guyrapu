# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Lo que no necesita la biblioteca gráfica en el JSON de la galería.

Colores, etiquetas, fuentes y medidas se convierten acá a tipos de Python,
sin importar la interfaz. La galería junta los valores leyendo los controles
y pasa por estas funciones antes de escribir el archivo. Contrato con
`qa/visual_reglas.py`.
"""

from __future__ import annotations


def color_hex(color) -> str:
    """El color efectivo en `#RRGGBB`, con mayúsculas y dos cifras por canal."""
    return "#{:02X}{:02X}{:02X}".format(
        int(color.GetRed()), int(color.GetGreen()), int(color.GetBlue()))


def sin_ampersand(texto) -> str:
    """La etiqueta sin la letra de acceso que marca el diálogo."""
    return str(texto or "").replace("&", "")


def fuente_diccionario(fuente, ppi=None) -> dict:
    """Cara, tamaño en puntos y en píxeles, y peso de la fuente del control.

    `GetPixelSize` da cero mientras la fuente no se usa con un contexto de
    dibujo. Con los puntos por pulgada del monitor se calcula el tamaño que
    tendrá en pantalla, que es lo que mide el contrato.
    """
    pixeles = fuente.GetPixelSize()
    puntos = int(fuente.GetPointSize())
    px = int(pixeles.GetWidth())
    if px <= 0 and ppi is not None:
        vertical = ppi[1] if isinstance(ppi, (tuple, list)) else ppi.GetHeight()
        px = round(puntos * int(vertical) / 72)
    return {
        "cara": fuente.GetFaceName(),
        "puntos": puntos,
        "px": px,
        "peso": int(fuente.GetWeight()),
    }


def rect_relativo(rect, origen) -> list:
    """El rectángulo en píxeles, con el origen en el área cliente de arriba."""
    x, y, ancho, alto = rect
    ox, oy = origen
    return [int(x - ox), int(y - oy), int(ancho), int(alto)]


def medida_texto(extension) -> list:
    """Lo que mide la etiqueta con su fuente, o cero si no tiene etiqueta."""
    if not extension:
        return [0, 0]
    return [int(extension[0]), int(extension[1])]


def control_diccionario(*, id, padre, clase, nombre, etiqueta, rect, visible,
                        habilitado, enfocable, fg, bg, fuente,
                        texto_px) -> dict:
    """Un control del árbol, con su padre y su geometría."""
    return {
        "id": int(id),
        "padre": None if padre is None else int(padre),
        "clase": str(clase),
        "nombre": str(nombre),
        "etiqueta": sin_ampersand(etiqueta),
        "rect": list(rect),
        "visible": bool(visible),
        "habilitado": bool(habilitado),
        "enfocable": bool(enfocable),
        "fg": str(fg),
        "bg": str(bg),
        "fuente": dict(fuente),
        "texto_px": list(texto_px),
    }


def captura_diccionario(muestra, clase, variante, pagina, png, tamano,
                        cliente, tamano_minimo, pantalla, controles) -> dict:
    """El archivo JSON de una página capturada de una muestra."""
    return {
        "muestra": str(muestra),
        "clase": str(clase),
        "variante": str(variante),
        "pagina": None if pagina is None else str(pagina),
        "png": str(png),
        "tamano": list(tamano),
        "cliente": list(cliente),
        "tamano_minimo": (None if tamano_minimo is None
                          else list(tamano_minimo)),
        "pantalla": list(pantalla),
        "controles": list(controles),
    }


def linea_indice(numero, muestra, clase, variante, pagina, png, ancho,
                 alto) -> str:
    """Una línea del índice, por cada imagen que salió."""
    return (f"- {numero:02d} · {png} · {muestra} · {clase} · {variante} · "
            f"{pagina or '—'} · {ancho}x{alto}")
