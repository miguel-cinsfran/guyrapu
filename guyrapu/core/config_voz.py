# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Leer la sección [voz] de config.ini.

Una sola responsabilidad: las opciones de voz validadas contra un único
origen de verdad, sin tener que duplicar la carga de config.ini. `config`
las reexporta para que la carga y las pruebas sigan iguales. Lo que necesita
de `config` (`guardar_opcion`, `a_entero`) se importa dentro de la función
para no cerrar un import circular.
"""

from __future__ import annotations

from guyrapu.core.ini_tipado import (
    leer_texto, leer_decimal, leer_entero, leer_booleano, a_entero, a_decimal,
)


def _velocidad_voz(p, ruta):
    """La velocidad en porcentaje propio, migrando una sola vez la clave vieja."""
    from guyrapu.core.config import guardar_opcion

    # La velocidad se guarda como porcentaje propio (0..100); la clave vieja
    # en palabras por minuto se convierte una sola vez y se fija en el archivo,
    # así el arranque siguiente no vuelve al valor de fábrica.
    from guyrapu.voice import escala_voz as _escala
    if p.has_option("voz", "velocidad_voz"):
        velocidad_voz = max(0, min(100, a_entero(
            leer_texto(p, "voz", "velocidad_voz"), _escala.VELOCIDAD_NORMAL)))
    elif p.has_option("voz", "velocidad"):
        velocidad_voz = _escala.velocidad_desde_wpm(
            a_entero(leer_texto(p, "voz", "velocidad"), 175))
        guardar_opcion(ruta, "voz", "velocidad_voz", str(velocidad_voz))
    else:
        velocidad_voz = _escala.VELOCIDAD_NORMAL
    return velocidad_voz


def opciones_voz(p, ruta) -> dict:
    """La sección [voz] como claves en memoria, en el mismo orden."""
    from guyrapu.core.config import decodificar_texto_ini

    # [voz]: el motor se valida contra los válidos de Prism (importarlos aquí
    # no arrastra Prism: motores lo importa de forma perezosa).
    from guyrapu.voice import motores as _motores
    from guyrapu.voice import proveedores as _proveedores
    motor = leer_texto(p, "voz", "motor").lower()
    if motor not in _motores.MOTORES:
        motor = _proveedores.PREDETERMINADO
    velocidad_voz = _velocidad_voz(p, ruta)

    return {**opciones_secundarias(p),
        "motor": motor,
        "voz": leer_texto(p, "voz", "voz"),
        "salida_voz": decodificar_texto_ini(leer_texto(p, "voz", "salida")),
        "velocidad_voz": velocidad_voz,
        "volumen": leer_decimal(p, "voz", "volumen"),
        "tono": leer_entero(p, "voz", "tono", lo=0, hi=100),
        "voz_respaldo": leer_texto(p, "voz", "voz_respaldo"),
        "elevenlabs_tope": leer_entero(p, "voz", "elevenlabs_tope", lo=0),
        "elevenlabs_solo_importantes": leer_booleano(p, "voz", "elevenlabs_solo_importantes"),
    }


def opciones_secundarias(p) -> dict:
    """La voz secundaria con su velocidad, su volumen y su respaldo.

    Los valores de fábrica viven acá: la sección [voz] los lee aunque falten
    en config.ini."""
    from guyrapu.voice import escala_voz as _escala
    velocidad = max(0, min(100, a_entero(
        leer_texto(p, "voz", "velocidad_secundaria"), _escala.VELOCIDAD_NORMAL)))
    volumen = max(0.0, min(1.0, a_decimal(
        leer_texto(p, "voz", "volumen_secundaria"), 1.0)))
    return {
        "voz_secundaria": leer_texto(p, "voz", "voz_secundaria"),
        "motor_secundaria": leer_texto(p, "voz", "motor_secundaria"),
        "velocidad_secundaria": velocidad,
        "volumen_secundaria": volumen,
        "voz_respaldo_secundaria": leer_texto(p, "voz", "voz_respaldo_secundaria"),
    }
