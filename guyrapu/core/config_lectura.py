# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Leer las opciones de lectura y de interfaz de config.ini.

Una sola responsabilidad: las opciones de cada sección validadas contra un
único origen de verdad, sin tener que duplicar la carga de config.ini.
`config` las reexporta para que la carga y las pruebas sigan iguales. Incluye
los segundos de agrupación de los me gusta, que viven en [tiktok], y las
opciones visibles de [ui].
"""

from __future__ import annotations

from guyrapu.core.ini_tipado import leer_entero, leer_texto, leer_booleano


def _formato(p) -> str:
    formato = leer_texto(p, "lectura", "formato_prefijo").lower()
    if formato not in (
            "nombre_mensaje", "mensaje_nombre", "solo_mensaje", "solo_nombre"):
        formato = "nombre_mensaje"
    return formato


def _recientes(p) -> str:
    recientes = leer_texto(p, "lectura", "recientes").lower()
    if recientes not in ("lector", "voz"):
        recientes = "lector"
    return recientes


def _sonido_plataformas(p) -> str:
    sonido = leer_texto(p, "lectura", "sonido_plataformas").lower()
    if sonido not in ("varios", "siempre", "nunca"):
        sonido = "varios"
    return sonido


def opciones_lectura(p) -> dict:
    """La sección [lectura] como claves en memoria, en el mismo orden."""
    return {
        "formato_prefijo": _formato(p),
        "lectura_recientes": _recientes(p),
        "lectura_atajos_globales": leer_booleano(p, "lectura", "atajos_globales"),
        "sonido_plataformas": _sonido_plataformas(p),
        "decir_plataforma": leer_booleano(p, "lectura", "decir_plataforma"),
    }


def opciones_tiktok(p) -> dict:
    """La sección [tiktok] como claves en memoria, en el mismo orden."""
    return {
        "tiktok_usuario": leer_texto(p, "tiktok", "usuario"),
        "tiktok_agrupar_me_gusta": leer_booleano(
            p, "tiktok", "agrupar_me_gusta"),
        "tiktok_segundos_me_gusta": leer_entero(
            p, "tiktok", "segundos_me_gusta", lo=1, hi=120),
        "tiktok_agrupar_entradas": leer_booleano(
            p, "tiktok", "agrupar_entradas"),
        "tiktok_segundos_entradas": leer_entero(
            p, "tiktok", "segundos_entradas", lo=1, hi=120),
    }


def _filtro_activo(p) -> str:
    """El filtro guardado, con el de fábrica si no es válido."""
    filtro = leer_texto(p, "ui", "filtro_activo").lower()
    if filtro not in ("todos", "texto", "superchat", "miembro", "avisos"):
        filtro = "todos"
    return filtro


def opciones_ui(p) -> dict:
    """Las claves de [ui] que se cargan en memoria."""
    return {
        "tamanio_fuente_chat": leer_entero(p, "ui", "tamanio_fuente_chat", lo=8, hi=24),
        "cache_video_mb": leer_entero(p, "ui", "cache_video_mb", lo=0, hi=20000),
        "idioma": leer_texto(p, "ui", "idioma"),
        "filtro_activo": _filtro_activo(p),
        "mostrar_total_superchats": leer_booleano(p, "ui", "mostrar_total_superchats"),
        "autoplay_reproductor": leer_booleano(p, "ui", "autoplay_reproductor"),
        "reproductor_solo_audio": leer_booleano(p, "ui", "reproductor_solo_audio"),
        "mostrar_botones_reproductor": leer_booleano(p, "ui", "mostrar_botones_reproductor"),
    }


def opciones_ui_booleans(p) -> dict:
    """Las casillas de [ui] que se cargan en memoria."""
    return {
        "mostrar_metadatos": leer_booleano(p, "ui", "mostrar_metadatos"),
        "confirmar_salida": leer_booleano(p, "ui", "confirmar_salida"),
        "sonido_inicio": leer_booleano(p, "ui", "sonido_inicio"),
        "silenciar_sonidos": leer_booleano(p, "ui", "silenciar_sonidos"),
        "avisos_cuadro": leer_booleano(p, "ui", "avisos_cuadro"),
    }
