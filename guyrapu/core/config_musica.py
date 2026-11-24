# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Leer la sección [musica] de config.ini.

Una sola responsabilidad: las opciones de música validadas contra un único
origen de verdad, sin tener que duplicar la carga de config.ini. `config`
las reexporta para que la carga y las pruebas sigan iguales. Lo que necesita
de `config` (`decodificar_texto_ini`, `normalizar_repetir`) se importa dentro
de la función para no cerrar un import circular.
"""

from __future__ import annotations

from guyrapu.core import diagnostico, musica_decir
from guyrapu.core import paths
from guyrapu.core.ini_tipado import leer_texto, leer_booleano, leer_entero


logger = diagnostico.obtener_logger(__name__)


def opciones_musica(p) -> dict:
    """La sección [musica] como claves en memoria, en el mismo orden."""
    from guyrapu.core.config import decodificar_texto_ini, normalizar_repetir

    return {
        "musica_carpeta": paths.resolver_carpeta_musica(decodificar_texto_ini(leer_texto(p, "musica", "carpeta"))),
        "musica_aleatorio": leer_booleano(p, "musica", "aleatorio"),
        "musica_repetir": normalizar_repetir(leer_texto(p, "musica", "repetir")),
        "musica_retomar": leer_booleano(p, "musica", "retomar"),
        "musica_decir": musica_decir.desde_ini(leer_texto(p, "musica", "decir"), leer_booleano(p, "musica", "decir_titulo"),
            leer_booleano(p, "musica", "incluir_artista")),
        "musica_decir_pausa": leer_booleano(p, "musica", "decir_pausa"),
        "musica_normalizar": leer_booleano(p, "musica", "normalizar"),
        "musica_preguntar_igualar": leer_booleano(p, "musica", "preguntar_igualar"),
        "musica_volumen": leer_entero(p, "musica", "volumen", lo=0, hi=100), "musica_cruce": leer_entero(p, "musica", "cruce", lo=0, hi=12),
        "musica_salida": leer_texto(p, "musica", "salida"),
        "musica_salida_nombre": decodificar_texto_ini(leer_texto(p, "musica", "salida_nombre")),
    } | _atajos_musica(p) | _filtros_musica(p) | _atenuacion_musica(p)


def _atenuacion_musica(p) -> dict:
    """Las fuentes y el volumen al bajar, con los valores de fábrica."""
    from guyrapu.music import atenuacion

    opciones = {}
    for fuente in atenuacion.FUENTES:
        clave = f"musica_atenuar_{fuente.id}"
        try:
            opciones[clave] = p.getboolean("musica", f"atenuar_{fuente.id}")
        except Exception:
            opciones[clave] = fuente.fabrica
    try:
        opciones["musica_volumen_atenuado"] = max(0, min(100, int(
            p.get("musica", "volumen_atenuado"))))
    except Exception:
        opciones["musica_volumen_atenuado"] = atenuacion.VOLUMEN_FABRICA
    return opciones


def _atajos_musica(p) -> dict:
    """Las opciones que manejan la música desde fuera de la ventana."""
    return {
        "musica_atajos_globales": leer_booleano(p, "musica", "atajos_globales"),
        "musica_teclas_multimedia": leer_booleano(p, "musica", "teclas_multimedia"),
    }


def _filtros_musica(p) -> dict:
    """La visibilidad de la Cola y los filtros de la ventana de música."""
    return {
        "musica_mostrar_cola": leer_booleano(p, "musica", "mostrar_cola"),
        "musica_mostrar_filtros": leer_booleano(p, "musica", "mostrar_filtros"),
        "musica_orden": leer_texto(p, "musica", "orden"),
        "musica_artista": leer_texto(p, "musica", "artista"),
    }
