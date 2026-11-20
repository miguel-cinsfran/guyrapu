# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Reglas medibles sobre el JSON de geometrías de la galería de ventanas.

Lee los `*.json` de una carpeta, aplica las reglas de diseño y escribe una
línea por hallazgo. No abre ventanas ni importa wx.
"""

from __future__ import annotations

import argparse
import itertools
import json
import sys
from pathlib import Path

_RAIZ = Path(__file__).resolve().parent.parent
for _carpeta in (str(_RAIZ), str(_RAIZ / "qa")):
    if _carpeta not in sys.path:
        sys.path.insert(0, _carpeta)

from guyrapu.obs.overlay_datos import relacion_de_contraste  # noqa: E402
from visual_reglas_medidas import abajo, area, area_interseccion  # noqa: E402
from visual_reglas_medidas import apilados, cabe_dentro, columnas  # noqa: E402
from visual_reglas_medidas import controles_medibles  # noqa: E402
from visual_reglas_medidas import derecha, envolvente, hermanos  # noqa: E402
from visual_reglas_medidas import huecos, margen_exterior  # noqa: E402
from visual_reglas_medidas import texto_cabe, visibles  # noqa: E402

ERROR = "error"
AVISO = "aviso"

GRAVEDAD_CONTRASTE = ERROR
GRAVEDAD_RECORTE = ERROR
GRAVEDAD_SOLAPE = ERROR
GRAVEDAD_LETRA_CHICA = ERROR
GRAVEDAD_FUERA_DE_PANTALLA = ERROR
GRAVEDAD_CASI_ALINEADOS = AVISO
GRAVEDAD_RITMO = AVISO
GRAVEDAD_MARGEN = AVISO
GRAVEDAD_PIE = AVISO
GRAVEDAD_PRINCIPALES = AVISO
GRAVEDAD_FAMILIAS = AVISO
GRAVEDAD_COLOR_AJENO = AVISO
GRAVEDAD_VACIO = AVISO

UMBRAL_CONTRASTE = 4.5
# Espacio que wx reserva además del texto: el borde del control y, en casillas
# y opciones, la caja que va delante. Medido el 19/11/2026.
RELLENO_POR_CLASE = {
    "wxStaticText": 4, "wxButton": 8,
    "wxCheckBox": 20, "wxRadioButton": 20,
}
SOLAPE_MINIMO_PX2 = 1
ALTURA_LETRA_MINIMA_PX = 12
ANCHO_PANTALLA = 1366
ALTO_PANTALLA = 728
ALINEACION_MIN_PX = 1
ALINEACION_MAX_PX = 6
PASO_RITMO_PX = 4
MAX_HUECOS_DISTINTOS = 3
MARGEN_MIN_PX = 8
BOTONES_PIE = ("Aceptar", "Cancelar", "Cerrar")
PIE_MARGEN_MAX_PX = 16
COLOR_PRINCIPAL = "#0B6E63"
MAX_BOTONES_PRINCIPALES = 2
MAX_FAMILIAS_LETRA = 1
MAX_PESOS_LETRA = 2
FRACCION_MINIMA_OCUPACION = 0.5

# La paleta de `guyrapu/ui/tema.py` (`_T`) en hexadecimal. Ese módulo arranca
# wx, que acá no se importa. Medido el 19/11/2026.
PALETA = frozenset((
    "#F3F6F6", "#FFFFFF", "#1C2629", "#56656A", "#0B6E63", "#B42318",
    "#E2E8E8",
))

# Colores que wx toma del sistema cuando el control no fija los suyos: caras y
# textos por defecto de Windows (SYS_COLOUR_BTNFACE, WINDOWTEXT, BTNTEXT,
# GRAYTEXT y HIGHLIGHT). Medido el 19/11/2026.
COLORES_SISTEMA = frozenset((
    "#F0F0F0", "#000000", "#6D6D6D", "#0078D7", "#FFFFFF",
))


def _numero(valor):
    return f"{valor:.1f}".replace(".", ",")


def nuevo(ventana, gravedad, regla, control, detalle):
    """Un hallazgo con el orden de campos del contrato."""
    return {"gravedad": gravedad, "regla": regla,
            "muestra": ventana["muestra"], "pagina": ventana.get("pagina"),
            "control": control, "detalle": detalle}


def formatear_hallazgo(hallazgo):
    lugar = hallazgo["muestra"]
    if hallazgo["pagina"]:
        lugar += "/" + hallazgo["pagina"]
    control = f"«{hallazgo['control']}»" if hallazgo["control"] else ""
    return " ".join(parte for parte in (
        hallazgo["gravedad"], hallazgo["regla"], lugar, control,
        hallazgo["detalle"]) if parte)


def leer_carpeta(carpeta):
    """Las ventanas de los `*.json` de la carpeta, en orden de nombre."""
    return [json.loads(ruta.read_text(encoding="utf-8"))
            for ruta in sorted(carpeta.glob("*.json"))]


def regla_contraste(ventana):
    hallazgos = []
    for c in visibles(ventana["controles"]):
        if not c["etiqueta"].strip():
            continue
        relacion = relacion_de_contraste(c["fg"], c["bg"])
        if relacion < UMBRAL_CONTRASTE:
            detalle = (f"{_numero(relacion)}:1, mínimo "
                       f"{_numero(UMBRAL_CONTRASTE)}:1")
            hallazgos.append(nuevo(ventana, GRAVEDAD_CONTRASTE, "contraste",
                                   c["nombre"], detalle))
    return hallazgos


def regla_recorte(ventana):
    medibles = visibles(controles_medibles(ventana["controles"], ventana["tamano"]))
    por_id = {c["id"]: c for c in medibles}
    cliente = ventana["cliente"]
    hallazgos = []
    for c in medibles:
        padre = por_id.get(c["padre"]) if c["padre"] is not None else None
        contenedor = padre["rect"] if padre else [0, 0, *cliente]
        if not cabe_dentro(c["rect"], contenedor):
            detalle = "fuera del rectángulo de su padre"
            hallazgos.append(nuevo(ventana, GRAVEDAD_RECORTE, "recorte",
                                   c["nombre"], detalle))
        relleno = RELLENO_POR_CLASE.get(c["clase"])
        if relleno is not None and not texto_cabe(c, relleno):
            detalle = (f"etiqueta de {c['texto_px'][0]} px en "
                       f"{c['rect'][2]} px de ancho")
            hallazgos.append(nuevo(ventana, GRAVEDAD_RECORTE, "recorte",
                                   c["nombre"], detalle))
    return hallazgos


def regla_solape(ventana):
    hallazgos = []
    for hermanos_ in hermanos(controles_medibles(ventana["controles"], ventana["tamano"])).values():
        for a, b in itertools.combinations(hermanos_, 2):
            area_comun = area_interseccion(a["rect"], b["rect"])
            if area_comun >= SOLAPE_MINIMO_PX2:
                control = f"{a['nombre']} y {b['nombre']}"
                detalle = f"se pisan {area_comun} px²"
                hallazgos.append(nuevo(ventana, GRAVEDAD_SOLAPE, "solape",
                                       control, detalle))
    return hallazgos


def regla_letra_chica(ventana):
    hallazgos = []
    for c in visibles(ventana["controles"]):
        if c["fuente"]["px"] < ALTURA_LETRA_MINIMA_PX:
            detalle = (f"{c['fuente']['px']} px, mínimo "
                       f"{ALTURA_LETRA_MINIMA_PX} px")
            hallazgos.append(nuevo(ventana, GRAVEDAD_LETRA_CHICA,
                                   "letra_chica", c["nombre"], detalle))
    return hallazgos


def regla_fuera_de_pantalla(ventana):
    hallazgos = []
    campos = (("tamano", "tamaño"), ("tamano_minimo", "tamaño mínimo"))
    for clave, rotulo in campos:
        ancho_, alto_ = ventana[clave]
        if ancho_ > ANCHO_PANTALLA or alto_ > ALTO_PANTALLA:
            detalle = (f"{rotulo} {ancho_}×{alto_} excede "
                       f"{ANCHO_PANTALLA}×{ALTO_PANTALLA}")
            hallazgos.append(nuevo(ventana, GRAVEDAD_FUERA_DE_PANTALLA,
                                   "fuera_de_pantalla", ventana["clase"],
                                   detalle))
    return hallazgos


def regla_casi_alineados(ventana):
    hallazgos = []
    for hermanos_ in hermanos(controles_medibles(ventana["controles"], ventana["tamano"])).values():
        for a, b in itertools.combinations(hermanos_, 2):
            if not apilados(a["rect"], b["rect"]):
                continue
            diferencia = abs(a["rect"][0] - b["rect"][0])
            if ALINEACION_MIN_PX <= diferencia <= ALINEACION_MAX_PX:
                detalle = (f"bordes izquierdos difieren {diferencia} px, "
                           f"entre {ALINEACION_MIN_PX} y "
                           f"{ALINEACION_MAX_PX} px")
                control = f"{a['nombre']} y {b['nombre']}"
                hallazgos.append(nuevo(ventana, GRAVEDAD_CASI_ALINEADOS,
                                       "casi_alineados", control, detalle))
    return hallazgos


def regla_ritmo(ventana):
    hallazgos = []
    for grupo in columnas(controles_medibles(ventana["controles"], ventana["tamano"])).values():
        if len(grupo) < 2:
            continue
        huecos_ = huecos(grupo)
        malos = sorted({h for h in huecos_ if h % PASO_RITMO_PX})
        if malos:
            valores = ", ".join(str(h) for h in malos)
            detalle = (f"huecos de {valores} px, no múltiplos de "
                       f"{PASO_RITMO_PX}")
            hallazgos.append(nuevo(ventana, GRAVEDAD_RITMO, "ritmo",
                                   grupo[0]["nombre"], detalle))
        if len(set(huecos_)) > MAX_HUECOS_DISTINTOS:
            detalle = (f"{len(set(huecos_))} huecos distintos, máximo "
                       f"{MAX_HUECOS_DISTINTOS}")
            hallazgos.append(nuevo(ventana, GRAVEDAD_RITMO, "ritmo",
                                   grupo[0]["nombre"], detalle))
    return hallazgos


def regla_margen(ventana):
    ancho_, alto_ = ventana["cliente"]
    hallazgos = []
    for c in visibles(controles_medibles(ventana["controles"], ventana["tamano"])):
        x, y, ancho_c, alto_c = c["rect"]
        distancia = min(x, y, ancho_ - x - ancho_c, alto_ - y - alto_c)
        if distancia < MARGEN_MIN_PX:
            detalle = (f"a {distancia} px del borde del área cliente, "
                       f"mínimo {MARGEN_MIN_PX} px")
            hallazgos.append(nuevo(ventana, GRAVEDAD_MARGEN, "margen",
                                   c["nombre"], detalle))
    return hallazgos


def regla_pie(ventana):
    botones = [c for c in visibles(ventana["controles"])
               if c["clase"] == "wxButton"
               and c["etiqueta"].strip() in BOTONES_PIE]
    if not botones:
        return []
    ancho_, alto_ = ventana["cliente"]
    nombres = ", ".join(c["nombre"] for c in botones)
    hallazgos = []

    def aviso(detalle):
        return nuevo(ventana, GRAVEDAD_PIE, "pie", nombres, detalle)

    if len({c["rect"][1] for c in botones}) > 1:
        hallazgos.append(aviso("botones en filas distintas"))
    if any(alto_ - abajo(c["rect"]) > PIE_MARGEN_MAX_PX for c in botones):
        hallazgos.append(aviso("botones no están abajo"))
    if ancho_ - max(derecha(c["rect"]) for c in botones) > PIE_MARGEN_MAX_PX:
        hallazgos.append(aviso("botones no están contra la derecha"))
    if len({c["rect"][3] for c in botones}) > 1:
        hallazgos.append(aviso("botones de alturas distintas"))
    return hallazgos


def regla_principales(ventana):
    botones = [c for c in visibles(ventana["controles"])
               if c["clase"] == "wxButton"
               and c["bg"].upper() == COLOR_PRINCIPAL]
    if len(botones) <= MAX_BOTONES_PRINCIPALES:
        return []
    detalle = (f"{len(botones)} botones con fondo {COLOR_PRINCIPAL}, "
               f"máximo {MAX_BOTONES_PRINCIPALES}")
    nombres = ", ".join(c["nombre"] for c in botones)
    return [nuevo(ventana, GRAVEDAD_PRINCIPALES, "principales",
                  nombres, detalle)]


def regla_familias(ventana):
    fuentes = [c["fuente"] for c in visibles(ventana["controles"])
               if c.get("fuente")]
    caras = sorted({f["cara"] for f in fuentes})
    pesos = sorted({f["peso"] for f in fuentes})
    hallazgos = []
    if len(caras) > MAX_FAMILIAS_LETRA:
        detalle = f"{len(caras)} familias de letra: {', '.join(caras)}"
        hallazgos.append(nuevo(ventana, GRAVEDAD_FAMILIAS, "familias",
                               ventana["clase"], detalle))
    if len(pesos) > MAX_PESOS_LETRA:
        valores = ", ".join(str(p) for p in pesos)
        detalle = f"{len(pesos)} pesos: {valores}"
        hallazgos.append(nuevo(ventana, GRAVEDAD_FAMILIAS, "familias",
                               ventana["clase"], detalle))
    return hallazgos


def colores_ajenos(ventana):
    permitidos = PALETA | COLORES_SISTEMA
    ajenos = []
    for c in visibles(ventana["controles"]):
        for canal in ("fg", "bg"):
            color = c.get(canal)
            if color and color.upper() not in permitidos:
                ajenos.append((c["nombre"], canal, color.upper()))
    return ajenos


def regla_color_ajeno(ventana):
    return [nuevo(ventana, GRAVEDAD_COLOR_AJENO, "color_ajeno", nombre,
                  f"{canal} {color} fuera de la paleta y del sistema")
            for nombre, canal, color in colores_ajenos(ventana)]


def regla_vacio(ventana):
    controles = visibles(ventana["controles"])
    ancho_, alto_ = ventana["cliente"]
    if not controles or not ancho_ or not alto_:
        return []
    fraccion = area(envolvente(controles)) / (ancho_ * alto_)
    if fraccion < FRACCION_MINIMA_OCUPACION:
        detalle = (f"ocupa {int(fraccion * 100)}% del área cliente, "
                   f"mínimo {int(FRACCION_MINIMA_OCUPACION * 100)}%")
        return [nuevo(ventana, GRAVEDAD_VACIO, "vacio",
                      ventana["clase"], detalle)]
    return []


REGLAS = (
    regla_contraste, regla_recorte, regla_solape, regla_letra_chica,
    regla_fuera_de_pantalla, regla_casi_alineados, regla_ritmo,
    regla_margen, regla_pie, regla_principales, regla_familias,
    regla_color_ajeno, regla_vacio,
)


def resumen_de(ventanas):
    margenes = {}
    familias, tamanos, colores = set(), set(), set()
    for ventana in ventanas:
        controles = visibles(controles_medibles(ventana["controles"], ventana["tamano"]))
        margen = margen_exterior(controles, ventana["cliente"])
        if margen is not None:
            margenes[margen] = margenes.get(margen, 0) + 1
        for c in controles:
            if c.get("fuente"):
                familias.add(c["fuente"]["cara"])
                tamanos.add(c["fuente"]["px"])
        colores.update(color for _, _, color in colores_ajenos(ventana))
    return {"ventanas": len(ventanas), "margenes": sorted(margenes.items()),
            "familias": sorted(familias), "tamanos": sorted(tamanos),
            "colores_ajenos": sorted(colores)}


def formatear_resumen(resumen):
    margenes = ", ".join(
        f"{px} px en {cantidad} "
        f"{'ventana' if cantidad == 1 else 'ventanas'}"
        for px, cantidad in resumen["margenes"])
    tamanos = resumen["tamanos"]
    texto_tamanos = (", ".join(str(n) for n in tamanos) + " px"
                     if tamanos else "ninguno")
    return "\n".join((
        f"Resumen de {resumen['ventanas']} "
        f"{'ventana' if resumen['ventanas'] == 1 else 'ventanas'}:",
        f"Margen exterior: {margenes or 'sin controles visibles'}",
        "Familias de letra: " + (", ".join(resumen["familias"]) or "ninguna"),
        f"Tamaños de letra: {texto_tamanos}",
        "Colores fuera de la paleta: "
        + (", ".join(resumen["colores_ajenos"]) or "ninguno"),
    ))


def analizar(ventanas):
    """Los hallazgos en orden de ventana y regla, y el resumen."""
    hallazgos = []
    for ventana in ventanas:
        for regla in REGLAS:
            hallazgos.extend(regla(ventana))
    return hallazgos, resumen_de(ventanas)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Revisa las geometrías de una carpeta de la galería.")
    parser.add_argument("carpeta", help="carpeta con los JSON de la galería")
    parser.add_argument("--json", dest="salida",
                        help="archivo donde guardar los hallazgos")
    argumentos = parser.parse_args(argv)
    ventanas = leer_carpeta(Path(argumentos.carpeta))
    hallazgos, resumen = analizar(ventanas)
    for hallazgo in hallazgos:
        print(formatear_hallazgo(hallazgo))
    if not hallazgos:
        print("Sin hallazgos.")
    print()
    print(formatear_resumen(resumen))
    if argumentos.salida:
        Path(argumentos.salida).write_text(
            json.dumps(hallazgos, ensure_ascii=False, indent=2),
            encoding="utf-8")
    return 1 if any(h["gravedad"] == ERROR for h in hallazgos) else 0


if __name__ == "__main__":
    sys.exit(main())
