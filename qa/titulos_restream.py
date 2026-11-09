# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Los destinos de la cuenta de Restream y sus títulos en la prueba.

La app escribe el título y la descripción del directo en cada destino del
perfil al transmitir. La prueba anota cómo estaban antes de empezar y los
devuelve al terminar, aunque la prueba haya fallado a mitad.
"""

from __future__ import annotations

from guyrapu.core import paths

from directo_comun import destino_tiktok


def leer_cuenta(anotar, cuenta_mod):
    """Lee la cuenta y guarda el título y la descripción de cada destino."""
    estado = {"respaldos": {}, "antes": {}, "rutas": {
        "config": paths.config_ini(),
        "sonidos": paths.sounds_ini(),
        "perfiles": paths.perfiles_restream(),
    }, "raiz": paths.carpeta_instalacion()}
    try:
        canales = cuenta_mod.canales()
    except Exception as exc:
        anotar("cuenta de Restream", False, f"no se pudo leer: {exc}")
        return None
    try:
        estado["titulos"] = guardar(canales, cuenta_mod)
    except Exception as exc:
        anotar("títulos de Restream", False,
               f"no se pudieron leer antes de empezar: {exc}")
        return None
    try:
        canal_tiktok = destino_tiktok(canales)
    except ValueError as exc:
        anotar("destino de TikTok", False, str(exc))
        return None
    anotar("destino de TikTok", True,
           f"{canal_tiktok.plataforma}: {canal_tiktok.nombre} "
           f"(id {canal_tiktok.id})")
    estado["canales_antes"] = list(canales)
    estado["canal_tiktok"] = canal_tiktok
    estado["antes"] = {canal.id: bool(canal.activo) for canal in canales}
    return estado


def guardar(canales, cuenta_mod) -> dict:
    """Título y descripción de cada destino, por id."""
    guardados = {}
    for canal in canales:
        try:
            meta = cuenta_mod.leer_meta(canal.id)
        except Exception as exc:
            raise RuntimeError(f"{canal.id}: {exc}") from exc
        guardados[canal.id] = (meta.titulo, meta.descripcion)
    return guardados


def devolver(guardados, cuenta_mod, ids_actuales):
    """Devuelve los títulos cambiados; salta los destinos que ya no existen.

    No corta en el primer fallo: devuelve los destinos restaurados y los
    fallos con su error.
    """
    devueltos = []
    fallos = []
    for identificador, (titulo, descripcion) in guardados.items():
        if identificador not in ids_actuales:
            continue
        try:
            meta = cuenta_mod.leer_meta(identificador)
            if (meta.titulo, meta.descripcion) != (titulo, descripcion):
                cuenta_mod.cambiar_meta(identificador, titulo, descripcion)
                devueltos.append(identificador)
        except Exception as exc:
            fallos.append((identificador, str(exc)))
    return devueltos, fallos


def paso_devolver(estado, anotar, cuenta_mod) -> None:
    """Anota el paso «títulos de Restream» con lo que se devolvió."""
    guardados = estado.get("titulos")
    if not guardados:
        return
    try:
        ids_actuales = {canal.id for canal in cuenta_mod.canales()}
    except Exception as exc:
        anotar("títulos de Restream", False,
               f"no se pudieron leer los destinos: {exc}")
        return
    devueltos, fallos = devolver(guardados, cuenta_mod, ids_actuales)
    if fallos:
        anotar("títulos de Restream", False,
               "; ".join(f"{identificador}: {error}"
                         for identificador, error in fallos))
    else:
        anotar("títulos de Restream", True,
               "devueltos: " + ", ".join(map(str, devueltos))
               if devueltos else "como estaban")
