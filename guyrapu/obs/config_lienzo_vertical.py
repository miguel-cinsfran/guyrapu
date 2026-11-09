# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Configuración del plugin Aitum Vertical Canvas.

El archivo es un objeto con `canvas`, la lista de lienzos, y cada lienzo
tiene `stream_outputs`. Las funciones puras trabajan sobre ese diccionario
y conservan todo lo demás. Leer y escribir el archivo es lo único que toca
el disco; comprobar si OBS está abierto le corresponde a quien llama.
"""

from __future__ import annotations

import copy
import json

from guyrapu.core import archivos


NOMBRE_SALIDA = "Guyrapu"


def _salidas(config):
    lienzos = (config or {}).get("canvas") or []
    if not lienzos:
        return []
    return lienzos[0].get("stream_outputs") or []


def posicion_salida(config, nombre=NOMBRE_SALIDA):
    """La posición de la salida con ese nombre, o None si no está."""
    for indice, salida in enumerate(_salidas(config)):
        if (salida or {}).get("name") == nombre:
            return indice
    return None


def con_salida(config, servidor, clave, nombre=NOMBRE_SALIDA):
    """Devuelve una copia con la salida encendida y su servidor y clave.

    Si la salida ya estaba, se actualiza en su lugar; si no, se agrega al
    final. El resto del archivo y las otras salidas quedan igual.
    """
    resultado = copy.deepcopy(config)
    lienzos = resultado.setdefault("canvas", [])
    if not lienzos:
        lienzos.append({})
    salidas = lienzos[0].setdefault("stream_outputs", [])
    cambios = {"stream_server": servidor, "stream_key": clave,
               "enabled": True}
    indice = posicion_salida(resultado, nombre)
    if indice is None:
        salidas.append({"name": nombre, **cambios})
    else:
        salidas[indice].update(cambios)
    return resultado


def leer(ruta):
    """El contenido del archivo, o None si el plugin nunca se cargó."""
    try:
        with open(ruta, "r", encoding="utf-8") as archivo:
            return json.load(archivo)
    except FileNotFoundError:
        return None


def escribir(ruta, config) -> None:
    """Escribe la configuración sin truncar el archivo anterior."""
    archivos.escribir_json_atomico(ruta, config, indent=2)
