# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Completar un config.ini viejo con lo que agrega la configuración de fábrica.

Una sola responsabilidad: agregar cada sección o clave ausente desde la
fuente canónica. No importa `config` (sería un ciclo), así que recibe
`guardar_opciones` por parámetro.
"""

from __future__ import annotations

from guyrapu.core import config_predeterminada
from guyrapu.core import diagnostico


logger = diagnostico.obtener_logger(__name__)


def completar_faltantes(parser, ruta, atajos_raw, guardar_opciones) -> None:
    """Agrega al INI lo que falte de la configuración de fábrica.

    Suma a `atajos_raw` los atajos que faltaban y deja en el registro la
    línea con los atajos nuevos."""
    # Migración genérica: agregar toda sección o clave ausente desde la fuente
    # canónica, preservando valores existentes incluso vacíos y claves desconocidas.
    _faltantes = [(s, c, v) for s, cs in config_predeterminada.datos().items()
                  for c, v in cs.items() if not parser.has_option(s, c)]
    guardar_opciones(ruta, _faltantes)
    _atajos_faltantes = [c for s, c, _v in _faltantes if s == "atajos"]
    for _sec, _clave, _valor_def in _faltantes:
        if _sec == "atajos":
            atajos_raw[_clave] = _valor_def
    if _atajos_faltantes:
        logger.info("Atajos nuevos añadidos a config.ini: %s", ", ".join(_atajos_faltantes))
