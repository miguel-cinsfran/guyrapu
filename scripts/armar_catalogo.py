#!/usr/bin/env python
# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Arma el catálogo de paquetes de voces desde revisiones fijas de Hugging Face.

Se corre con `python scripts/armar_catalogo.py SALIDA`. Escribe
`SALIDA/catalogo.json` y `SALIDA/LICENCIAS.txt`. Lo que exige cuenta en
Hugging Face queda en `.cache-voces/subir/` para subirlo a mano a
`guyrapu-contenido`. No sube nada ni toca ningún repositorio.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

# Raíz del repositorio: la carpeta de arriba de la suya.
RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from guyrapu.core.config import APP_VERSION, USER_AGENT  # noqa: E402


URL_CONTENIDO = "https://github.com/miguel-cinsfran/guyrapu-contenido"
URL_SUBIR = URL_CONTENIDO + "/releases/download/modelos-1/"
BASE_HF = "https://huggingface.co"
CACHE = RAIZ / ".cache-voces"
TIEMPO_ESPERA = 60
SUBIR = CACHE / "subir"


def token_huggingface() -> str | None:
    valor = os.environ.get("HF_TOKEN")
    if isinstance(valor, str) and valor.strip():
        return valor.strip()
    ruta = Path.home() / ".cache" / "huggingface" / "token"
    try:
        return ruta.read_text(encoding="utf-8").strip() or None
    except OSError:
        return None


def _abrir(url: str, token: str | None = None, metodo: str | None = None):
    cabeceras = {"User-Agent": USER_AGENT}
    if token and urllib.parse.urlsplit(url).hostname == "huggingface.co":
        cabeceras["Authorization"] = "Bearer " + token
    peticion = urllib.request.Request(url, headers=cabeceras, method=metodo)
    return urllib.request.urlopen(peticion, timeout=TIEMPO_ESPERA)


def pedir_texto(url: str, token: str | None = None) -> str:
    with _abrir(url, token) as respuesta:
        return respuesta.read().decode("utf-8", "replace")


def pide_cuenta(url: str) -> bool:
    """Verdadero si el archivo exige cuenta, con una petición sin token."""
    try:
        with _abrir(url, metodo="HEAD"):
            return False
    except urllib.error.HTTPError as error:
        if error.code in (401, 403):
            return True
        raise


def descargar(url: str, destino: Path, token: str | None = None) -> None:
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    with _abrir(url, token) as respuesta, destino.open("wb") as archivo:
        shutil.copyfileobj(respuesta, archivo, 1024 * 1024)


def sha256(ruta: Path) -> str:
    with Path(ruta).open("rb") as archivo:
        return hashlib.file_digest(archivo, "sha256").hexdigest().lower()


def url_origen(repo: str, revision: str, ruta: str) -> str:
    return f"{BASE_HF}/{repo}/resolve/{revision}/{urllib.parse.quote(ruta, safe='/')}"


def _archivo(url: str, destino: Path, ruta: str,
             esperado: str | None) -> dict:
    calculado = sha256(destino)
    if esperado is not None and calculado != esperado:
        raise SystemExit(
            f"el SHA-256 de {ruta} no coincide: calculado {calculado}, "
            f"publicado {esperado}")
    return {"url": url, "bytes": destino.stat().st_size,
            "sha256": calculado, "ruta": ruta}


def preparar_archivo(repo, revision, ruta, metadatos, cache, subir,
                     nombre=None) -> dict:
    """Decide la URL de un archivo: el origen o la release de contenido."""
    url = url_origen(repo, revision, ruta)
    lfs = metadatos.get("lfs") if isinstance(metadatos, dict) else None
    esperado = (lfs.get("sha256") or lfs.get("oid")) if isinstance(lfs, dict) else None  # SHA-256 del LFS
    if pide_cuenta(url):
        destino = Path(subir) / (nombre or Path(ruta).name)
        if not (destino.is_file() and (esperado is None
                                      or sha256(destino) == esperado)):
            descargar(url, destino, token_huggingface())
        return _archivo(URL_SUBIR + destino.name, destino, ruta, esperado)
    if esperado is not None:
        return {"url": url, "bytes": int(metadatos["size"]),
                "sha256": esperado, "ruta": ruta}
    destino = Path(cache) / repo.replace("/", "__") / ruta
    if not destino.is_file():
        descargar(url, destino)
    return _archivo(url, destino, ruta, None)


