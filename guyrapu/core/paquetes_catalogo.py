# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Formato del catálogo de paquetes descargables, sin red ni disco.

La única razón de este módulo para cambiar es cómo se lee y se valida el
catálogo. Los tipos y los proveedores conocidos los pasa quien llama, para
no depender de `guyrapu/voice/`.
"""

from __future__ import annotations

import json
import re
from pathlib import PurePosixPath

from guyrapu.core.versiones import version_como_tupla


URL_CATALOGO = (
    "https://raw.githubusercontent.com/miguel-cinsfran/guyrapu-contenido/"
    "main/catalogo.json"
)
FORMATO = 1

_ID_RE = re.compile(r"^[a-z0-9-]+$")
_SHA_RE = re.compile(r"^[0-9a-fA-F]{64}$")
_UNIDAD_RE = re.compile(r"^[A-Za-z]:")


def _https(valor) -> bool:
    return isinstance(valor, str) and valor.lower().startswith("https://")


def _texto(valor) -> bool:
    return isinstance(valor, str) and bool(valor.strip())


def _entero(valor) -> bool:
    return isinstance(valor, int) and not isinstance(valor, bool)


def _ruta_valida(valor) -> bool:
    if not _texto(valor):
        return False
    if "\\" in valor or valor.startswith("/") or _UNIDAD_RE.match(valor):
        return False
    return ".." not in PurePosixPath(valor).parts


def _archivo_valido(archivo) -> bool:
    if not isinstance(archivo, dict):
        return False
    if not _https(archivo.get("url")):
        return False
    if not _entero(archivo.get("bytes")) or archivo["bytes"] < 0:
        return False
    if not isinstance(archivo.get("sha256"), str):
        return False
    if not _SHA_RE.match(archivo["sha256"]):
        return False
    return _ruta_valida(archivo.get("ruta"))


def _voz_valida(voz) -> bool:
    if not isinstance(voz, dict):
        return False
    if not _texto(voz.get("nombre")) or not _texto(voz.get("idioma")):
        return False
    if voz.get("genero") is not None and not isinstance(voz.get("genero"), str):
        return False
    if voz.get("muestra") is not None and not _https(voz.get("muestra")):
        return False
    archivo = voz.get("archivo")
    return archivo is None or _ruta_valida(archivo)


def _motivo(paquete, version_app, tipos, proveedores):
    if not isinstance(paquete, dict):
        return "el paquete no es un objeto"
    if not isinstance(paquete.get("id"), str) or not _ID_RE.match(paquete["id"]):
        return "el id del paquete no es válido"
    if paquete.get("tipo") not in tipos:
        return "el tipo del paquete no se conoce"
    if paquete.get("proveedor") not in proveedores:
        return "el proveedor del paquete no se conoce"
    for campo in ("nombre", "idioma", "licencia", "origen"):
        if not _texto(paquete.get(campo)):
            return f"el campo {campo} del paquete no es válido"
    if not _https(paquete.get("licencia_url")):
        return "la URL de la licencia del paquete no es https"
    if not _entero(paquete.get("version")) or paquete["version"] < 1:
        return "la versión del paquete no es válida"
    minima = version_como_tupla(paquete.get("guyrapu_minima"))
    if minima is None:
        return "la versión mínima de Guyrapu del paquete no es válida"
    actual = version_como_tupla(version_app)
    if actual is not None and minima > actual:
        return "el paquete pide una versión más nueva de Guyrapu"
    archivos = paquete.get("archivos")
    if not isinstance(archivos, list) or not archivos:
        return "el paquete no trae archivos"
    if any(not _archivo_valido(archivo) for archivo in archivos):
        return ("un archivo del paquete no es válido: la ruta, la URL https "
                "o el SHA-256 no sirven")
    voces = paquete.get("voces")
    if not isinstance(voces, list):
        return "las voces del paquete no son una lista"
    if any(not _voz_valida(voz) for voz in voces):
        return "una voz del paquete no es válida"
    return None


def _cargar(texto):
    if isinstance(texto, dict):
        return texto
    if not isinstance(texto, str):
        return None
    try:
        return json.loads(texto)
    except ValueError:
        return None


def _sin_repetidos(paquetes, descartes):
    vistos = {}
    for paquete in paquetes:
        vistos[paquete["id"]] = vistos.get(paquete["id"], 0) + 1
    repetidos = {identificador for identificador, cantidad in vistos.items()
                 if cantidad > 1}
    if not repetidos:
        return paquetes
    validos = []
    for paquete in paquetes:
        if paquete["id"] in repetidos:
            descartes.append(
                f"{paquete['id']}: el id del paquete está repetido")
        else:
            validos.append(paquete)
    return validos


def leer(texto, version_app, tipos, proveedores):
    """Devuelve los paquetes válidos y visibles y los motivos de los descartes."""
    datos = _cargar(texto)
    if not isinstance(datos, dict):
        return [], ["el catálogo no se reconoce"]
    formato = datos.get("formato")
    if _entero(formato) and formato > FORMATO:
        return [], ["el catálogo es de una versión más nueva de Guyrapu"]
    paquetes = datos.get("paquetes")
    if not isinstance(paquetes, list):
        return [], ["el catálogo no trae la lista de paquetes"]
    validos = []
    descartes = []
    for paquete in paquetes:
        motivo = _motivo(paquete, version_app, tipos, proveedores)
        if motivo is None:
            validos.append(paquete)
        else:
            identificador = paquete.get("id") if isinstance(paquete, dict) else "?"
            descartes.append(f"{identificador}: {motivo}")
    return _sin_repetidos(validos, descartes), descartes


def estado(paquete, instalado) -> str:
    """Estado de un paquete del catálogo frente a su ficha instalada."""
    if paquete is None:
        return "fuera_del_catalogo"
    if not isinstance(instalado, dict):
        return "sin_descargar"
    instalada = instalado.get("version")
    if _entero(instalada) and instalada < paquete["version"]:
        return "actualizable"
    return "instalado"
