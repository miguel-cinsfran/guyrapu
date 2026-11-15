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

from tests.reglas_controles import (
    detectar_mnemonico,
    detectar_nombres_de_control,
    detectar_predeterminado,
)
from tests.reglas_detectores import (
    Hallazgo,
    _controles,
    _esperas,
    _menus_de_la_barra,
    _paquete,
    _todo,
    detectar_bibliotecas_voz,
    detectar_capas,
    detectar_controles,
    detectar_cuadros,
    detectar_escape,
    detectar_esperas,
    detectar_red,
    detectar_rotulos_de_menu,
)
from tests.reglas_sonido import detectar_avisar, detectar_avisar_error


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
        pendientes={},
        duenos=("guyrapu/core/red.py", "guyrapu/core/red_httpx.py"),
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
        prohibido="avisar recibe como sonido un evento literal de EVENTOS",
        detectar=detectar_avisar,
        pendientes={
            "guyrapu/restream/ganchos.py": Pendiente(
                1, "el sonido llega por un cierre desde _anunciar_de_frame y "
                   "no se puede saber leyendo la llamada"),
            "guyrapu/ui/comando_directo.py": Pendiente(
                1, "el sonido lo calcula obs_estado.sonido_resultado y no se "
                   "puede saber leyendo el código"),
            "guyrapu/ui/gui_musica.py": Pendiente(
                1, "el sonido es el atributo aviso.sonido de otro módulo y no "
                   "se sigue entre módulos"),
        },
    ),
    Regla(
        id="R6",
        prohibido="no se deshabilita un control con Disable() ni con Enable(False)",
        detectar=detectar_controles,
        pendientes=_pendientes("dejar el control habilitado y anunciar el motivo", {
            "guyrapu/ui/boton_directo.py": 1,
            "guyrapu/ui/escena_captura_ventana.py": 1,
            "guyrapu/ui/escena_propiedades.py": 2,
            "guyrapu/ui/gui.py": 7,
            "guyrapu/ui/gui_descargas.py": 1, "guyrapu/ui/gui_directo_youtube.py": 2,
            "guyrapu/ui/gui_sesion.py": 2,
            "guyrapu/ui/ia_agregar_captura.py": 2, "guyrapu/ui/ia_ventana.py": 2,
            "guyrapu/ui/lista_acciones.py": 1,
            "guyrapu/ui/obs_ventana.py": 1,
            "guyrapu/ui/preferencias_atajos.py": 1,
            "guyrapu/ui/restream_pagina_cuenta.py": 1,
        }),
        ambito=_controles,
    ),
    Regla(
        id="R7",
        prohibido="usar guyrapu.core.esperas o guyrapu.core.vigilancia",
        detectar=detectar_esperas,
        pendientes={
            "guyrapu/obs/candado_obs.py": Pendiente(
                2, "el candado de OBS no espera a un servicio"),
            "guyrapu/obs/reacciones_supervisor.py": Pendiente(
                1, "repite esperar_salida, que ya usa guyrapu.core.esperas"),
        },
        duenos=("guyrapu/core/tiempo.py", "guyrapu/core/esperas.py",
                "guyrapu/core/vigilancia.py"),
        ambito=_esperas,
    ),
    Regla(
        id="R8",
        prohibido="prism, ptts, piper, onnxruntime y sounddevice se importan solo en sus dueños",
        detectar=detectar_bibliotecas_voz,
        pendientes={},
        duenos=("guyrapu/voice/proveedores/",
                "guyrapu/voice/reproductor_pcm.py",
                "guyrapu/voice/lector.py",
                "guyrapu/core/autocomprobacion.py"),
        ambito=_paquete,
    ),
    Regla(
        id="R9",
        prohibido="los rótulos de la barra de menús salen de textos fijos del código",
        detectar=detectar_rotulos_de_menu,
        pendientes={},
        ambito=_menus_de_la_barra,
    ),
    Regla(
        id="R10",
        prohibido="avisar con error=True no usa un sonido de una familia que no sea error, desconexión o espera",
        detectar=detectar_avisar_error,
        pendientes={},
    ),
    Regla(
        id="R11",
        prohibido="preguntar se llama sin predeterminado_si explícito",
        detectar=detectar_predeterminado,
        pendientes={},
    ),
    Regla(
        id="R12",
        prohibido="un constructor de control interactivo de wx queda sin name= no vacío ni nombre_accesible",
        detectar=detectar_nombres_de_control,
        pendientes=_pendientes(
            "darle nombre accesible al control en el constructor o con "
            "nombre_accesible", {
                "guyrapu/ui/gui_actualizacion.py": 2,
            }),
        ambito=_paquete,
    ),
    Regla(
        id="R13",
        prohibido="un rótulo _() literal de botón, casilla o radio no lleva exactamente un &",
        detectar=detectar_mnemonico,
        pendientes={},
    ),
)
