# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Tipos de medio y cómo se dice uno en la lista.

Puro y sin wx. Única razón para cambiar: qué extensiones forman la
biblioteca de medios y cómo se nombran en una fila.
"""

from __future__ import annotations

from pathlib import Path

from guyrapu.core.idioma import N_, _, ngettext

TIPOS = (
    ("imagen", N_("imagen"), (".png", ".jpg", ".jpeg", ".bmp", ".gif")),
    ("video", N_("vídeo"), (".mp4", ".webm", ".mov", ".mkv")),
    ("sonido", N_("sonido"), (".wav", ".mp3", ".ogg", ".m4a")),
)

CLAVES = tuple(clave for clave, _nombre, _extensiones in TIPOS)
EXTENSIONES = tuple(extension for _clave, _nombre, extensiones in TIPOS
                    for extension in extensiones)


def tipo_de(ruta) -> str | None:
    """El tipo del medio por su extensión, o None si no es un medio."""
    sufijo = Path(str(ruta or "")).suffix.lower()
    for clave, _nombre, extensiones in TIPOS:
        if sufijo in extensiones:
            return clave
    return None


def es_medio(ruta) -> bool:
    """Si esa ruta tiene una extensión de la biblioteca."""
    return tipo_de(ruta) is not None


def etiqueta_tipo(tipo) -> str:
    """Cómo se dice un tipo en la interfaz."""
    for clave, nombre, _extensiones in TIPOS:
        if clave == tipo:
            return _(nombre)
    return ""


def comodin() -> str:
    """El filtro del cuadro de Windows, con toda la lista de extensiones."""
    patrones = ";".join("*" + extension for extension in EXTENSIONES)
    return _("Archivos de medios") + "|" + patrones


def duracion_en_palabras(segundos) -> str:
    """La duración en palabras, como se muestra en la lista y el cuadro."""
    segundos = max(0, int(segundos))
    if segundos < 60:
        # Traductores: duración de un medio; {n} son los segundos.
        return ngettext("{n} segundo", "{n} segundos",
                        segundos).format(n=segundos)
    minutos = segundos // 60
    # Traductores: duración de un medio; {n} son los minutos.
    return ngettext("{n} minuto", "{n} minutos", minutos).format(n=minutos)


def fila(medio) -> str:
    """La línea de la lista: nombre, tipo y duración si la tiene."""
    datos = medio if isinstance(medio, dict) else {}
    nombre = str(datos.get("nombre", "")).strip()
    tipo = etiqueta_tipo(datos.get("tipo"))
    duracion = datos.get("duracion") or 0
    if datos.get("tipo") == "imagen":
        # Traductores: una fila de la lista de medios; {nombre} es el nombre
        # y {tipo} la clase de archivo.
        return _("{nombre}, {tipo}").format(nombre=nombre, tipo=tipo)
    if not duracion:
        # Traductores: una fila de la lista de medios sin duración conocida.
        return _("{nombre}, {tipo}, duración desconocida").format(
            nombre=nombre, tipo=tipo)
    # Traductores: una fila de la lista de medios; {duracion} está en palabras.
    return _("{nombre}, {tipo}, {duracion}").format(
        nombre=nombre, tipo=tipo,
        duracion=duracion_en_palabras(duracion))


def escuchar(medio) -> str:
    """La frase que cuenta el nombre y la descripción al pedir Escuchar."""
    datos = medio if isinstance(medio, dict) else {}
    nombre = str(datos.get("nombre", "")).strip()
    descripcion = str(datos.get("descripcion", "")).strip()
    if descripcion:
        # Traductores: lo que se oye al escuchar un medio; {nombre} y
        # {descripcion} son los dos datos del medio.
        return _("{nombre}. {descripcion}").format(
            nombre=nombre, descripcion=descripcion)
    return nombre
