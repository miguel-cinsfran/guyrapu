# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""El instalador corre desde la carpeta del paquete nuevo, no desde la
instalación: por eso cada ruta tiene su variante `..._en(instalacion)`
que arma la misma ruta relativa a la instalación recibida por argumento.
Las sin sufijo llaman a esas con `carpeta_instalacion()`.
"""

from __future__ import annotations

from pathlib import Path

from guyrapu.core import paths


def carpeta_actualizacion_en(instalacion: Path) -> Path:
    return Path(instalacion) / "data" / "actualizacion"


def paquete_descargado_en(instalacion: Path) -> Path:
    return carpeta_actualizacion_en(instalacion) / "paquete.zip"


def paquete_descargado() -> Path:
    return paquete_descargado_en(paths.carpeta_instalacion())


def paquete_extraido_en(instalacion: Path) -> Path:
    return carpeta_actualizacion_en(instalacion) / "nueva"


def paquete_extraido() -> Path:
    return paquete_extraido_en(paths.carpeta_instalacion())


def respaldo_actualizacion_en(instalacion: Path) -> Path:
    return carpeta_actualizacion_en(instalacion) / "respaldo"


def actualizacion_pendiente_en(instalacion: Path) -> Path:
    return carpeta_actualizacion_en(instalacion) / "pendiente.json"


def arranque_confirmado_en(instalacion: Path) -> Path:
    return carpeta_actualizacion_en(instalacion) / "arranque-ok"


def resultado_actualizacion_en(instalacion: Path) -> Path:
    return carpeta_actualizacion_en(instalacion) / "resultado.json"


def registro_actualizacion_en(instalacion: Path) -> Path:
    return carpeta_actualizacion_en(instalacion) / "registro.log"
