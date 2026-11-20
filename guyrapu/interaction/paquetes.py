# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Paquetes .zip para compartir estilos, avisos y comandos entre personas.

Puro y sin wx. Única razón para cambiar: el formato del paquete y sus
defensas ante un archivo que llega de otra persona. No conoce qué hay
dentro de los elementos: solo los guarda y los devuelve.
"""

from __future__ import annotations

import json
import os
import zipfile
import zlib
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from guyrapu.core.config import APP_NAME
from guyrapu.core.idioma import _, N_


FORMATO = 1

# Traductores: tipos de contenido que se pueden compartir en un paquete.
TIPOS = (
    ("estilos", N_("estilos")),
    ("avisos", N_("avisos")),
    ("comandos", N_("comandos")),
    ("encuestas", N_("encuestas")),
    ("medios", N_("medios")),
)

_MANIFIESTO = "manifiesto.json"
_DATOS = "datos.json"
_CARPETA = "archivos/"
_ERRORES_DE_LECTURA = (KeyError, zipfile.BadZipFile, OSError, EOFError,
                       RuntimeError, NotImplementedError, ValueError,
                       zlib.error)


class PaqueteRechazado(Exception):
    """El paquete no se puede importar. El texto ya está traducido."""


@dataclass(frozen=True)
class Paquete:
    """Lo que trae un paquete leído: su tipo, sus elementos y sus archivos."""

    tipo: str
    elementos: list
    archivos: tuple[str, ...]


def _parece_zip(ruta) -> bool:
    try:
        with open(ruta, "rb") as archivo:
            return archivo.read(4).startswith(b"PK")
    except OSError:
        return False


def _abrir(ruta):
    try:
        return zipfile.ZipFile(ruta)
    except zipfile.BadZipFile as error:
        if _parece_zip(ruta):
            raise PaqueteRechazado(
                _("El paquete está dañado y no se puede leer.")) from error
        raise PaqueteRechazado(
            _("El archivo no es un paquete de Guyrapu.")) from error
    except NotImplementedError as error:
        raise PaqueteRechazado(
            _("El paquete está dañado y no se puede leer.")) from error
    except OSError as error:
        raise PaqueteRechazado(
            _("El archivo no es un paquete de Guyrapu.")) from error


def _leer_json(archivo, nombre):
    try:
        return json.loads(archivo.read(nombre).decode("utf-8"))
    except _ERRORES_DE_LECTURA as error:
        raise PaqueteRechazado(
            _("El paquete está dañado y no se puede leer.")) from error


def _ruta_prohibida(nombre: str) -> bool:
    if "\\" in nombre or nombre.startswith("/"):
        return True
    if len(nombre) >= 2 and nombre[1] == ":" and nombre[0].isalpha():
        return True
    return ".." in PurePosixPath(nombre).parts


def _con_punto(extension: str) -> str:
    if not extension:
        return ""
    return extension if extension.startswith(".") else "." + extension


def _rechazar_archivo(nombre: str) -> None:
    motivo = _("El paquete contiene un archivo que Guyrapu no importa: "
               "{nombre}.")
    raise PaqueteRechazado(motivo.format(nombre=nombre))


def _validar_entradas(entradas, extensiones) -> None:
    permitidas = None
    if extensiones:
        permitidas = {_con_punto(str(extension)).lower()
                      for extension in extensiones}
    for info in entradas:
        nombre = info.orig_filename
        if _ruta_prohibida(nombre):
            _rechazar_archivo(nombre)
        if nombre in (_MANIFIESTO, _DATOS):
            continue
        if nombre == _CARPETA:
            if not info.is_dir():
                _rechazar_archivo(nombre)
            continue
        if not nombre.startswith(_CARPETA):
            _rechazar_archivo(nombre)
        resto = nombre[len(_CARPETA):]
        if (not resto or "/" in resto or info.is_dir()
                or resto in (".", "..")):
            _rechazar_archivo(nombre)
        if (permitidas is not None
                and PurePosixPath(resto).suffix.lower() not in permitidas):
            _rechazar_archivo(nombre)


def _medir(archivo, entradas, tope_mb) -> None:
    limite = int(tope_mb) * 1024 * 1024
    total = 0
    try:
        for info in entradas:
            if info.is_dir():
                continue
            with archivo.open(info) as origen:
                while True:
                    bloque = origen.read(1024 * 1024)
                    if not bloque:
                        break
                    total += len(bloque)
                    if total > limite:
                        raise PaqueteRechazado(
                            _("El paquete supera el tamaño máximo de "
                              "{megas} MB.").format(megas=tope_mb))
    except _ERRORES_DE_LECTURA as error:
        raise PaqueteRechazado(
            _("El paquete está dañado y no se puede leer.")) from error


def _nombre_de_tipo(clave):
    for clave_tipo, nombre in TIPOS:
        if clave_tipo == clave:
            return _(nombre)
    return clave


def _elemento_valido(elemento) -> bool:
    return (isinstance(elemento, dict)
            and isinstance(elemento.get("nombre"), str))


def leer(ruta, tipo, extensiones=(), tope_mb=50) -> Paquete:
    """Lee un paquete y devuelve sus elementos y los nombres de sus archivos.

    Rechaza el paquete entero con `PaqueteRechazado` si no es un paquete,
    si es de otra versión o de otro tipo, si está dañado, si supera el
    tope descomprimido o si trae una ruta o una extensión que no se
    importa. Con `extensiones` vacía no se limita la extensión.
    """
    archivo = _abrir(ruta)
    with archivo:
        entradas = archivo.infolist()
        if _MANIFIESTO not in {info.filename for info in entradas}:
            raise PaqueteRechazado(
                _("El archivo no es un paquete de Guyrapu."))
        _validar_entradas(entradas, extensiones)
        _medir(archivo, entradas, tope_mb)
        manifiesto = _leer_json(archivo, _MANIFIESTO)
        if not isinstance(manifiesto, dict):
            raise PaqueteRechazado(
                _("El paquete está dañado y no se puede leer."))
        formato = manifiesto.get("formato")
        if not isinstance(formato, int) or isinstance(formato, bool):
            raise PaqueteRechazado(
                _("El paquete está dañado y no se puede leer."))
        if formato > FORMATO:
            raise PaqueteRechazado(
                _("El paquete es de una versión posterior de Guyrapu. "
                  "Actualiza Guyrapu para importarlo."))
        tipo_paquete = manifiesto.get("tipo")
        if not isinstance(tipo_paquete, str):
            raise PaqueteRechazado(
                _("El paquete está dañado y no se puede leer."))
        if tipo_paquete != tipo:
            raise PaqueteRechazado(
                _("El paquete contiene {contiene}, no {esperado}.").format(
                    contiene=_nombre_de_tipo(tipo_paquete),
                    esperado=_nombre_de_tipo(tipo)))
        datos = _leer_json(archivo, _DATOS)
        if not isinstance(datos, list) or not all(
                _elemento_valido(elemento) for elemento in datos):
            raise PaqueteRechazado(
                _("El paquete está dañado y no se puede leer."))
        archivos = tuple(
            info.orig_filename[len(_CARPETA):]
            for info in entradas
            if not info.is_dir() and info.orig_filename.startswith(_CARPETA))
        return Paquete(tipo_paquete, datos, archivos)


def exportar(ruta, tipo, elementos, archivos=()) -> None:
    """Escribe un paquete con su manifiesto, sus elementos y sus archivos.

    Escribe a un temporal al lado y lo renombra con `os.replace`: si algo
    falla a mitad, el archivo anterior con ese nombre queda intacto.
    """
    ruta = Path(ruta)
    temporal = ruta.with_suffix(ruta.suffix + ".tmp")
    manifiesto = {
        "formato": FORMATO,
        "tipo": tipo,
        "cantidad": len(elementos),
        "app": APP_NAME,
    }
    try:
        with zipfile.ZipFile(temporal, "w", zipfile.ZIP_DEFLATED) as archivo:
            archivo.writestr(_MANIFIESTO,
                             json.dumps(manifiesto, ensure_ascii=False))
            archivo.writestr(_DATOS,
                             json.dumps(elementos, ensure_ascii=False))
            for nombre in archivos:
                archivo_origen = Path(nombre)
                archivo.write(archivo_origen,
                              _CARPETA + archivo_origen.name)
        os.replace(temporal, ruta)
    except BaseException:
        try:
            os.unlink(temporal)
        except OSError:
            pass
        raise


def repetidos(elementos, existentes) -> list:
    """Los nombres del paquete que ya existen, sin distinguir mayúsculas ni
    espacios en los extremos.

    `existentes` puede traer nombres o elementos con nombre.
    """
    ya = {(item["nombre"] if isinstance(item, dict)
           else getattr(item, "nombre", item)).strip().casefold()
          for item in existentes}
    return [elemento["nombre"] for elemento in elementos
            if elemento["nombre"].strip().casefold() in ya]


def _nombre_dentro(nombre: str) -> str:
    limpio = Path(nombre).name
    if not limpio or limpio in (".", ".."):
        _rechazar_archivo(nombre)
    return limpio


def _nombre_libre(carpeta: Path, nombre: str, contenido: bytes) -> str:
    ruta = carpeta / nombre
    if not ruta.exists():
        return nombre
    if ruta.is_file() and ruta.read_bytes() == contenido:
        return nombre
    base = Path(nombre)
    numero = 2
    while True:
        candidato = f"{base.stem} ({numero}){base.suffix}"
        ruta = carpeta / candidato
        if not ruta.exists():
            return candidato
        if ruta.is_file() and ruta.read_bytes() == contenido:
            return candidato
        numero += 1


def extraer_archivos(ruta, paquete, carpeta) -> dict:
    """Escribe los archivos del paquete dentro de `carpeta`, sin abrirlos.

    Devuelve, por cada nombre del paquete, el nombre con que quedó. Reusa
    el archivo que ya tiene el mismo contenido y numera el que no.
    """
    carpeta = Path(carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)
    destinos = {}
    with zipfile.ZipFile(ruta) as archivo:
        for nombre in paquete.archivos:
            contenido = archivo.read(_CARPETA + nombre)
            final = _nombre_libre(carpeta, _nombre_dentro(nombre), contenido)
            (carpeta / final).write_bytes(contenido)
            destinos[nombre] = final
    return destinos
