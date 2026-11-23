# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Paso único de los disparadores viejos a comandos del chat.

Puro salvo la función que toca el disco. Única razón para cambiar: cómo un
disparador de comando, palabra o atajo pasa a ser un comando. Los eventos del
directo no se tocan.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from guyrapu.core import archivos, diagnostico, paths
from guyrapu.interaction import comandos_guardados
from guyrapu.interaction.texto import normalizar

logger = diagnostico.obtener_logger(__name__)

TIPOS_VIEJOS = ("comando", "palabra", "atajo")
NOMBRE_COPIA = "disparadores.anterior.json"


@dataclass(frozen=True)
class Resultado:
    """Lo convertido, lo que sigue siendo de evento y lo que no entró."""

    comandos: list[dict] = field(default_factory=list)
    disparadores: list[dict] = field(default_factory=list)
    descartados: list[str] = field(default_factory=list)


def _leer(ruta) -> list:
    try:
        with open(ruta, "r", encoding="utf-8") as archivo:
            datos = json.load(archivo)
    except Exception:
        return []
    return [dato for dato in datos if isinstance(dato, dict)] \
        if isinstance(datos, list) else []


def _nombres_de(datos: dict) -> list[str]:
    clave = "comandos" if datos.get("cuando") == "comando" else "palabras"
    return [str(palabra).strip() for palabra in (datos.get(clave) or [])
            if str(palabra).strip()]


def _respuesta_de(datos: dict) -> str:
    texto = str(datos.get("tarjeta") or "")
    texto = texto.replace("{cantidad}", "").replace("{regalo}", "")
    return " ".join(texto.split())


def _comando_de(datos: dict) -> dict | None:
    cuando = datos.get("cuando")
    if cuando == "atajo":
        nombre = "".join(str(datos.get("nombre") or "").split())
        alias = []
        permiso = "solo_atajo"
        ubicacion = "principio"
        atajo = datos.get("atajo") or 0
    else:
        palabras = _nombres_de(datos)
        if not palabras:
            return None
        nombre, *alias = palabras
        permiso = datos.get("permiso") or "todos"
        ubicacion = "cualquiera" if cuando == "palabra" else "principio"
        atajo = 0
    if not normalizar(nombre):
        return None
    return comandos_guardados.desde_comando(comandos_guardados.a_comando({
        "nombre": nombre,
        "alias": alias,
        "respuesta": _respuesta_de(datos),
        "medio": datos.get("medio") or "",
        "destino": "video",
        "permiso": permiso,
        "nombres": datos.get("nombres") or [],
        "espera_general": datos.get("espera_general", 5),
        "espera_persona": datos.get("espera_persona", 30),
        "activo": datos.get("activo", True),
        "estilo": datos.get("estilo", "clasico"),
        "segundos": datos.get("segundos", 8),
        "atajo": atajo,
        "ubicacion": ubicacion,
    }))


def _claves_de(comando: dict) -> set[str]:
    return {normalizar(nombre) for nombre in
            (comando["nombre"], *comando.get("alias", ()))}


def _choca(contenido: dict, comandos_actuales: list[dict]) -> dict | None:
    claves = _claves_de(contenido)
    return next((comando for comando in comandos_actuales
                 if claves & _claves_de(comando)), None)


def convertir(datos_comandos, datos_disparadores) -> Resultado:
    """Convierte los tipos viejos sin tocar los disparadores de evento."""
    actuales = [comandos_guardados.normalizar(dato)
                for dato in datos_comandos if isinstance(dato, dict)]
    resultado = Resultado(comandos=list(actuales))
    atajos = {comando["atajo"] for comando in actuales if comando["atajo"]}
    for dato in datos_disparadores:
        if not isinstance(dato, dict):
            continue
        if dato.get("cuando") not in TIPOS_VIEJOS:
            resultado.disparadores.append(dato)
            continue
        nuevo = _comando_de(dato)
        if nuevo is None:
            resultado.descartados.append(
                str(dato.get("nombre") or dato.get("cuando")))
            continue
        choque = _choca(nuevo, resultado.comandos)
        if choque is not None:
            if not choque["medio"] and nuevo["medio"]:
                choque["medio"] = nuevo["medio"]
            resultado.descartados.append(nuevo["nombre"])
            continue
        if nuevo["atajo"] and nuevo["atajo"] in atajos:
            resultado.descartados.append(nuevo["nombre"])
            continue
        resultado.comandos.append(nuevo)
        if nuevo["atajo"]:
            atajos.add(nuevo["atajo"])
    return resultado


def convertir_en_disco(ruta_comandos=None, ruta_disparadores=None):
    """Convierte los archivos de datos una vez, sin lanzar nunca."""
    ruta_comandos = paths.comandos() if ruta_comandos is None else ruta_comandos
    ruta_disparadores = (paths.disparadores() if ruta_disparadores is None
                         else ruta_disparadores)
    try:
        anteriores = _leer(ruta_disparadores)
        if not any(dato.get("cuando") in TIPOS_VIEJOS
                   for dato in anteriores):
            return None
        resultado = convertir(_leer(ruta_comandos), anteriores)
        copia = Path(ruta_disparadores).with_name(NOMBRE_COPIA)
        if not copia.exists():
            archivos.escribir_json_atomico(copia, anteriores, indent=2)
        archivos.escribir_json_atomico(ruta_comandos,
                                       resultado.comandos, indent=2)
        archivos.escribir_json_atomico(ruta_disparadores,
                                       resultado.disparadores, indent=2)
        for descartado in resultado.descartados:
            logger.info("Disparador viejo que no entró: %s", descartado)
        return resultado
    except Exception:
        logger.exception("No se pudieron convertir los disparadores viejos")
        return None
