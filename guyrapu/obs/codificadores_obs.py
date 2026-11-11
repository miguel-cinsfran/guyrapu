# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Los codificadores de vídeo H.264 que tiene la PC, según el registro de OBS.

El WebSocket no lista los codificadores disponibles. El último registro de
OBS trae, al arrancar, un bloque «Available Encoders:» con sus líneas
«- id (nombre)». Solo interesan los H.264 porque YouTube y TikTok por RTMP
lo piden. Sin registro legible se ofrece x264, que viene con OBS.
"""

from __future__ import annotations

import json
from pathlib import Path

from guyrapu.core import diagnostico, paths
from guyrapu.obs import perfil_en_disco

logger = diagnostico.obtener_logger(__name__)

_BITRATE_POR_DEFECTO = 2500

CODIFICADOR_POR_ID = {
    "obs_x264": "x264",
    "obs_qsv11_v2": "qsv",
    "obs_qsv11": "qsv",
    "obs_nvenc_h264_tex": "nvenc",
    "jim_nvenc": "nvenc",
    "ffmpeg_nvenc": "nvenc",
    "h264_texture_amf": "amd",
    "amd_amf_h264": "amd",
}
PRIORIDAD = ("nvenc", "qsv", "amd", "x264")
_INICIO_VIDEO = "Video" + " Encoders:"
_FIN_VIDEO = "Audio" + " Encoders:"


def codificador_simple(identificador) -> str:
    """El nombre del modo Sencillo para un id de OBS; x264 si no se conoce."""
    return CODIFICADOR_POR_ID.get(
        str(identificador or "").strip().lower(), "x264")


def _identificador(linea) -> str:
    texto = linea.strip()
    # La línea del registro lleva delante la hora: «10:55:13.696: \t- id».
    posicion = texto.find("- ")
    if posicion < 0:
        return ""
    return texto[posicion + 2:].split(" (", 1)[0].strip().lower()


def leer_codificadores(texto) -> tuple:
    """Los H.264 del bloque de codificadores de vídeo, en orden de preferencia."""
    encontrados = set()
    en_video = False
    for linea in str(texto or "").splitlines():
        if _INICIO_VIDEO in linea:
            en_video = True
            continue
        if _FIN_VIDEO in linea:
            en_video = False
            continue
        if not en_video:
            continue
        identificador = _identificador(linea)
        if identificador in CODIFICADOR_POR_ID:
            encontrados.add(CODIFICADOR_POR_ID[identificador])
    if not encontrados:
        return ("x264",)
    return tuple(nombre for nombre in PRIORIDAD if nombre in encontrados)


def _ultimo_registro(carpeta):
    try:
        registros = sorted(Path(carpeta).glob("*.txt"))
    except OSError:
        return None
    return registros[-1] if registros else None


def codificadores_disponibles(carpeta=None) -> tuple:
    """Lee el último registro de OBS; sin uno legible devuelve solo x264."""
    ruta = _ultimo_registro(carpeta if carpeta is not None
                            else paths.carpeta_obs("registros"))
    if ruta is None:
        return ("x264",)
    try:
        texto = ruta.read_text(encoding="utf-8", errors="replace")
    except OSError as error:
        logger.debug("no se pudo leer el registro de OBS %s: %s", ruta, error)
        return ("x264",)
    return leer_codificadores(texto)


def bitrate_avanzado(nombre) -> int:
    """El bitrate que el modo Avanzado dejó en streamEncoder.json."""
    carpeta = perfil_en_disco.carpeta_de_perfil(nombre)
    if carpeta is None:
        return _BITRATE_POR_DEFECTO
    try:
        datos = json.loads((carpeta / "streamEncoder.json").read_text(
            encoding="utf-8-sig"))
    except (OSError, ValueError):
        return _BITRATE_POR_DEFECTO
    bitrate = datos.get("bitrate") if isinstance(datos, dict) else None
    try:
        return int(bitrate) if int(bitrate) > 0 else _BITRATE_POR_DEFECTO
    except (TypeError, ValueError):
        return _BITRATE_POR_DEFECTO
