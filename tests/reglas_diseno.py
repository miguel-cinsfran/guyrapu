# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Detectores de armado visual escrito a mano en la interfaz.

Cuentan bordes, tamaños, letras y colores puestos con números o texto en
guyrapu/ui/. Las piezas comunes son las dueñas y el resto queda pendiente.
"""

from __future__ import annotations

import ast

from tests.reglas_detectores import Hallazgo

PIEZAS = (
    "guyrapu/ui/formulario.py",
    "guyrapu/ui/pagina_de_lista.py",
    "guyrapu/ui/botonera.py",
    "guyrapu/ui/deslizador.py",
    "guyrapu/ui/paleta.py",
    "guyrapu/ui/tema.py",
)

MOTIVO = "falta pasar a las piezas comunes"

_POSICION_BORDE = {"Add": 3, "Insert": 4}
_METODOS_TAMANO = ("SetSize", "SetMinSize", "SetMaxSize", "SetInitialSize")


def _ui(archivo: str) -> bool:
    return archivo.startswith("guyrapu/ui/")


def _numeros(nodo: ast.expr) -> list[int | float]:
    if isinstance(nodo, ast.Constant) and isinstance(nodo.value, (int, float)):
        if not isinstance(nodo.value, bool):
            return [nodo.value]
    if isinstance(nodo, (ast.Tuple, ast.List)):
        return [valor for elemento in nodo.elts
                for valor in _numeros(elemento)]
    return []


def _destino(nodo: ast.expr) -> str | None:
    if isinstance(nodo, ast.Attribute):
        return nodo.attr
    if isinstance(nodo, ast.Name):
        return nodo.id
    return None


def _es_wx(nodo: ast.expr, nombre: str) -> bool:
    return (isinstance(nodo, ast.Attribute) and nodo.attr == nombre
            and isinstance(nodo.value, ast.Name) and nodo.value.id == "wx")


def _borde_de(llamada: ast.Call) -> ast.expr | None:
    posicion = _POSICION_BORDE.get(_destino(llamada.func))
    if posicion is not None and len(llamada.args) > posicion:
        return llamada.args[posicion]
    for palabra in llamada.keywords:
        if palabra.arg == "border":
            return palabra.value
    return None


def _tamanos_de(llamada: ast.Call) -> list[ast.expr]:
    if (_destino(llamada.func) in _METODOS_TAMANO
            or _es_wx(llamada.func, "Size")):
        return [*llamada.args, *(kw.value for kw in llamada.keywords)]
    return [kw.value for kw in llamada.keywords if kw.arg == "size"]


def _nombres_en(expresion: ast.expr) -> set[str]:
    return {nodo.id for nodo in ast.walk(expresion)
            if isinstance(nodo, ast.Name)}


def _nombres_de_medidas(arbol: ast.Module) -> set[str]:
    nombres = set()
    for nodo in ast.walk(arbol):
        if not isinstance(nodo, ast.Call):
            continue
        borde = _borde_de(nodo)
        if borde is not None:
            nombres.update(_nombres_en(borde))
        for medida in _tamanos_de(nodo):
            nombres.update(_nombres_en(medida))
    return nombres


def _numero_local(nodo: ast.stmt, nombres: set[str]) -> bool:
    if not isinstance(nodo, ast.Assign):
        return False
    destinos = [d.id for d in nodo.targets if isinstance(d, ast.Name)]
    return (bool(destinos) and any(d in nombres for d in destinos)
            and bool(_numeros(nodo.value)))


def _unicos(hallazgos: list[Hallazgo]) -> list[Hallazgo]:
    vistos: set[int] = set()
    resultado = []
    for hallazgo in sorted(hallazgos, key=lambda hallazgo: hallazgo.linea):
        if hallazgo.linea not in vistos:
            vistos.add(hallazgo.linea)
            resultado.append(hallazgo)
    return resultado


def detectar_bordes(archivo: str, arbol: ast.Module) -> list[Hallazgo]:
    nombres = _nombres_de_medidas(arbol)
    hallazgos = []
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Call):
            borde = _borde_de(nodo)
            if borde is not None and any(valor != 0
                                         for valor in _numeros(borde)):
                hallazgos.append(Hallazgo(archivo, nodo.lineno))
        if _numero_local(nodo, nombres):
            hallazgos.append(Hallazgo(archivo, nodo.lineno))
    return _unicos(hallazgos)


def detectar_tamanos(archivo: str, arbol: ast.Module) -> list[Hallazgo]:
    nombres = _nombres_de_medidas(arbol)
    hallazgos = []
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Call):
            if any(valor != -1 for medida in _tamanos_de(nodo)
                   for valor in _numeros(medida)):
                hallazgos.append(Hallazgo(archivo, nodo.lineno))
        if _numero_local(nodo, nombres):
            hallazgos.append(Hallazgo(archivo, nodo.lineno))
    return _unicos(hallazgos)


def detectar_fuentes(archivo: str, arbol: ast.Module) -> list[Hallazgo]:
    hallazgos = []
    for nodo in ast.walk(arbol):
        if not isinstance(nodo, ast.Call):
            continue
        if _es_wx(nodo.func, "Font"):
            if (nodo.args and _numeros(nodo.args[0])) or any(
                    kw.arg == "pointSize" and _numeros(kw.value)
                    for kw in nodo.keywords):
                hallazgos.append(Hallazgo(archivo, nodo.lineno))
        elif (_destino(nodo.func) == "SetPointSize"
              and any(_numeros(arg) for arg in nodo.args)):
            hallazgos.append(Hallazgo(archivo, nodo.lineno))
    return _unicos(hallazgos)


def _literal_color(nodo: ast.expr) -> bool:
    if isinstance(nodo, (ast.Tuple, ast.List)):
        return any(_literal_color(elemento) for elemento in nodo.elts)
    if isinstance(nodo, ast.Constant):
        return (isinstance(nodo.value, (int, float, str))
                and not isinstance(nodo.value, bool))
    return False


def _tupla_o_texto(nodo: ast.expr) -> bool:
    if isinstance(nodo, ast.Tuple):
        return any(_literal_color(elemento) for elemento in nodo.elts)
    return isinstance(nodo, ast.Constant) and isinstance(nodo.value, str)


def detectar_colores(archivo: str, arbol: ast.Module) -> list[Hallazgo]:
    hallazgos = []
    for nodo in ast.walk(arbol):
        if not isinstance(nodo, ast.Call):
            continue
        if _es_wx(nodo.func, "Colour"):
            if any(_literal_color(arg) for arg in nodo.args):
                hallazgos.append(Hallazgo(archivo, nodo.lineno))
        elif (_destino(nodo.func) in ("SetForegroundColour",
                                      "SetBackgroundColour")
              and nodo.args and _tupla_o_texto(nodo.args[0])):
            hallazgos.append(Hallazgo(archivo, nodo.lineno))
    return _unicos(hallazgos)


PENDIENTES_BORDES: dict[str, tuple[int, str]] = {
    "guyrapu/ui/gui_preferencias.py": (4, MOTIVO),
    "guyrapu/ui/descargas_buscador.py": (13, MOTIVO),
    "guyrapu/ui/gui_descargas.py": (7, MOTIVO),
    "guyrapu/ui/voces_ventana.py": (13, MOTIVO),
    "guyrapu/ui/gui_construccion.py": (12, MOTIVO),
    "guyrapu/ui/musica_ventana.py": (12, MOTIVO),
    "guyrapu/ui/gui.py": (2, MOTIVO),
    "guyrapu/ui/escena_pagina_audio.py": (8, MOTIVO),
    "guyrapu/ui/gui_comentarios.py": (8, MOTIVO),
    "guyrapu/ui/obs_ventana.py": (2, MOTIVO),
    "guyrapu/ui/chat_participacion.py": (7, MOTIVO),
    "guyrapu/ui/musica_filtros.py": (6, MOTIVO),
    "guyrapu/ui/restream_pagina_eventos.py": (6, MOTIVO),
    "guyrapu/ui/chat_buscar.py": (5, MOTIVO),
    "guyrapu/ui/descargas_listas.py": (5, MOTIVO),
    "guyrapu/ui/escena_pagina_escena.py": (5, MOTIVO),
    "guyrapu/ui/gui_historial.py": (5, MOTIVO),
    "guyrapu/ui/escena_pagina_fuentes.py": (4, MOTIVO),
    "guyrapu/ui/escena_propiedades.py": (1, MOTIVO),
    "guyrapu/ui/ia_ventana.py": (2, MOTIVO),
    "guyrapu/ui/obs_pagina_general.py": (4, MOTIVO),
    "guyrapu/ui/recientes_inicio.py": (3, MOTIVO),
    "guyrapu/ui/gui_transmision.py": (3, MOTIVO),
    "guyrapu/ui/musica_ventana_igualando.py": (2, MOTIVO),
    "guyrapu/ui/obs_pagina_grabacion.py": (3, MOTIVO),
    "guyrapu/ui/restream_pagina_perfiles.py": (2, MOTIVO),
    "guyrapu/ui/buscador_filtros.py": (2, MOTIVO),
    "guyrapu/ui/gui_redactar.py": (2, MOTIVO),
    "guyrapu/ui/ia_agregar_captura.py": (2, MOTIVO),
    "guyrapu/ui/interaccion_ventana.py": (2, MOTIVO),
    "guyrapu/ui/obs_pagina_perfiles.py": (2, MOTIVO),
    "guyrapu/ui/restream_pagina_cuenta.py": (2, MOTIVO),
    "guyrapu/ui/restream_pagina_destinos.py": (2, MOTIVO),
    "guyrapu/ui/restream_perfil.py": (2, MOTIVO),
    "guyrapu/ui/restream_ventana.py": (2, MOTIVO),
    "guyrapu/ui/gui_grabaciones.py": (1, MOTIVO),
}

PENDIENTES_TAMANOS: dict[str, tuple[int, str]] = {
    "guyrapu/ui/gui.py": (3, MOTIVO),
    "guyrapu/ui/obs_ventana.py": (2, MOTIVO),
    "guyrapu/ui/gui_descargas.py": (1, MOTIVO),
    "guyrapu/ui/gui_directo_youtube.py": (1, MOTIVO),
    "guyrapu/ui/gui_preferencias.py": (3, MOTIVO),
    "guyrapu/ui/dialogo_asistente_perfiles.py": (2, MOTIVO),
    "guyrapu/ui/dialogo_prueba_conexion.py": (2, MOTIVO),
    "guyrapu/ui/dialogo_prueba_equipo.py": (2, MOTIVO),
    "guyrapu/ui/encuesta_cuadro.py": (1, MOTIVO),
    "guyrapu/ui/escena_pagina_audio.py": (1, MOTIVO),
    "guyrapu/ui/gui_construccion.py": (2, MOTIVO),
    "guyrapu/ui/gui_microfono.py": (2, MOTIVO),
    "guyrapu/ui/ia_agregar_captura.py": (2, MOTIVO),
    "guyrapu/ui/musica_editor_lista.py": (1, MOTIVO),
    "guyrapu/ui/musica_filtros.py": (2, MOTIVO),
    "guyrapu/ui/musica_ventana.py": (2, MOTIVO),
    "guyrapu/ui/voces_ventana.py": (2, MOTIVO),
    "guyrapu/ui/chat_buscar.py": (1, MOTIVO),
    "guyrapu/ui/chat_participacion.py": (1, MOTIVO),
    "guyrapu/ui/descargas_buscador.py": (1, MOTIVO),
    "guyrapu/ui/ensayo_ventana.py": (1, MOTIVO),
    "guyrapu/ui/escena_pagina_escena.py": (1, MOTIVO),
    "guyrapu/ui/escena_pagina_fuentes.py": (1, MOTIVO),
    "guyrapu/ui/gui_actualizacion.py": (1, MOTIVO),
    "guyrapu/ui/gui_historial.py": (1, MOTIVO),
    "guyrapu/ui/interaccion_ventana.py": (1, MOTIVO),
    "guyrapu/ui/obs_pagina_general.py": (1, MOTIVO),
    "guyrapu/ui/restream_perfil.py": (1, MOTIVO),
    "guyrapu/ui/restream_ventana.py": (1, MOTIVO),
    "guyrapu/ui/ventana_espera.py": (1, MOTIVO),
}

PENDIENTES_FUENTES: dict[str, tuple[int, str]] = {}
PENDIENTES_COLORES: dict[str, tuple[int, str]] = {}
