# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Lo que no necesita la biblioteca gráfica en el JSON de la galería.

Colores, etiquetas, fuentes y medidas se convierten acá a tipos de Python,
sin importar la interfaz. La galería junta los valores leyendo los controles
y pasa por estas funciones antes de escribir el archivo. Contrato con
`qa/visual_reglas.py`.
"""

from __future__ import annotations

from collections import Counter
from itertools import combinations


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


def medida_de_etiqueta(etiqueta, medir) -> list:
    """Ancho y alto de la etiqueta tal como se dibuja, sin letra de acceso.

    wx no pinta el `&` del mnemónico, así que medir la etiqueta cruda da un
    ancho mayor que el del control. La comprobación compara esta medida con
    el rectángulo: tiene que usar el mismo texto que ve el usuario.
    """
    texto = sin_ampersand(etiqueta)
    if not texto:
        return [0, 0]
    medidas = [medir(linea) for linea in texto.split("\n")]
    return [max(int(m[0]) for m in medidas),
            sum(int(m[1]) for m in medidas)]


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


def linea_fallida(numero, muestra, clase, variante, motivo) -> str:
    """Una línea del índice para la captura que no sirve, con su motivo."""
    base = linea_indice(numero, muestra, clase, variante, "", "", 0, 0)
    return base + " · FALLIDA: " + str(motivo)


def controles_con_area(controles):
    """Controles visibles que ocupan algo más que un punto."""
    return [c for c in controles
            if c["visible"] and c["rect"][2] > 0 and c["rect"][3] > 0]


def es_region_plana(colores) -> bool:
    """Si una muestra de píxeles es toda del mismo color.

    Un botón con etiqueta no puede salir como un rectángulo liso: si ocurre,
    el pintado no alcanzó y la captura hay que repetirla.
    """
    return bool(colores) and len(set(colores)) == 1


def _casi_encima(a, b):
    """Si dos rectángulos se pisan casi por completo."""
    comun_x = min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0])
    comun_y = min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1])
    comun = max(0, comun_x) * max(0, comun_y)
    menor = min(max(0, a[2]) * max(0, a[3]),
                max(0, b[2]) * max(0, b[3]))
    return menor > 0 and comun >= menor * 0.9


def _amontonados(controles):
    """Cuántos controles comparten posición o se pisan casi enteros."""
    grupos = {}
    for c in controles:
        grupos.setdefault(c["padre"], []).append(c)
    tocados = set()
    for grupo in grupos.values():
        for a, b in combinations(grupo, 2):
            if a["rect"][:2] == b["rect"][:2] or _casi_encima(a["rect"],
                                                              b["rect"]):
                tocados.add(id(a))
                tocados.add(id(b))
    return len(tocados)


def motivo_invalido(controles, colores=None, tamano=None) -> str | None:
    """Por qué no sirve esta captura, o None si sirve.

    Un layout que no corrió deja los controles en el origen y sin tamaño:
    siguen siendo visibles para wx, pero la imagen no muestra la ventana.
    La ventana de nivel superior no es un control y no se cuenta.
    """
    utiles = controles_con_area(controles)
    if (tamano and utiles
            and utiles[0]["rect"] == [0, 0, tamano[0], tamano[1]]):
        utiles = utiles[1:]
    if len(utiles) < 4:
        return f"solo {len(utiles)} controles visibles con área"
    amontonados = _amontonados(utiles)
    if amontonados * 2 > len(utiles):
        return (f"{amontonados} de {len(utiles)} controles amontonados "
                "en la misma posición")
    if colores:
        comunidad = Counter(colores).most_common(1)[0][1] / len(colores)
        if comunidad >= 0.98:
            return f"la imagen es casi de un color ({comunidad:.0%})"
    return None
