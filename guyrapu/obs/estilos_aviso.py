# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Cómo se ve un aviso en el vídeo: estilos de fábrica y del usuario.

Sin wx, sin red y sin OBS. Su única razón para cambiar es el aspecto de un
aviso: las claves de un estilo, sus valores válidos y el cálculo de tamaño,
contraste y fuente.
"""

from __future__ import annotations

import json
import re

from guyrapu.core import archivos
from guyrapu.core.idioma import _, N_
from guyrapu.interaction.animacion import ENTRADAS, SALIDAS
from guyrapu.obs.overlay_datos import relacion_de_contraste

_COLOR_RE = re.compile(r"#[0-9A-Fa-f]{6}")
_CLAVES_ENTRADA = {clave for clave, _nombre in ENTRADAS}
_CLAVES_SALIDA = {clave for clave, _nombre in SALIDAS}

# Traductores: zonas de la pantalla donde se puede ubicar un aviso.
ZONAS = (
    ("automatica", N_("Según la orientación del vídeo")),
    ("arriba_izquierda", N_("Arriba a la izquierda")),
    ("arriba_centro", N_("Arriba al centro")),
    ("arriba_derecha", N_("Arriba a la derecha")),
    ("medio_izquierda", N_("Centro a la izquierda")),
    ("medio_centro", N_("Centro")),
    ("medio_derecha", N_("Centro a la derecha")),
    ("abajo_izquierda", N_("Abajo a la izquierda")),
    ("abajo_centro", N_("Abajo al centro")),
    ("abajo_derecha", N_("Abajo a la derecha")),
)

_CLAVES_ZONA = {clave for clave, _nombre in ZONAS}

# Traductores: tipos de elemento que pueden usar un estilo predeterminado.
TIPOS = (
    ("comando", N_("Comandos")),
    ("disparador", N_("Alertas")),
    ("mensaje", N_("Mensajes automáticos")),
    ("encuesta", N_("Encuestas")),
    ("meta", N_("Metas")),
    ("pregunta", N_("Preguntas")),
)

# Traductores: nombres de los colores disponibles para un estilo de aviso.
COLORES = (
    (N_("Blanco"), "#FFFFFF"),
    (N_("Negro"), "#000000"),
    (N_("Amarillo"), "#FFFF00"),
    (N_("Naranja"), "#FF8C00"),
    (N_("Rojo"), "#E53935"),
    (N_("Rosa"), "#FF4FA3"),
    (N_("Violeta"), "#8E44AD"),
    (N_("Azul"), "#1E64C8"),
    (N_("Celeste"), "#4FC3F7"),
    (N_("Verde"), "#2E9E44"),
    (N_("Gris claro"), "#D0D0D0"),
    (N_("Gris oscuro"), "#1E1E1E"),
)

# La tupla de fábrica no se modifica: quien la pide recibe copias.
# Traductores: nombres de los estilos de aviso de fábrica.
FABRICA = (
    {
        "clave": "clasico",
        "nombre": N_("Clásico"),
        "fuente": "Segoe UI",
        "tamano": 5,
        "negrita": True,
        "color_texto": "#FFFFFF",
        "color_contorno": "#000000",
        "ancho_contorno": 4,
        "color_fondo": "#000000",
        "opacidad_fondo": 0,
        "alineacion": "izquierda",
        "zona": "automatica",
        "entrada": "suave",
        "salida": "fundido",
        "ms_entrada": 350,
        "ms_salida": 250,
        "esquinas": "rectas",
        "sombra": False,
    },
    {
        "clave": "banda",
        "nombre": N_("Banda"),
        "fuente": "Segoe UI",
        "tamano": 4.5,
        "negrita": False,
        "color_texto": "#FFFFFF",
        "color_contorno": "#000000",
        "ancho_contorno": 0,
        "color_fondo": "#1E1E1E",
        "opacidad_fondo": 85,
        "alineacion": "izquierda",
        "zona": "automatica",
        "entrada": "suave",
        "salida": "fundido",
        "ms_entrada": 350,
        "ms_salida": 250,
        "esquinas": "rectas",
        "sombra": False,
    },
    {
        "clave": "tarjeta",
        "nombre": N_("Tarjeta"),
        "fuente": "Segoe UI",
        "tamano": 4,
        "negrita": False,
        "color_texto": "#1A1A1A",
        "color_contorno": "#000000",
        "ancho_contorno": 0,
        "color_fondo": "#FFFFFF",
        "opacidad_fondo": 90,
        "alineacion": "centro",
        "zona": "automatica",
        "entrada": "suave",
        "salida": "fundido",
        "ms_entrada": 350,
        "ms_salida": 250,
        "esquinas": "redondeadas",
        "sombra": True,
    },
    {
        "clave": "alto_contraste",
        "nombre": N_("Alto contraste"),
        "fuente": "Arial",
        "tamano": 5.5,
        "negrita": True,
        "color_texto": "#FFFF00",
        "color_contorno": "#000000",
        "ancho_contorno": 0,
        "color_fondo": "#000000",
        "opacidad_fondo": 100,
        "alineacion": "centro",
        "zona": "automatica",
        "entrada": "suave",
        "salida": "fundido",
        "ms_entrada": 350,
        "ms_salida": 250,
        "esquinas": "rectas",
        "sombra": False,
    },
)

_DEFECTOS = {
    "clave": "",
    "nombre": "",
    "fuente": "Segoe UI",
    "tamano": 5.0,
    "negrita": False,
    "color_texto": "#FFFFFF",
    "color_contorno": "#000000",
    "ancho_contorno": 0,
    "color_fondo": "#000000",
    "opacidad_fondo": 0,
    "alineacion": "izquierda",
    "zona": "automatica",
    "entrada": "suave",
    "salida": "fundido",
    "ms_entrada": 350,
    "ms_salida": 250,
    "esquinas": "redondeadas",
    "sombra": False,
}


def nombre_de_color(codigo) -> str:
    """El nombre traducido del color o, si no está en la lista, su código."""
    buscado = str(codigo).upper()
    for nombre, valor in COLORES:
        if valor == buscado:
            return _(nombre)
    return codigo


def tamano_en_pixeles(estilo: dict, ancho_lienzo: int, alto_lienzo: int) -> int:
    """El tamaño del texto sobre el lado menor del lienzo, redondeado."""
    lado = min(ancho_lienzo, alto_lienzo)
    return max(8, int(round(float(estilo.get("tamano", 5)) * lado / 100)))


def contorno_en_pixeles(estilo: dict, ancho_lienzo: int,
                        alto_lienzo: int) -> int:
    """El ancho del contorno en un lienzo de 1080 de lado menor."""
    lado = min(ancho_lienzo, alto_lienzo)
    return max(0, int(round(float(estilo.get("ancho_contorno", 0)) * lado / 1080)))


def contraste(estilo: dict):
    """La relación de contraste que se puede medir, o None si no hay con qué."""
    if float(estilo.get("opacidad_fondo", 0)) >= 50:
        return relacion_de_contraste(estilo["color_texto"], estilo["color_fondo"])
    if float(estilo.get("ancho_contorno", 0)) >= 1:
        return relacion_de_contraste(estilo["color_texto"],
                                     estilo["color_contorno"])
    return None


def aviso_contraste(estilo: dict) -> str:
    """Un aviso si el contraste no alcanza 4,5 a 1, o vacío si alcanza."""
    relacion = contraste(estilo)
    if relacion is None:
        # Traductores: aviso de un estilo de aviso sin fondo ni contorno.
        return _("El texto no tiene fondo ni contorno y puede perderse sobre "
                 "la imagen.")
    if relacion >= 4.5:
        return ""
    # Traductores: aviso de contraste insuficiente. {relacion} es la relación medida y 4,5 el mínimo.
    return _("El contraste es de {relacion} a 1 y debería ser de al menos "
             "4,5 a 1.").format(relacion=f"{relacion:.1f}".replace(".", ","))


def fuente_para(estilo: dict, instaladas) -> tuple[str, str]:
    """La fuente a usar y un aviso si la elegida no está instalada."""
    fuente = str(estilo.get("fuente", _DEFECTOS["fuente"]))
    if any(fuente.casefold() == str(nombre).casefold() for nombre in instaladas):
        return fuente, ""
    # Traductores: aviso cuando la fuente elegida no está instalada. {fuente} es su nombre.
    return "Segoe UI", _("La fuente {fuente} no está instalada. Se usa Segoe "
                         "UI.").format(fuente=fuente)


def _fuera_de_rango(estilo: dict, clave, minimo, maximo,
                    conversion=int) -> bool:
    try:
        valor = conversion(float(estilo.get(clave)))
    except (TypeError, ValueError):
        return True
    return not minimo <= valor <= maximo


def validar_estilo(estilo: dict, otros) -> str:
    """El error que impide guardar el estilo, o vacío si se puede guardar."""
    nombre = str(estilo.get("nombre", "")).strip()
    if not nombre:
        # Traductores: validación de un estilo de aviso (error).
        return _("El estilo necesita un nombre.")
    for referencia in FABRICA + tuple(otros or ()):
        if referencia.get("clave") == estilo.get("clave"):
            continue
        existente = str(referencia.get("nombre", "")).strip()
        if existente.casefold() == nombre.casefold():
            # Traductores: validación de un estilo de aviso repetido. {nombre} es el nombre.
            return _("Ya hay un estilo llamado {nombre}.").format(nombre=nombre)
    if _fuera_de_rango(estilo, "tamano", 2, 15, float):
        # Traductores: validación del tamaño de un estilo de aviso (error).
        return _("El tamaño debe estar entre 2 y 15.")
    for clave in ("color_texto", "color_contorno", "color_fondo"):
        if not _COLOR_RE.fullmatch(str(estilo.get(clave, ""))):
            # Traductores: validación de un color de un estilo de aviso (error).
            return _("Los colores deben ser códigos como #RRGGBB.")
    if _fuera_de_rango(estilo, "opacidad_fondo", 0, 100):
        # Traductores: validación de la opacidad de un estilo de aviso (error).
        return _("La opacidad del fondo debe estar entre 0 y 100.")
    for clave in ("ms_entrada", "ms_salida"):
        if _fuera_de_rango(estilo, clave, 100, 1000):
            # Traductores: validación de la duración de una animación de aviso (error).
            return _("La duración de la animación debe estar entre 100 y 1000 "
                     "milisegundos.")
    return ""


def _a_bool(valor) -> bool:
    if isinstance(valor, str):
        return valor.strip().lower() in ("true", "1", "yes", "si", "sí", "on")
    return bool(valor)


def _normalizar_estilo(estilo: dict) -> dict:
    resultado = dict(_DEFECTOS)
    resultado.update(estilo)
    # Un JSON editado a mano puede traer "true" o "6.5": se fuerzan los tipos
    # de las claves conocidas para que la ventana no reviente al usarlas.
    for clave, defecto in _DEFECTOS.items():
        valor = resultado[clave]
        try:
            if isinstance(defecto, bool):
                resultado[clave] = _a_bool(valor)
            elif isinstance(defecto, int):
                resultado[clave] = int(float(valor))
            elif isinstance(defecto, float):
                resultado[clave] = float(valor)
            else:
                resultado[clave] = "" if valor is None else str(valor)
        except (TypeError, ValueError):
            resultado[clave] = defecto
    for clave in ("ms_entrada", "ms_salida"):
        resultado[clave] = min(1000, max(100, resultado[clave]))
    if resultado["entrada"] not in _CLAVES_ENTRADA:
        resultado["entrada"] = _DEFECTOS["entrada"]
    if resultado["salida"] not in _CLAVES_SALIDA:
        resultado["salida"] = _DEFECTOS["salida"]
    if resultado["zona"] not in _CLAVES_ZONA:
        resultado["zona"] = "automatica"
    return resultado


def _leer_datos(ruta) -> tuple[list, dict]:
    """Lee el archivo en sus dos formas: la vieja lista o el diccionario nuevo."""
    try:
        with open(ruta, "r", encoding="utf-8") as archivo:
            datos = json.load(archivo)
    except Exception:
        return [], {}
    if isinstance(datos, list):
        return datos, {}
    if isinstance(datos, dict):
        estilos = datos.get("estilos")
        por_tipo = datos.get("por_tipo")
        return (estilos if isinstance(estilos, list) else [],
                por_tipo if isinstance(por_tipo, dict) else {})
    return [], {}


def cargar_estilos(ruta) -> list[dict]:
    """Carga los estilos del usuario sin romperse con un archivo roto."""
    datos, _por_tipo = _leer_datos(ruta)
    claves = {estilo["clave"] for estilo in FABRICA}
    estilos = []
    for entrada in datos:
        if not isinstance(entrada, dict):
            continue
        estilo = _normalizar_estilo(entrada)
        if estilo["clave"] in claves:
            continue
        estilos.append(estilo)
    return estilos


def cargar_por_tipo(ruta) -> dict:
    """El estilo predeterminado de cada tipo; Clásico si no hay otro."""
    _estilos, por_tipo = _leer_datos(ruta)
    resultado = {}
    for tipo, _nombre in TIPOS:
        valor = por_tipo.get(tipo)
        resultado[tipo] = (valor if isinstance(valor, str) and valor
                           else "clasico")
    return resultado


def _guardar(ruta, estilos: list[dict], por_tipo: dict) -> None:
    archivos.escribir_json_atomico(
        ruta, {"estilos": estilos, "por_tipo": por_tipo}, indent=2)


def guardar_estilos(ruta, estilos: list[dict]) -> None:
    """Guarda los estilos mediante un temporal y conserva los predeterminados."""
    _guardar(ruta, estilos, cargar_por_tipo(ruta))


def guardar_por_tipo(ruta, por_tipo: dict) -> None:
    """Guarda los predeterminados mediante un temporal y conserva los estilos."""
    actuales = cargar_por_tipo(ruta)
    actuales.update(por_tipo or {})
    _guardar(ruta, cargar_estilos(ruta), actuales)


def todos(usuario) -> list[dict]:
    """Los estilos de fábrica primero y después los del usuario, como copias."""
    return [dict(estilo) for estilo in FABRICA] + [dict(estilo)
                                                   for estilo in usuario]


def buscar(clave, usuario) -> dict:
    """El estilo con esa clave o el Clásico si no existe."""
    for estilo in todos(usuario):
        if estilo["clave"] == clave:
            return estilo
    return dict(FABRICA[0])


def buscar_para(clave, tipo, usuario, por_tipo) -> dict:
    """El estilo elegido o, con la clave vacía, el predeterminado de su tipo."""
    if not clave:
        clave = (por_tipo or {}).get(tipo) or "clasico"
    return buscar(clave, usuario)
