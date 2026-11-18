# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""El archivo de los comandos del chat: leer, escribir y convertir.

Puro y sin wx. Única razón para cambiar: el formato guardado de un comando
y cómo se pasa de y a `Comando`.
"""

from __future__ import annotations

import json

from guyrapu.core import archivos
from guyrapu.interaction.comandos import (
    DESTINOS, PERMISOS, Comando, separar_alias, separar_nombres)

DEFECTOS = {
    "nombre": "",
    "alias": (),
    "respuesta": "",
    "destino": "video",
    "permiso": "todos",
    "nombres": (),
    "espera_general": 5.0,
    "espera_persona": 30.0,
    "activo": True,
    "estilo": "clasico",
    "segundos": 8,
}


def _texto(valor) -> str:
    return "" if valor is None else str(valor)


def _a_bool(valor) -> bool:
    if isinstance(valor, str):
        return valor.strip().lower() in ("true", "1", "yes", "si", "sí", "on")
    return bool(valor)


def _lista(valor, separar) -> tuple[str, ...]:
    if isinstance(valor, (list, tuple)):
        return tuple(str(parte).strip() for parte in valor
                     if str(parte).strip())
    return separar(_texto(valor))


def _numero(valor, defecto, tipo):
    try:
        return tipo(float(valor))
    except (TypeError, ValueError):
        return defecto


def _elegido(valor, validos, defecto) -> str:
    texto = _texto(valor).strip()
    return texto if texto in validos else defecto


def _estilo(datos: dict) -> str:
    """El estilo elegido, que puede ser el vacío, o Clásico si falta el dato."""
    if "estilo" not in datos:
        return "clasico"
    return _texto(datos.get("estilo")).strip()


def a_comando(datos: dict) -> Comando:
    """Convierte los datos guardados en un `Comando` seguro de usar."""
    datos = datos if isinstance(datos, dict) else {}
    return Comando(
        nombre=_texto(datos.get("nombre")),
        alias=_lista(datos.get("alias"), separar_alias),
        respuesta=_texto(datos.get("respuesta")),
        destino=_elegido(datos.get("destino"), DESTINOS, "video"),
        permiso=_elegido(datos.get("permiso"), PERMISOS, "todos"),
        nombres=_lista(datos.get("nombres"), separar_nombres),
        espera_general=_numero(datos.get("espera_general"), 5.0, float),
        espera_persona=_numero(datos.get("espera_persona"), 30.0, float),
        activo=_a_bool(datos.get("activo", True)),
        estilo=_estilo(datos),
        segundos=_numero(datos.get("segundos"), 8, int),
    )


def desde_comando(comando: Comando) -> dict:
    """Los datos que se guardan de un comando, con las listas sueltas."""
    return {
        "nombre": comando.nombre,
        "alias": list(comando.alias),
        "respuesta": comando.respuesta,
        "destino": comando.destino,
        "permiso": comando.permiso,
        "nombres": list(comando.nombres),
        "espera_general": comando.espera_general,
        "espera_persona": comando.espera_persona,
        "activo": comando.activo,
        "estilo": comando.estilo,
        "segundos": comando.segundos,
    }


def normalizar(datos: dict) -> dict:
    """Los datos de un comando tal como se guardan, con los tipos forzados."""
    return desde_comando(a_comando(datos))


def cargar(ruta) -> list[dict]:
    """Carga los comandos y devuelve una lista aunque el archivo esté roto."""
    try:
        with open(ruta, "r", encoding="utf-8") as archivo:
            datos = json.load(archivo)
        if not isinstance(datos, list):
            return []
        return [normalizar(comando) for comando in datos
                if isinstance(comando, dict)]
    except Exception:
        return []


def guardar(ruta, comandos) -> None:
    """Guarda los comandos mediante un temporal para conservar el anterior."""
    datos = [desde_comando(comando) if isinstance(comando, Comando)
             else normalizar(comando) for comando in comandos]
    archivos.escribir_json_atomico(ruta, datos, indent=2)