def _arbol(repo: str, revision: str, token: str | None) -> dict:
    url = (f"{BASE_HF}/api/models/{repo}/tree/{revision}"
           "?recursive=true&limit=1000")
    entradas = {}
    while url:
        with _abrir(url, token) as respuesta:
            datos = json.load(respuesta)
            enlace = respuesta.headers.get("Link")
        for entrada in datos:
            if (isinstance(entrada, dict) and entrada.get("type") == "file"
                    and isinstance(entrada.get("path"), str)):
                entradas[entrada["path"]] = entrada
        siguiente = re.search(r'<([^>]+)>;\s*rel="next"', enlace or "")
        url = siguiente.group(1) if siguiente else None
    return entradas


def _paquete(identificador, proveedor, nombre, idioma, licencia, origen,
             repo, voces, archivos, enlace=None) -> dict:
    return {
        "id": identificador,
        "tipo": "voz",
        "proveedor": proveedor,
        "nombre": nombre,
        "idioma": idioma,
        "version": 1,
        "guyrapu_minima": APP_VERSION,
        "licencia": licencia,
        "licencia_url": enlace or f"{BASE_HF}/{repo}",
        "origen": origen,
        "voces": voces,
        "archivos": archivos,
    }


def escribir_catalogo(salida, entradas) -> None:
    salida = Path(salida)
    salida.mkdir(parents=True, exist_ok=True)
    paquetes = sorted((entrada["paquete"] for entrada in entradas),
                      key=lambda paquete: (paquete["proveedor"],
                                           paquete["idioma"],
                                           paquete["id"]))
    (salida / "catalogo.json").write_text(
        json.dumps({"formato": 1, "paquetes": paquetes},
                   ensure_ascii=False, indent=2),
        encoding="utf-8")
    lineas = []
    for entrada in sorted(entradas, key=lambda e: e["paquete"]["id"]):
        paquete = entrada["paquete"]
        lineas.extend([
            f"{paquete['nombre']} ({paquete['id']})",
            f"  Origen: {paquete['origen']}",
            f"  Licencia: {paquete['licencia']}",
            f"  Uso: {paquete.get('uso', 'libre')}",
            f"  Más información: {paquete['licencia_url']}",
            f"  Repositorio: {BASE_HF}/{entrada['repo']}",
            f"  Revisión: {entrada['revision']}",
            "",
        ])
    (salida / "LICENCIAS.txt").write_text("\n".join(lineas),
                                          encoding="utf-8")


# Las fuentes importan estas funciones comunes: importarlas aquí, después de
# definirlas, evita el ciclo cuando se carga una fuente antes que este módulo.
from scripts import fuente_phonon, fuente_piper  # noqa: E402

FUENTES = (fuente_phonon, fuente_piper)


def main(argv) -> int:
    if len(argv) != 1:
        print("Uso: python scripts/armar_catalogo.py SALIDA", file=sys.stderr)
        return 1
    token = token_huggingface()
    if token is None:
        print("Falta el token de Hugging Face: los modelos phonon-40m-es y "
              "phonon-40m-pt lo piden.", file=sys.stderr)
        return 1
    try:
        entradas = []
        for fuente in FUENTES:
            entradas.extend(fuente.paquetes(token))
    except (urllib.error.HTTPError, urllib.error.URLError, OSError,
            ValueError) as error:
        print(f"No se pudo armar el catálogo: {error}", file=sys.stderr)
        return 1
    escribir_catalogo(argv[0], entradas)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
