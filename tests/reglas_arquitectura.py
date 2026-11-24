# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Reglas de arquitectura declaradas como tabla.

Cada regla dice qué está prohibido, quién es su único dueño y qué archivos
quedan pendientes con su motivo. Los detectores de la mayoría de las
reglas y la revisión viven en tests/reglas_detectores.py.
"""

from __future__ import annotations

import ast
from collections.abc import Callable
from dataclasses import dataclass

from tests.reglas_controles import (
    detectar_cuadro_sin_escape,
    detectar_mnemonico,
    detectar_nombres_de_control,
    detectar_pestana_sin_anuncio,
    detectar_predeterminado,
)
from tests.reglas_diseno import (
    PENDIENTES_BORDES,
    PENDIENTES_COLORES,
    PENDIENTES_FUENTES,
    PENDIENTES_TAMANOS,
    PIEZAS,
    _ui,
    detectar_bordes,
    detectar_colores,
    detectar_fuentes,
    detectar_tamanos,
)
from tests.reglas_detectores import (
    Hallazgo,
    _controles,
    _esperas,
    _interaccion,
    _menus_de_la_barra,
    _paquete,
    _todo,
    detectar_bibliotecas_voz,
    detectar_capas,
    detectar_controles,
    detectar_cuadros,
    detectar_escape,
    detectar_esperas,
    detectar_interaccion,
    detectar_red,
    detectar_rotulos_de_menu,
)
from tests.reglas_plataformas import detectar_ids_de_plataforma
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


def _a_pendientes(casos: dict[str, tuple[int, str]]) -> dict[str, Pendiente]:
    return {archivo: Pendiente(cantidad, motivo)
            for archivo, (cantidad, motivo) in casos.items()}


def _importa_zipfile(nombre: str) -> bool:
    return nombre == "zipfile" or nombre.startswith("zipfile.")


def _modulo_traduccion_prohibido(nombre: str) -> bool:
    raices = ("wx", "guyrapu.ui", "guyrapu.capture")
    return any(nombre == raiz or nombre.startswith(raiz + ".")
               for raiz in raices)


def detectar_traduccion(archivo: str, arbol: ast.Module) -> list[Hallazgo]:
    hallazgos = []
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            hallazgos.extend(
                Hallazgo(archivo, nodo.lineno)
                for alias in nodo.names
                if _modulo_traduccion_prohibido(alias.name))
        elif (isinstance(nodo, ast.ImportFrom)
              and _modulo_traduccion_prohibido(nodo.module or "")):
            hallazgos.append(Hallazgo(archivo, nodo.lineno))
    return sorted(hallazgos, key=lambda hallazgo: hallazgo.linea)


_NOMBRES_LOCALES = ("phonon", "piper")


def detectar_nombres_de_motores_locales(archivo: str,
                                        arbol: ast.Module) -> list[Hallazgo]:
    """Los ids de los motores locales solo viven en su proveedor y fuente."""
    hallazgos = [
        Hallazgo(archivo, nodo.lineno)
        for nodo in ast.walk(arbol)
        if isinstance(nodo, ast.Constant) and nodo.value in _NOMBRES_LOCALES
    ]
    return sorted(hallazgos, key=lambda hallazgo: hallazgo.linea)


_LITERALES_DE_FABRICA = ("sapi", "gemini")


def detectar_literales_de_fabrica(archivo: str,
                                  arbol: ast.Module) -> list[Hallazgo]:
    """El motor y el proveedor de fábrica solo son literales en sus dueños."""
    hallazgos = [
        Hallazgo(archivo, nodo.lineno)
        for nodo in ast.walk(arbol)
        if isinstance(nodo, ast.Constant) and nodo.value in _LITERALES_DE_FABRICA
    ]
    return sorted(hallazgos, key=lambda hallazgo: hallazgo.linea)


def _traduccion(archivo: str) -> bool:
    return archivo.startswith("guyrapu/translation/")


def detectar_zipfile(archivo: str, arbol: ast.Module) -> list[Hallazgo]:
    hallazgos = []
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            hallazgos.extend(Hallazgo(archivo, nodo.lineno)
                             for alias in nodo.names
                             if _importa_zipfile(alias.name))
        elif (isinstance(nodo, ast.ImportFrom) and nodo.level == 0
                and _importa_zipfile(nodo.module or "")):
            hallazgos.append(Hallazgo(archivo, nodo.lineno))
    return sorted(hallazgos, key=lambda hallazgo: hallazgo.linea)


def detectar_deslizador(archivo: str, arbol: ast.Module) -> list[Hallazgo]:
    hallazgos = []
    for nodo in ast.walk(arbol):
        if (isinstance(nodo, ast.Call)
                and isinstance(nodo.func, ast.Attribute)
                and nodo.func.attr == "Slider"
                and isinstance(nodo.func.value, ast.Name)
                and nodo.func.value.id == "wx"):
            hallazgos.append(Hallazgo(archivo, nodo.lineno))
    return sorted(hallazgos, key=lambda hallazgo: hallazgo.linea)


def _musica(archivo: str) -> bool:
    return archivo.startswith("guyrapu/music/")


def detectar_volumen_sin_atenuar(archivo: str, arbol: ast.Module) -> list[Hallazgo]:
    """Todo volumen que llega a VLC pasa por `atenuado`, salvo el 0 del fundido."""
    hallazgos = []
    for nodo in ast.walk(arbol):
        if not (isinstance(nodo, ast.Call)
                and isinstance(nodo.func, ast.Attribute)
                and nodo.func.attr == "audio_set_volume" and nodo.args):
            continue
        valor = nodo.args[0]
        pasa_por_atenuado = (
            isinstance(valor, ast.Call)
            and ((isinstance(valor.func, ast.Name) and valor.func.id == "atenuado")
                 or (isinstance(valor.func, ast.Attribute)
                     and valor.func.attr == "atenuado")))
        if pasa_por_atenuado or (isinstance(valor, ast.Constant)
                                 and valor.value == 0):
            continue
        hallazgos.append(Hallazgo(archivo, nodo.lineno))
    return sorted(hallazgos, key=lambda hallazgo: hallazgo.linea)


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
        duenos=("guyrapu/core/red.py", "guyrapu/core/red_httpx.py",
                "guyrapu/translation/proveedores/google.py"),
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
        pendientes={},
        duenos=("guyrapu/ui/menu_habilitado.py",),
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
                "guyrapu/core/vigilancia.py",
                # No espera a un servicio: reproduce cuadros a su hora.
                "guyrapu/obs/animador.py"),
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
        pendientes={},
        ambito=_paquete,
    ),
    Regla(
        id="R13",
        prohibido="un rótulo _() literal de botón, casilla o radio no lleva exactamente un &",
        detectar=detectar_mnemonico,
        pendientes={},
    ),
    Regla(
        id="R14",
        prohibido="un wx.Notebook no se pasa a enlazar_anuncio_de_pestana en su archivo",
        detectar=detectar_pestana_sin_anuncio,
        pendientes={},
        ambito=_paquete,
    ),
    Regla(
        id="R15",
        prohibido="un cuadro de wx no tiene en su clase ninguna vía para cerrar con Escape",
        detectar=detectar_cuadro_sin_escape,
        pendientes={},
        ambito=_paquete,
    ),
    Regla(
        id="R16",
        prohibido="guyrapu/interaction/ no importa guyrapu.capture, guyrapu.youtube, guyrapu.ui ni wx",
        detectar=detectar_interaccion,
        pendientes={},
        ambito=_interaccion,
    ),
    Regla(
        id="R17",
        prohibido="zipfile se importa solo en guyrapu/interaction/paquetes.py y guyrapu/core/actualizacion.py",
        detectar=detectar_zipfile,
        pendientes={},
        duenos=("guyrapu/interaction/paquetes.py",
                "guyrapu/core/actualizacion.py"),
        ambito=_paquete,
    ),
    Regla(
        id="R18",
        prohibido="guyrapu/translation/ no importa guyrapu.capture, guyrapu.ui ni wx",
        detectar=detectar_traduccion,
        pendientes={},
        ambito=_traduccion,
    ),
    Regla(
        id="R19",
        prohibido="el nivel en un rango va por deslizador_accesible",
        detectar=detectar_deslizador,
        pendientes={},
        duenos=("guyrapu/ui/deslizador.py", "guyrapu/player/reproductor.py"),
        ambito=_paquete,
    ),
    Regla(
        id="R20",
        prohibido="phonon y piper solo son literales en su proveedor y su fuente",
        detectar=detectar_nombres_de_motores_locales,
        pendientes={},
        duenos=("guyrapu/voice/proveedores/phonon.py",
                "guyrapu/voice/proveedores/piper.py"),
        ambito=_paquete,
    ),
    Regla(
        id="R21",
        prohibido="sapi y gemini solo son literales en su registro y sus dueños",
        detectar=detectar_literales_de_fabrica,
        pendientes={},
        duenos=("guyrapu/voice/proveedores/",
                "guyrapu/voice/escala_voz.py",
                "guyrapu/core/autocomprobacion.py",
                "guyrapu/ai/proveedores.py",
                "guyrapu/ai/protocolos.py",
                "guyrapu/core/config_predeterminada.py"),
        ambito=_paquete,
    ),
    Regla(
        id="R22",
        prohibido="los bordes de un sizer y los nombres numéricos solo viven en las piezas comunes de guyrapu/ui/",
        detectar=detectar_bordes,
        pendientes=_a_pendientes(PENDIENTES_BORDES),
        duenos=PIEZAS,
        ambito=_ui,
    ),
    Regla(
        id="R23",
        prohibido="los tamaños de control y wx.Size solo viven en las piezas comunes de guyrapu/ui/",
        detectar=detectar_tamanos,
        pendientes=_a_pendientes(PENDIENTES_TAMANOS),
        duenos=PIEZAS,
        ambito=_ui,
    ),
    Regla(
        id="R24",
        prohibido="los tamaños de letra de wx.Font y SetPointSize solo viven en las piezas comunes de guyrapu/ui/",
        detectar=detectar_fuentes,
        pendientes=_a_pendientes(PENDIENTES_FUENTES),
        duenos=PIEZAS,
        ambito=_ui,
    ),
    Regla(
        id="R25",
        prohibido="los colores de wx.Colour y de primer plano o fondo solo viven en las piezas comunes de guyrapu/ui/",
        detectar=detectar_colores,
        pendientes=_a_pendientes(PENDIENTES_COLORES),
        duenos=PIEZAS,
        ambito=_ui,
    ),
    Regla(
        id="R26",
        prohibido="en guyrapu/music/, audio_set_volume recibe un valor sin atenuar",
        detectar=detectar_volumen_sin_atenuar,
        pendientes={},
        ambito=_musica,
    ),
    Regla(
        id="R27",
        prohibido="el id de una plataforma se escribe solo en su registro",
        detectar=detectar_ids_de_plataforma,
        pendientes={
            **_pendientes(
                "id de plataforma: usar plataformas.YOUTUBE o TIKTOK", {
                    "guyrapu/obs/overlay_datos.py": 2,
                    "guyrapu/player/reproductor.py": 1,
                    "guyrapu/restream/chat_restream.py": 1,
                    "guyrapu/restream/ganchos.py": 2,
                    "guyrapu/restream/perfiles.py": 5,
                    "guyrapu/restream/transmitir.py": 5,
                    "guyrapu/ui/gui_historial.py": 3,
                    "guyrapu/ui/recientes_inicio.py": 1,
                    "guyrapu/ui/restream_perfil.py": 4,
                    "main.py": 2,
                }),
            **_pendientes("no es un id de plataforma", {
                "guyrapu/core/autocomprobacion.py": 1,
                "guyrapu/core/avisos_tiktok.py": 4,
                "guyrapu/core/config_lectura.py": 5,
                "guyrapu/core/config_predeterminada.py": 2,
                "guyrapu/downloads/busqueda_youtube.py": 1,
                "guyrapu/ui/gui_transmitir.py": 1,
                "guyrapu/ui/preferencias_eventos.py": 4,
                "guyrapu/youtube/cuota.py": 1,
            }),
        },
    ),
)
