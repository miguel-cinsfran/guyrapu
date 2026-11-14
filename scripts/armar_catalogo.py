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

PHONON = {
    "es": ("gradium/phonon-40m-es", "e5e052b26e31abd5918ade71d3135e69d51a66f8",
           "es-ES", "CC BY-NC 4.0", "Phonon español"),
    "pt": ("gradium/phonon-40m-pt", "4cbfd742a1555d60eb5399c6d296e9f2e07389e9",
           "pt-BR", "CC BY-NC 4.0", "Phonon portugués"),
    "en": ("gradium/phonon-31m-en", "92741c5b07d085ff840e26fea8ce43110b87852f",
           "en-US", "Apache 2.0", "Phonon inglés"),
}
VOCES_PHONON = ("gradium/phonon-voices",
                "0ee17205f254b5abc43b266c8a0f215565c352f7")
PIPER = ("rhasspy/piper-voices", "6b9cfaacb4fb2e02a9621227e3c1a48bec9710c3")
ARCHIVOS_MODELO = ("config.json", "model.q8.gguf", "tokenizer.json",
                   "default-voice.safetensors")
ORDEN_CALIDAD = {"high": 0, "medium": 1, "low": 2, "x_low": 3}
_NO_LIBRE = re.compile(r"\b(nc|non[- ]?commercial)\b", re.IGNORECASE)
_LICENCIA = re.compile(r"^\s*\*\s*License:\s*(.+)$", re.MULTILINE | re.IGNORECASE)
_LIBRES = ("public domain", "cc0", "cc by", "attribution", "apache",
           "unlicense", "licenses/by/", "licenses/by sa/", "publicdomain/")
_ENTRENAMIENTO = re.compile(r"^##\s+Training\s*$(.*?)(?=^##\s|\Z)", re.M | re.S | re.I)
_BASE_NO_LIBRE = re.compile(r"fine?[- ]?tuned from [^\n]*(lessac|ryan)", re.I)


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


def licencia_piper(nombre: str, texto: str) -> str | None:
    """La licencia de un MODEL_CARD si deja repartir la voz, o None."""
    if (nombre or "").strip().lower() == "lessac":
        return None
    if (nombre or "").strip().lower() == "jenny_dioco":
        return "See URL"
    encontrado = _LICENCIA.search(texto or "")
    if not encontrado:
        return None
    licencia = encontrado.group(1).strip()
    bajo = re.sub(r"[-_]+", " ", licencia.lower())
    if "see url" in bajo or "see license file" in bajo:
        return None
    if _NO_LIBRE.search(bajo):
        return None
    return licencia if any(clave in bajo for clave in _LIBRES) else None


def base_piper(texto: str, aceptadas=()) -> str | None:
    """Motivo por el que el modelo base no es libre, o None si lo es."""
    seccion = _ENTRENAMIENTO.search(texto or "")
    if seccion is None:
        return "base desconocida"
    base = seccion.group(1).lower()
    if no_libre := _BASE_NO_LIBRE.search(base):
        return "base no libre: " + no_libre.group(1)
    if any(clave in base for clave in ("scratch", "hifi_tts_92", "rdh", "brycebeattie.com")):
        return None
    if any(nombre in base for nombre in aceptadas):
        return None
    return "base desconocida"


def nombre_piper(nombre: str) -> str:
    return ("Jenny (Dioco)" if (nombre or "").lower() == "jenny_dioco"
            else str(nombre).replace("_", " ").title())


def _grupos_piper(voices: dict) -> dict:
    grupos = {}
    for entrada in voices.values():
        idioma = entrada.get("language") if isinstance(entrada, dict) else None
        if not isinstance(idioma, dict) or idioma.get("family") not in ("es", "en", "pt"):
            continue
        clave = (idioma.get("code"), entrada.get("name"))
        actual = grupos.get(clave)
        if (actual is None
                or ORDEN_CALIDAD.get(entrada.get("quality"), 99)
                < ORDEN_CALIDAD.get(actual.get("quality"), 99)):
            grupos[clave] = entrada
    return grupos


def _paquete(identificador, proveedor, nombre, idioma, licencia, origen,
             repo, voces, archivos) -> dict:
    return {
        "id": identificador,
        "tipo": "voz",
        "proveedor": proveedor,
        "nombre": nombre,
        "idioma": idioma,
        "version": 1,
        "guyrapu_minima": APP_VERSION,
        "licencia": licencia,
        "licencia_url": f"{BASE_HF}/{repo}",
        "origen": origen,
        "voces": voces,
        "archivos": archivos,
    }


