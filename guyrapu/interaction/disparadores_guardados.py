# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""El archivo de los disparadores: leer, escribir y convertir.

Puro y sin wx. Única razón para cambiar: el formato guardado de un
disparador y cómo se pasa de y a `Disparador`.
"""

from __future__ import annotations

import json

from guyrapu.core import archivos
from guyrapu.interaction.comandos import DESTINOS, PERMISOS, separar_nombres
from guyrapu.interaction.disparadores import (
    CUANDOS, EVENTOS_DEL_DIRECTO, Disparador)


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


def _opcional(valor):
    if valor is None or valor == "":
        return None
    return _numero(valor, None, float)


def _elegido(valor, validos, defecto) -> str:
    texto = _texto(valor).strip()
    return texto if texto in validos else defecto


def _estilo(datos: dict) -> str:
    """El estilo elegido, que puede ser el vacío, o Clásico si falta el dato."""
    if "estilo" not in datos:
        return "clasico"
    return _texto(datos.get("estilo")).strip()


def a_disparador(datos: dict) -> Disparador:
    """Convierte los datos guardados en un `Disparador` seguro de usar."""
    datos = datos if isinstance(datos, dict) else {}
    return Disparador(
        nombre=_texto(datos.get("nombre")),
        cuando=_elegido(datos.get("cuando"), CUANDOS, "evento"),
        evento=_elegido(datos.get("evento"), EVENTOS_DEL_DIRECTO, ""),
        minimo=_opcional(datos.get("minimo")),
        regalo=_texto(datos.get("regalo")),
        medio=_texto(datos.get("medio")),
        destino=_elegido(datos.get("destino"), DESTINOS, "video"),
        tarjeta=_texto(datos.get("tarjeta")),
        estilo=_estilo(datos),
        segundos=_numero(datos.get("segundos"), 8, int),
        permiso=_elegido(datos.get("permiso"), PERMISOS, "todos"),
        nombres=_lista(datos.get("nombres"), separar_nombres),
        espera_general=_numero(datos.get("espera_general"), 5.0, float),
        espera_persona=_numero(datos.get("espera_persona"), 30.0, float),
        activo=_a_bool(datos.get("activo", True)),
    )


def desde_disparador(disparador: Disparador) -> dict:
    """Los datos que se guardan de un disparador, con las listas sueltas."""
    return {
        "nombre": disparador.nombre,
        "cuando": disparador.cuando,
        "evento": disparador.evento,
        "minimo": disparador.minimo,
        "regalo": disparador.regalo,
        "medio": disparador.medio,
        "destino": disparador.destino,
        "tarjeta": disparador.tarjeta,
        "estilo": disparador.estilo,
        "segundos": disparador.segundos,
        "permiso": disparador.permiso,
        "nombres": list(disparador.nombres),
        "espera_general": disparador.espera_general,
        "espera_persona": disparador.espera_persona,
        "activo": disparador.activo,
    }


def normalizar(datos: dict) -> dict:
    """Los datos tal como se guardan, con los tipos forzados."""
    return desde_disparador(a_disparador(datos))


def cargar(ruta) -> list[dict]:
    """Carga los disparadores y devuelve una lista aunque esté roto."""
    try:
        with open(ruta, "r", encoding="utf-8") as archivo:
            datos = json.load(archivo)
        if not isinstance(datos, list):
            return []
        return [normalizar(disparador) for disparador in datos
                if isinstance(disparador, dict)]
    except Exception:
        return []


def guardar(ruta, disparadores) -> None:
    """Guarda los disparadores con un temporal para conservar los anteriores."""
    datos = [desde_disparador(disparador)
             if isinstance(disparador, Disparador)
             else normalizar(disparador) for disparador in disparadores]
    archivos.escribir_json_atomico(ruta, datos, indent=2)
