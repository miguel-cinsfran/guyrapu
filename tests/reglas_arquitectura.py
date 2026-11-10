# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Reglas de arquitectura declaradas como tabla.

Cada regla dice qué está prohibido, quién es su único dueño y qué archivos
quedan pendientes con su motivo. Los detectores y la revisión viven en
tests/reglas_detectores.py.
"""

from __future__ import annotations

import ast
from collections.abc import Callable
from dataclasses import dataclass

from tests.reglas_detectores import (
    Hallazgo,
    _controles,
    _paquete,
    _todo,
    detectar_avisar,
    detectar_capas,
    detectar_controles,
    detectar_cuadros,
    detectar_escape,
    detectar_red,
)


@dataclass(frozen=True)
class Pendiente:
    cantidad: int
    motivo: str


@dataclass(frozen=True)
class Regla:
    id: str
    prohibido: str
    detectar: Callable[[str, ast.Module], list[Hallazgo]]
    pendientes: dict[str, Pendiente]
    duenos: tuple[str, ...] = ()
    ambito: Callable[[str], bool] = _todo


def _pendientes(motivo: str, casos: dict[str, int]) -> dict[str, Pendiente]:
    return {archivo: Pendiente(cantidad, motivo)
            for archivo, cantidad in casos.items()}


REGLAS = (
    Regla(
        id="R1",
        prohibido="wx.MessageBox y wx.MessageDialog solo en guyrapu/ui/confirmar.py",
        detectar=detectar_cuadros,
        pendientes={},
        duenos=("guyrapu/ui/confirmar.py",),
    ),
    Regla(
        id="R2",
        prohibido="guyrapu.ui se importa solo desde guyrapu/ui/, main.py y el reproductor",
        detectar=detectar_capas,
        pendientes=_pendientes(
            "recibir funciones en vez de importar la ventana", {
                "guyrapu/capture/chat_adicional.py": 1,
                "guyrapu/restream/chat_restream.py": 3,
                "guyrapu/restream/ganchos.py": 5,
            }),
        duenos=("guyrapu/ui/", "main.py", "guyrapu/player/reproductor.py",
                "guyrapu/player/pantalla_completa.py"),
    ),
    Regla(
        id="R3",
        prohibido="urllib.request, httpx y requests no se importan en guyrapu/",
        detectar=detectar_red,
        pendientes=_pendientes("pasar al módulo de red común", {
            "guyrapu/ai/catalogo.py": 1, "guyrapu/ai/envio_ia.py": 1,
            "guyrapu/core/actualizacion.py": 1, "guyrapu/core/canal_app.py": 1,
            "guyrapu/core/novedades.py": 1,
            "guyrapu/downloads/ytdlp_actualizar.py": 1,
            "guyrapu/player/flujo_tiktok.py": 1,
            "guyrapu/player/relevo_ffmpeg.py": 1,
            "guyrapu/restream/api.py": 1, "guyrapu/restream/oauth.py": 1,
            "guyrapu/voice/elevenlabs.py": 1,
        }),
        ambito=_paquete,
    ),
    Regla(
        id="R4",
        prohibido="WXK_ESCAPE no aparece en guyrapu/",
        detectar=detectar_escape,
        pendientes={},
        duenos=("guyrapu/ui/tecla_escape.py",),
        ambito=_paquete,
    ),
    Regla(
        id="R5",
        prohibido="avisar recibe un evento de EVENTOS que no sea error ni copiar",
        detectar=detectar_avisar,
        pendientes=_pendientes("elegir un sonido propio para este aviso", {
            "guyrapu/restream/ganchos.py": 1,
            "guyrapu/ui/boton_directo.py": 3, "guyrapu/ui/comandos_clips.py": 2,
            "guyrapu/ui/comandos_grabacion.py": 2,
            "guyrapu/ui/control_grabacion.py": 4,
            "guyrapu/ui/descargas_buscador.py": 1, "guyrapu/ui/directo_panel.py": 1,
            "guyrapu/ui/gui_directo_huerfano.py": 1,
            "guyrapu/ui/gui_envio_chat.py": 1, "guyrapu/ui/gui_musica.py": 1,
            "guyrapu/ui/gui_transmitir.py": 1,
            "guyrapu/ui/inicio_youtube.py": 2, "guyrapu/ui/obs_ventana.py": 1,
            "guyrapu/ui/operaciones_obs.py": 1,
            "guyrapu/ui/preferencias_api.py": 1,
            "guyrapu/ui/restream_acciones_destino.py": 5,
            "guyrapu/ui/restream_ventana.py": 2,
        }),
    ),
    Regla(
        id="R6",
        prohibido="no se deshabilita un control con Disable() ni con Enable(False)",
        detectar=detectar_controles,
        pendientes=_pendientes("dejar el control habilitado y anunciar el motivo", {
            "guyrapu/ui/boton_directo.py": 2, "guyrapu/ui/buscador_tandas.py": 3,
            "guyrapu/ui/descargas_buscador.py": 1, "guyrapu/ui/escena_captura_ventana.py": 1,
            "guyrapu/ui/escena_propiedades.py": 2,
            "guyrapu/ui/gui.py": 10, "guyrapu/ui/gui_comentarios.py": 7,
            "guyrapu/ui/gui_descargas.py": 1, "guyrapu/ui/gui_directo_youtube.py": 2,
            "guyrapu/ui/gui_historial.py": 2, "guyrapu/ui/gui_microfono.py": 2,
            "guyrapu/ui/ia_agregar_captura.py": 2, "guyrapu/ui/ia_ventana.py": 2,
            "guyrapu/ui/lista_acciones.py": 1, "guyrapu/ui/musica_ventana.py": 1,
            "guyrapu/ui/obs_ventana.py": 2, "guyrapu/ui/preferencias_api.py": 3,
            "guyrapu/ui/preferencias_atajos.py": 1, "guyrapu/ui/preferencias_ia.py": 1,
            "guyrapu/ui/preferencias_ia_lista.py": 1, "guyrapu/ui/preferencias_voz.py": 5,
            "guyrapu/ui/restream_pagina_cuenta.py": 1,
        }),
        ambito=_controles,
    ),
)
