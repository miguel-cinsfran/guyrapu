# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Baja e instala paquetes descargables, en su carpeta junto al programa.

La única razón de este módulo para cambiar es cómo se baja y se guarda un
paquete. Cada tipo de paquete tiene su carpeta y cada paquete su ficha
`paquete.json` con lo que decía el catálogo más la fecha de instalación.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import NamedTuple

from guyrapu.core import paths
from guyrapu.core import red


logger = logging.getLogger(f"guyrapu.{__name__}")

_FICHA = "paquete.json"
_CARPETAS = {"voz": paths.carpeta_voces}


class ResultadoInstalacion(NamedTuple):
    correcta: bool
    motivo: str
    cancelada: bool = False


def _carpeta(tipo: str) -> Path:
    return _CARPETAS[tipo]()


def _borrar_si_existe(ruta: Path) -> None:
    try:
        if ruta.is_dir() and not ruta.is_symlink():
            shutil.rmtree(ruta)
        elif ruta.exists() or ruta.is_symlink():
            ruta.unlink()
    except OSError as error:
        logger.debug("no se pudo borrar %s: %s", ruta, error)


def _limpiar_restos(base: Path) -> None:
    for hijo in list(base.iterdir()):
        if (hijo.name.startswith(".")
                and (hijo.name.endswith(".descarga")
                     or hijo.name.endswith(".vieja"))):
            _borrar_si_existe(hijo)


def _leer_ficha(carpeta: Path) -> dict | None:
    try:
        ficha = json.loads((carpeta / _FICHA).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return ficha if isinstance(ficha, dict) else None


def instalados(tipo: str) -> list[dict]:
    """Las fichas de lo instalado para un tipo, sin catálogo ni red."""
    base = _carpeta(tipo)
    if not base.is_dir():
        return []
    _limpiar_restos(base)
    fichas = []
    for hijo in sorted(base.iterdir()):
        if hijo.name.startswith(".") or not hijo.is_dir():
            continue
        ficha = _leer_ficha(hijo)
        if ficha is None:
            logger.warning("no se pudo leer la ficha de %s", hijo)
            continue
        fichas.append(ficha)
    return fichas


def _sha256(ruta: Path) -> str:
    resumen = hashlib.sha256()
    with ruta.open("rb") as archivo:
        for bloque in iter(lambda: archivo.read(1024 * 1024), b""):
            resumen.update(bloque)
    return resumen.hexdigest().lower()


def _aviso_parcial(aviso, previos: int, tamanio: int, total: int):
    if aviso is None or not total:
        return None

    def avisar(porcentaje):
        if porcentaje is None:
            aviso(None)
            return
        hecho = previos + tamanio * porcentaje / 100
        aviso(min(100, max(0, int(hecho * 100 / total))))

    return avisar


def _bajar_archivo(archivo: dict, paso: Path, previos: int, total: int,
                   aviso, cancelar) -> None:
    destino = paso / archivo["ruta"]
    destino.parent.mkdir(parents=True, exist_ok=True)
    red.descargar_archivo(
        archivo["url"], destino,
        aviso=_aviso_parcial(aviso, previos, archivo["bytes"], total),
        cancelar=cancelar)
    if _sha256(destino) != archivo["sha256"].lower():
        raise OSError("la firma SHA-256 del archivo no coincide")
    if destino.stat().st_size != archivo["bytes"]:
        raise OSError("los bytes del archivo no coinciden con el catálogo")


def _reemplazar(base: Path, paso: Path, identificador: str) -> None:
    destino = base / identificador
    vieja = base / f".{identificador}.vieja"
    _borrar_si_existe(vieja)
    if destino.exists():
        os.replace(destino, vieja)
    try:
        os.replace(paso, destino)
    except OSError:
        if vieja.exists():
            os.replace(vieja, destino)
        raise
    _borrar_si_existe(vieja)


def _instalar_en(base: Path, paso: Path, paquete: dict,
                 aviso, cancelar) -> ResultadoInstalacion:
    archivos = paquete["archivos"]
    total = sum(archivo["bytes"] for archivo in archivos)
    necesario = total + total // 10
    if shutil.disk_usage(base).free < necesario:
        return ResultadoInstalacion(False, "no hay espacio suficiente")
    _borrar_si_existe(paso)
    paso.mkdir(parents=True)
    previos = 0
    for archivo in archivos:
        _bajar_archivo(archivo, paso, previos, total, aviso, cancelar)
        previos += archivo["bytes"]
    ficha = dict(paquete)
    ficha["instalado"] = datetime.now().astimezone().isoformat(timespec="seconds")
    (paso / _FICHA).write_text(
        json.dumps(ficha, ensure_ascii=False, indent=2), encoding="utf-8")
    _reemplazar(base, paso, paquete["id"])
    return ResultadoInstalacion(True, "paquete instalado")


def instalar(paquete: dict, aviso=None, cancelar=None) -> ResultadoInstalacion:
    """Baja y verifica todos los archivos; deja el paquete entero o nada."""
    try:
        base = _carpeta(paquete["tipo"])
        base.mkdir(parents=True, exist_ok=True)
    except (KeyError, OSError) as error:
        return ResultadoInstalacion(False, f"no se pudo preparar la carpeta: {error}")
    paso = base / f".{paquete['id']}.descarga"
    try:
        return _instalar_en(base, paso, paquete, aviso, cancelar)
    except red.DescargaCancelada:
        return ResultadoInstalacion(False, "instalación cancelada", True)
    except OSError as error:
        return ResultadoInstalacion(False, f"no se pudo instalar: {error}")
    finally:
        _borrar_si_existe(paso)


def borrar(identificador: str, tipo: str) -> ResultadoInstalacion:
    """Quita la carpeta del paquete; si no se puede, devuelve el motivo."""
    try:
        destino = _carpeta(tipo) / identificador
        if destino.exists():
            shutil.rmtree(destino)
    except OSError as error:
        return ResultadoInstalacion(False, f"no se pudo borrar: {error}")
    return ResultadoInstalacion(True, "paquete borrado")
