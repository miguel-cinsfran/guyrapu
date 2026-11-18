# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""El archivo de las encuestas guardadas: leer, escribir y convertir.

Puro y sin wx. Única razón para cambiar: el formato guardado de una encuesta
y cómo se pasa de y a sus datos.
"""

from __future__ import annotations

import json
from pathlib import Path

from guyrapu.core import archivos, diagnostico
from guyrapu.core.idioma import _, ngettext
from guyrapu.interaction.encuestas import MAXIMO_OPCIONES

logger = diagnostico.obtener_logger(__name__)

DESTINOS = ("video", "chat", "ambos")
DURACION_POR_DEFECTO = 120
ESTILO_POR_DEFECTO = "clasico"


def _texto(valor) -> str:
    return "" if valor is None else str(valor).strip()


def _opciones(valor) -> list[str]:
    if isinstance(valor, str):
        partes = valor.splitlines()
    elif isinstance(valor, (list, tuple)):
        partes = valor
    else:
        return []
    return [str(parte).strip() for parte in partes
            if str(parte).strip()][:MAXIMO_OPCIONES]


def _segundos(valor) -> int:
    try:
        numero = int(float(valor))
    except (TypeError, ValueError):
        return DURACION_POR_DEFECTO
    return numero if numero > 0 else DURACION_POR_DEFECTO


def _destino(valor) -> str:
    texto = _texto(valor)
    return texto if texto in DESTINOS else "video"


def _estilo(valor) -> str:
    if valor is None:
        return ESTILO_POR_DEFECTO
    return _texto(valor)


def normalizar(datos: dict) -> dict:
    """Los datos de una encuesta tal como se guardan, con los tipos forzados.

    El nombre acompaña a la pregunta: es la clave con la que duplicar y
    combinar lo importado reconocen una encuesta.
    """
    datos = datos if isinstance(datos, dict) else {}
    pregunta = _texto(datos.get("pregunta")) or _texto(datos.get("nombre"))
    return {
        "pregunta": pregunta,
        "nombre": pregunta,
        "opciones": _opciones(datos.get("opciones")),
        "segundos": _segundos(datos.get("segundos")),
        "destino": _destino(datos.get("destino")),
        "estilo": _estilo(datos.get("estilo")),
    }


def cargar(ruta) -> list[dict]:
    """Carga las encuestas y devuelve una lista aunque el archivo esté roto."""
    try:
        with open(ruta, "r", encoding="utf-8") as archivo:
            datos = json.load(archivo)
    except FileNotFoundError:
        return []
    except Exception as exc:
        logger.warning("No se pudo leer %s (se usa una lista vacía): %s",
                       Path(ruta).name, exc)
        return []
    if not isinstance(datos, list):
        logger.warning("No se pudo leer %s (se usa una lista vacía): "
                       "no es una lista", Path(ruta).name)
        return []
    return [normalizar(encuesta) for encuesta in datos
            if isinstance(encuesta, dict)]


def guardar(ruta, encuestas) -> None:
    """Guarda las encuestas mediante un temporal para conservar las anteriores."""
    archivos.escribir_json_atomico(
        ruta, [normalizar(encuesta) for encuesta in encuestas], indent=2)


def duracion(segundos) -> str:
    """La duración en palabras, como se muestra en la lista."""
    segundos = int(segundos)
    if segundos < 60:
        # Traductores: duración de una encuesta; {n} son los segundos.
        return ngettext("{n} segundo", "{n} segundos",
                        segundos).format(n=segundos)
    minutos = segundos // 60
    # Traductores: duración de una encuesta; {n} son los minutos.
    return ngettext("{n} minuto", "{n} minutos", minutos).format(n=minutos)


def fila(encuesta) -> str:
    """La línea de la lista: pregunta, cuántas opciones y duración."""
    datos = normalizar(encuesta)
    opciones = ngettext("{n} opción", "{n} opciones",
                        len(datos["opciones"])).format(
                            n=len(datos["opciones"]))
    # Traductores: una fila de la lista de encuestas; {pregunta} es la
    # pregunta, {opciones} cuántas opciones tiene y {duracion} cuánto dura.
    return _("{pregunta}, {opciones}, {duracion}").format(
        pregunta=datos["pregunta"], opciones=opciones,
        duracion=duracion(datos["segundos"]))


def escuchar(encuesta) -> str:
    """La frase que cuenta la pregunta y sus opciones al pedir Escuchar."""
    datos = normalizar(encuesta)
    # Traductores: lo que se oye al pedir Escuchar una encuesta; {pregunta}
    # es la pregunta y {opciones} sus opciones separadas por comas.
    return _("Encuesta: {pregunta}. Opciones: {opciones}.").format(
        pregunta=datos["pregunta"], opciones=", ".join(datos["opciones"]))
