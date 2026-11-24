# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Qué trae sounds.ini de fábrica y cómo se le pasa a quien ya tiene la app."""

from __future__ import annotations

from guyrapu.core import (archivos, diagnostico, motivos_sonido, paths,
                          sonidos_ini)
from guyrapu.core.eventos_sonido import EVENTOS, SONIDOS
from guyrapu.core.ini_tipado import leer_booleano


logger = diagnostico.obtener_logger(__name__)

# La nueva vale 1. Se graba en `[sesion] version_sonidos`.
VERSION_SONIDOS = 1


def _lineas_archivos(nombres):
    """Nombres en comentarios de hasta 100 caracteres, en orden."""
    lineas = []
    actual = []
    for nombre in nombres:
        if actual and len("# " + ", ".join(actual + [nombre])) > 100:
            lineas.append("# " + ", ".join(actual))
            actual = [nombre]
        else:
            actual.append(nombre)
    if actual:
        lineas.append("# " + ", ".join(actual))
    return lineas


def _enumerar(nombres):
    """Nombres en prosa, con «y» antes del último."""
    if len(nombres) < 2:
        return "".join(nombres)
    if len(nombres) == 2:
        return " y ".join(nombres)
    return ", ".join(nombres[:-1]) + " y " + nombres[-1]


def _texto_fabrica():
    opcionales = motivos_sonido.MOTIVOS["opcional"]
    # `config` importa este módulo: la lista se calcula aquí, desde el
    # catálogo, para no cerrar el ciclo de imports.
    propios = [evento for evento in EVENTOS if evento not in SONIDOS]
    return "\n".join([
        "[sonidos]",
        "volumen = 0.7",
        "# Tema: carpeta en sounds/themes/ con un WAV por sonido y, si hace falta, uno",
        "# con el nombre de un evento. Copia default a mi_tema y pon: tema = mi_tema",
        "tema = default",
        "# Archivos de fábrica:",
        *_lineas_archivos(propios),
        f"# {_enumerar(opcionales)} vienen callados: "
        "se activan en Preferencias, Sonidos.",
        *(f"{clave} =" for clave in opcionales),
        "",
    ])


TEXTO_FABRICA = _texto_fabrica()


def _callar_musica_tema() -> None:
    """Calla el cambio de canción en el sounds.ini del usuario, si existe.

    Se parte de los callados actuales para no activar ninguno de paso.
    """
    ruta = paths.sounds_ini()
    if not ruta.exists():
        return
    try:
        texto = ruta.read_text(encoding="utf-8")
        callados = sonidos_ini.silenciados(texto)
        if "musica_tema" in callados:
            return
        callados.add("musica_tema")
        archivos.escribir_texto_atomico(
            ruta, sonidos_ini.con_silenciados(texto, callados, EVENTOS))
    except Exception as exc:
        logger.warning(
            "No se pudo callar el cambio de canción en sounds.ini: %s", exc)


def migrar(p, ruta) -> None:
    """Calla una sola vez el cambio de canción de quien lo tenía apagado.

    La versión vive en `[sesion] version_sonidos` y se graba aunque no haya
    nada que cambiar. La clave vieja `[musica] sonido_tema` se deja en
    `config.ini`, sin uso.
    """
    from guyrapu.core import config as _config

    try:
        version = p.getint("sesion", "version_sonidos")
    except Exception:
        version = 0
    if version >= VERSION_SONIDOS:
        return
    if (p.has_option("musica", "sonido_tema")
            and not leer_booleano(p, "musica", "sonido_tema")):
        _callar_musica_tema()
    _config.guardar_opcion(
        ruta, "sesion", "version_sonidos", str(VERSION_SONIDOS))
