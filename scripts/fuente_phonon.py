#!/usr/bin/env python
# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Fuente de las voces de Phonon para el catálogo.

La única razón de este módulo para cambiar es cómo se leen las voces de
Phonon de su revisión fija de Hugging Face. Lo común de descarga y
escritura sigue en `armar_catalogo.py`.
"""

from __future__ import annotations

import json
from pathlib import Path

from scripts import armar_catalogo

ID = "phonon"

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
ARCHIVOS_MODELO = ("config.json", "model.q8.gguf", "tokenizer.json",
                   "default-voice.safetensors")


def _muestras(arbol: dict) -> dict:
    clips = sorted((ruta for ruta in arbol if ruta.endswith(".ogg")),
                   key=lambda ruta: (-arbol[ruta].get("size", 0), ruta))
    return {ruta.rsplit("/", 1)[0].rsplit("_", 1)[-1]: ruta for ruta in reversed(clips)}


def _paquete_phonon(idioma, datos, voces, metadatos_modelo,
                    metadatos_voces, muestras) -> dict:
    repo, revision, idioma_app, licencia, nombre = datos
    base = armar_catalogo
    archivos = [base.preparar_archivo(
        repo, revision, ruta, metadatos_modelo[ruta], base.CACHE, base.SUBIR,
        nombre=f"phonon-{idioma}-{Path(ruta).name}")
        for ruta in ARCHIVOS_MODELO]
    voces_paquete = []
    for voz in voces:
        ruta = voz.get("filename")
        if not isinstance(ruta, str) or ruta not in metadatos_voces:
            continue
        archivos.append(base.preparar_archivo(
            *VOCES_PHONON, ruta, metadatos_voces[ruta], base.CACHE, base.SUBIR))
        partes = str(voz.get("locale") or "").split("-")
        idioma_voz = ("-".join([partes[0].lower()]
                               + [parte.upper() for parte in partes[1:]])
                      if len(partes) > 1 else (voz.get("language") or ""))
        muestra = muestras.get(voz.get("voice_id"))
        voces_paquete.append({
            "nombre": str(voz.get("name") or "Voz"),
            "idioma": idioma_voz,
            "genero": voz.get("gender"),
            "muestra": (base.url_origen(*VOCES_PHONON, muestra)
                        if muestra else None),
            "archivo": ruta,
        })
    return base._paquete(
        f"phonon-{idioma}", ID, nombre, idioma_app, licencia,
        f"Gradium, {repo}", repo, voces_paquete, archivos)


def paquetes(token) -> list[dict]:
    base = armar_catalogo
    arbol_voces = base._arbol(*VOCES_PHONON, token)
    texto = base.pedir_texto(base.url_origen(*VOCES_PHONON, "voices.jsonl"), token)
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
        metadatos_modelo = base._arbol(repo, revision, token)
        paquete = _paquete_phonon(
            idioma, datos, [voz for voz in voces
                            if voz.get("language") == idioma],
            metadatos_modelo, arbol_voces, muestras)
        entradas.append({"paquete": paquete, "repo": repo,
                         "revision": revision})
    return entradas
