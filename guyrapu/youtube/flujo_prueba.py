# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Crear y borrar el flujo RTMP de una prueba de conexión.

Su única razón para cambiar es cómo se crea y se borra ese flujo. Recibe el
servicio de escritura de YouTube ya construido, igual que el resto de la capa.
"""

from __future__ import annotations

_PARTE = "snippet,cdn,contentDetails"


def crear(servicio, titulo) -> tuple[str, str, str]:
    """Crea un flujo no reutilizable y devuelve (id, servidor, clave)."""
    resp = servicio.liveStreams().insert(
        part=_PARTE,
        body={"snippet": {"title": (titulo or "").strip()[:100]},
              "cdn": {"ingestionType": "rtmp", "frameRate": "variable",
                      "resolution": "variable"},
              "contentDetails": {"isReusable": False}}).execute()
    info = (resp.get("cdn") or {}).get("ingestionInfo") or {}
    return (resp.get("id") or "", info.get("ingestionAddress") or "",
            info.get("streamName") or "")


def borrar(servicio, id_flujo) -> None:
    """Borra de la cuenta el flujo de la prueba."""
    servicio.liveStreams().delete(id=id_flujo).execute()