def _paquete_piper(clave, entrada, metadatos, repo, revision,
                   descartes, aceptadas) -> dict | None:
    code, nombre = clave
    tarjeta = next((ruta for ruta in entrada.get("files") or {}
                    if ruta.endswith("MODEL_CARD")), None)
    texto = (pedir_texto(url_origen(repo, revision, tarjeta))
             if tarjeta else None)
    if (nombre or "").strip().lower() == "lessac":
        descartes.append((clave, "lessac"))
        return None
    licencia = licencia_piper(nombre, texto)
    motivo = ("licencia no permitida" if licencia is None
              else base_piper(texto, aceptadas))
    if motivo is not None:
        descartes.append((clave, motivo))
        return None
    pares = sorted(((ruta, Path(ruta).name)
                    for ruta in entrada.get("files") or {}
                    if ruta.endswith(".onnx") or ruta.endswith(".onnx.json")),
                   key=lambda par: par[1])
    archivos = [preparar_archivo(repo, revision, ruta, metadatos[ruta],
                                 CACHE, SUBIR) for ruta, _ in pares]
    calidad = entrada.get("quality")
    familia = str(code or "").split("_")[0]
    muestra = ("https://rhasspy.github.io/piper-samples/samples/"
               f"{familia}/{code}/{urllib.parse.quote(str(nombre), safe='')}/{calidad}/speaker_0.mp3")
    crudo = re.sub(r"[^a-z0-9-]+", "-",
                   f"{code}-{nombre}-{calidad}".lower())
    return _paquete(
        "piper-" + re.sub(r"-+", "-", crudo).strip("-"), "piper",
        f"Piper {nombre_piper(nombre)}",
        str(code or "").replace("_", "-"), licencia,
        f"Piper, {repo}, {entrada.get('key')}", repo,
        [{"nombre": nombre_piper(nombre),
          "idioma": str(code or "").replace("_", "-"), "genero": None,
          "muestra": muestra, "archivo": pares[0][1]}],
        archivos)


def paquetes_piper(token, descartes) -> list[dict]:
    repo, revision = PIPER
    with _abrir(url_origen(repo, revision, "voices.json"), token) as respuesta:
        voices = json.load(respuesta)
    metadatos = _arbol(repo, revision, token)
    entradas = []
    aceptadas = set()
    for clave, entrada in sorted(_grupos_piper(voices).items()):
        paquete = _paquete_piper(clave, entrada, metadatos, repo, revision,
                                 descartes, aceptadas)
        if paquete is not None:
            aceptadas.add(str(clave[1]).lower())
            entradas.append({"paquete": paquete, "repo": repo,
                             "revision": revision})
    return entradas


def _muestras(arbol: dict) -> dict:
    rutas = sorted((ruta for ruta in arbol if ruta.endswith(".ogg")),
                   reverse=True)
    return {ruta.rsplit("/", 1)[0].rsplit("_", 1)[-1]: ruta for ruta in rutas}


def _paquete_phonon(idioma, datos, voces, metadatos_modelo,
                    metadatos_voces, muestras) -> dict:
    repo, revision, idioma_app, licencia, nombre = datos
    archivos = [preparar_archivo(
        repo, revision, ruta, metadatos_modelo[ruta], CACHE, SUBIR,
        nombre=f"phonon-{idioma}-{Path(ruta).name}")
        for ruta in ARCHIVOS_MODELO]
    voces_paquete = []
    for voz in voces:
        ruta = voz.get("filename")
        if not isinstance(ruta, str) or ruta not in metadatos_voces:
            continue
        archivos.append(preparar_archivo(
            *VOCES_PHONON, ruta, metadatos_voces[ruta], CACHE, SUBIR))
        partes = str(voz.get("locale") or "").split("-")
        idioma_voz = ("-".join([partes[0].lower()]
                               + [parte.upper() for parte in partes[1:]])
                      if len(partes) > 1 else (voz.get("language") or ""))
        muestra = muestras.get(voz.get("voice_id"))
        voces_paquete.append({
            "nombre": str(voz.get("name") or "Voz"),
            "idioma": idioma_voz,
            "genero": voz.get("gender"),
            "muestra": (url_origen(*VOCES_PHONON, muestra)
                        if muestra else None),
            "archivo": ruta,
        })
    return _paquete(
        f"phonon-{idioma}", "phonon", nombre, idioma_app, licencia,
        f"Gradium, {repo}", repo, voces_paquete, archivos)


def paquetes_phonon(token) -> list[dict]:
    arbol_voces = _arbol(*VOCES_PHONON, token)
    texto = pedir_texto(url_origen(*VOCES_PHONON, "voices.jsonl"), token)
    voces = []
    for linea in texto.splitlines():
        try:
            voz = json.loads(linea)
        except ValueError:
            continue
        if isinstance(voz, dict) and voz.get("language") in PHONON:
            voces.append(voz)
    muestras = _muestras(arbol_voces)
    entradas = []
    for idioma, datos in PHONON.items():
        repo, revision = datos[0], datos[1]
        metadatos_modelo = _arbol(repo, revision, token)
        paquete = _paquete_phonon(
            idioma, datos, [voz for voz in voces
                            if voz.get("language") == idioma],
            metadatos_modelo, arbol_voces, muestras)
        entradas.append({"paquete": paquete, "repo": repo,
                         "revision": revision})
    return entradas


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
            f"  Más información: {paquete['licencia_url']}",
            f"  Repositorio: {BASE_HF}/{entrada['repo']}",
            f"  Revisión: {entrada['revision']}",
            "",
        ])
    (salida / "LICENCIAS.txt").write_text("\n".join(lineas),
                                          encoding="utf-8")


def main(argv) -> int:
    if len(argv) != 1:
        print("Uso: python scripts/armar_catalogo.py SALIDA", file=sys.stderr)
        return 1
    token = token_huggingface()
    if token is None:
        print("Falta el token de Hugging Face: los modelos phonon-40m-es y "
              "phonon-40m-pt lo piden.", file=sys.stderr)
        return 1
    descartes = []
    try:
        entradas = paquetes_phonon(token) + paquetes_piper(token, descartes)
    except (urllib.error.HTTPError, urllib.error.URLError, OSError,
            ValueError) as error:
        print(f"No se pudo armar el catálogo: {error}", file=sys.stderr)
        return 1
    escribir_catalogo(argv[0], entradas)
    for (code, nombre), motivo in descartes:
        print(f"Descartada {code} {nombre}: {motivo}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
