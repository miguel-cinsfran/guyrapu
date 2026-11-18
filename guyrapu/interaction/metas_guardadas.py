# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""El archivo de las metas: leer, escribir y convertir.

Puro y sin wx. Única razón para cambiar: el formato guardado de una meta y
cómo se pasa de y a `Meta`.
"""

from __future__ import annotations

import json

from guyrapu.core import archivos
from guyrapu.interaction.metas import QUE_CUENTA, Meta


def _texto(valor) -> str:
    return "" if valor is None else str(valor)


def _a_bool(valor) -> bool:
    if isinstance(valor, str):
        return valor.strip().lower() in ("true", "1", "yes", "si", "sí", "on")
    return bool(valor)


def _entero(valor, defecto) -> int:
    try:
        numero = int(float(valor))
    except (TypeError, ValueError, OverflowError):
        return defecto
    return numero if numero > 0 else defecto


def _elegido(valor, validos, defecto) -> str:
    texto = _texto(valor).strip()
    return texto if texto in validos else defecto


def a_meta(datos: dict) -> Meta:
    """Convierte los datos guardados en una `Meta` segura de usar."""
    datos = datos if isinstance(datos, dict) else {}
    return Meta(
        nombre=_texto(datos.get("nombre")),
        que_cuenta=_elegido(
            datos.get("que_cuenta"), QUE_CUENTA, "me_gusta"),
        objetivo=_entero(datos.get("objetivo"), 1),
        estilo=_texto(datos.get("estilo")),
        festejo=_texto(datos.get("festejo")),
        activa=_a_bool(datos.get("activa", True)),
        en_video=_a_bool(datos.get("en_video", False)),
    )


def desde_meta(meta: Meta) -> dict:
    """Los datos que se guardan de una meta."""
    return {
        "nombre": meta.nombre,
        "que_cuenta": meta.que_cuenta,
        "objetivo": meta.objetivo,
        "estilo": meta.estilo,
        "festejo": meta.festejo,
        "activa": meta.activa,
        "en_video": meta.en_video,
    }


def cargar(ruta) -> list[dict]:
    """Carga las metas y devuelve una lista aunque esté roto."""
    try:
        with open(ruta, "r", encoding="utf-8") as archivo:
            datos = json.load(archivo)
        if not isinstance(datos, list):
            return []
        return [desde_meta(a_meta(meta)) for meta in datos
                if isinstance(meta, dict)]
    except Exception:
        return []


def guardar(ruta, metas) -> None:
    """Guarda las metas con un temporal para conservar las anteriores."""
    datos = [desde_meta(meta) if isinstance(meta, Meta)
             else desde_meta(a_meta(meta)) for meta in metas]
    archivos.escribir_json_atomico(ruta, datos, indent=2)
