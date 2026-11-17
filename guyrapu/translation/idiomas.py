# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""El nombre y la sigla de un idioma a partir de su código.

Puro: lee la tabla que genera `scripts/generar_nombres_idiomas.py` y no
importa Babel. Su única razón para cambiar es cómo se nombra un idioma.
"""

from __future__ import annotations

import json
from pathlib import Path

from guyrapu.core.idioma import _, idioma_actual

_RUTA = Path(__file__).with_name("nombres_idiomas.json")
_TABLA = None


def _tabla() -> dict:
    global _TABLA
    if _TABLA is None:
        _TABLA = json.loads(_RUTA.read_text(encoding="utf-8"))
    return _TABLA


def base(codigo) -> str:
    """La parte de idioma de un código ISO, sin la región."""
    return (codigo or "").replace("_", "-").split("-")[0].lower()


def nombre(codigo, idioma=None):
    """El nombre del idioma en el idioma pedido, o None si no está en la tabla."""
    datos = _tabla().get(base(codigo))
    if not datos:
        return None
    return datos.get("en" if (idioma or idioma_actual()) == "en" else "es")


def sigla(codigo) -> str:
    """El código del idioma en mayúsculas."""
    return base(codigo).upper()


def sufijo(codigo, idioma=None) -> str:
    """La frase que dice de qué idioma salió: «del inglés» o «from English»."""
    nombre_ = nombre(codigo, idioma)
    if not nombre_:
        return ""
    if (idioma or idioma_actual()) == "en":
        return f"from {nombre_}"
    return f"del {nombre_}"


def mencion(codigo, forma="completo", voz=False, idioma=None) -> str:
    """Lo que se agrega al mensaje para decir su idioma original."""
    if forma == "no" or not codigo:
        return ""
    nombre_ = nombre(codigo, idioma)
    if forma == "abreviado" or not nombre_:
        return f" ({sigla(codigo)})"
    if voz:
        return f", {sufijo(codigo, idioma)}"
    return f" ({sufijo(codigo, idioma)})"


def destino(config) -> str:
    """El código de idioma al que se traduce, según la configuración."""
    elegido = str(config.get("traducir_destino") or "interfaz").strip()
    if elegido.lower() in ("", "interfaz"):
        return idioma_actual()
    return elegido


def opciones() -> list[tuple[str, str]]:
    """Pares (código, nombre) para elegir el idioma destino."""
    idioma = "en" if idioma_actual() == "en" else "es"
    pares = [("interfaz", _("Idioma de la interfaz"))]
    pares.extend(sorted(((codigo, datos[idioma])
                         for codigo, datos in _tabla().items()),
                        key=lambda par: par[1]))
    return pares
