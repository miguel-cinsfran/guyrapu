#!/usr/bin/env python
# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Fuente de las voces de Piper para el catálogo.

La única razón de este módulo para cambiar es cómo se leen las voces de
Piper de su revisión fija de Hugging Face. Lo común de descarga y escritura
sigue en `armar_catalogo.py`.
"""

from __future__ import annotations

import json
import re
import urllib.parse
from pathlib import Path

from scripts import armar_catalogo
from scripts import uso_voces

ID = "piper"

PIPER = ("rhasspy/piper-voices", "6b9cfaacb4fb2e02a9621227e3c1a48bec9710c3")
ORDEN_CALIDAD = {"high": 0, "medium": 1, "low": 2, "x_low": 3}
VERSION_AVISO_USO = "3.0.0-beta.6"
MAX_HABLANTES = 25
URL_JENNY = "https://github.com/dioco-group/jenny-tts-dataset"


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


def _voces_piper(nombre, idioma, muestra, archivo, hablantes):
    mapa = hablantes if isinstance(hablantes, dict) else {}
    pares = sorted(((str(clave), int(valor)) for clave, valor in mapa.items()
                    if isinstance(valor, int)), key=lambda par: par[1])
    modelo = nombre_piper(nombre)
    comun = {"idioma": idioma, "muestra": muestra, "archivo": archivo}
    if not 2 <= len(pares) <= MAX_HABLANTES:
        return [dict(comun, nombre=modelo, genero=None)]
    generos = ({"M": "male", "F": "female"}
               if {clave for clave, _ in pares} == {"M", "F"} else {})
    voces = []
    for clave, hablante in pares:
        if generos:
            voz = dict(comun, nombre=modelo, genero=generos[clave])
        else:
            voz = dict(comun, nombre=f"{modelo} {clave}", genero=None)
        voz["hablante"] = hablante
        voces.append(voz)
    return voces


def _paquete_piper(clave, entrada, metadatos, repo, revision) -> dict:
    code, nombre = clave
    base = armar_catalogo
    tarjeta = next((ruta for ruta in entrada.get("files") or {}
                    if ruta.endswith("MODEL_CARD")), None)
    texto = (base.pedir_texto(base.url_origen(repo, revision, tarjeta))
             if tarjeta else None)
    licencia = uso_voces.licencia(nombre, texto)
    categoria = uso_voces.uso(nombre, texto)
    enlace = (URL_JENNY if nombre_piper(nombre) == "Jenny (Dioco)"
              else f"{base.BASE_HF}/{repo}/blob/{revision}/{tarjeta}")
    pares = sorted(((ruta, Path(ruta).name)
                    for ruta in entrada.get("files") or {}
                    if ruta.endswith(".onnx") or ruta.endswith(".onnx.json")),
                   key=lambda par: par[1])
    archivos = [base.preparar_archivo(repo, revision, ruta, metadatos[ruta],
                                      base.CACHE, base.SUBIR)
                for ruta, _ in pares]
    calidad = entrada.get("quality")
    familia = str(code or "").split("_")[0]
    muestra = ("https://rhasspy.github.io/piper-samples/samples/"
               f"{familia}/{code}/{urllib.parse.quote(str(nombre), safe='')}/"
               f"{calidad}/speaker_0.mp3")
    crudo = re.sub(r"[^a-z0-9-]+", "-",
                   f"{code}-{nombre}-{calidad}".lower())
    idioma = str(code or "").replace("_", "-")
    paquete = base._paquete(
        "piper-" + re.sub(r"-+", "-", crudo).strip("-"), ID,
        f"Piper {nombre_piper(nombre)}", idioma, licencia,
        f"Piper, {repo}, {entrada.get('key')}", repo,
        _voces_piper(nombre, idioma, muestra, pares[0][1],
                     entrada.get("speaker_id_map")),
        archivos, enlace)
    paquete["uso"] = categoria
    if categoria != uso_voces.LIBRE:
        paquete["guyrapu_minima"] = VERSION_AVISO_USO
    return paquete


def paquetes(token) -> list[dict]:
    base = armar_catalogo
    repo, revision = PIPER
    with base._abrir(base.url_origen(repo, revision, "voices.json"), token) as respuesta:
        voices = json.load(respuesta)
    metadatos = base._arbol(repo, revision, token)
    entradas = []
    for clave, entrada in sorted(_grupos_piper(voices).items()):
        paquete = _paquete_piper(clave, entrada, metadatos, repo, revision)
        entradas.append({"paquete": paquete, "repo": repo,
                         "revision": revision})
    return entradas
