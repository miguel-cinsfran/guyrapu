# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Detectores de las reglas sobre avisos y sonidos, con ast.

Leen archivos, no importan wx ni la aplicación. R5 y R10.
"""

from __future__ import annotations

import ast
from functools import lru_cache

from guyrapu.core.eventos_sonido import CATALOGO
from guyrapu.core.eventos_sonido import EVENTOS as EVENTOS_SONIDO
from tests.reglas_detectores import (
    Hallazgo,
    _es_llamada_avisar,
    _nombres_avisar,
    _sonido_de,
)

FAMILIAS = {evento.clave: evento.familia for evento in CATALOGO}
# Un fallo en vivo que se cae o que la app reintenta sola también va con error.
FAMILIAS_DE_ERROR = frozenset(("error", "desconexion", "en_curso"))


@lru_cache(maxsize=None)
def eventos_de_sonido() -> frozenset[str]:
    return frozenset(EVENTOS_SONIDO)


def _constantes_de_sonido(arbol: ast.Module,
                          eventos: frozenset[str]) -> dict[str, str]:
    asignados = {nodo.targets[0].id: nodo.value for nodo in arbol.body
                 if isinstance(nodo, ast.Assign) and len(nodo.targets) == 1
                 and isinstance(nodo.targets[0], ast.Name)}
    usos = [nodo.id for nodo in ast.walk(arbol)
            if isinstance(nodo, ast.Name) and isinstance(nodo.ctx, ast.Store)]
    return {nombre: valor.value for nombre, valor in asignados.items()
            if usos.count(nombre) == 1
            and isinstance(valor, ast.Constant)
            and isinstance(valor.value, str) and valor.value in eventos}


def _parametros_de(arbol: ast.Module, linea: int) -> set[str]:
    funciones = [nodo for nodo in ast.walk(arbol)
                 if isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef))
                 and nodo.lineno <= linea <= (nodo.end_lineno or nodo.lineno)]
    if not funciones:
        return set()
    interna = max(funciones, key=lambda nodo: nodo.lineno)
    return {argumento.arg
            for argumento in [*interna.args.posonlyargs, *interna.args.args,
                              *interna.args.kwonlyargs]}


def _sonido_valido(nodo: ast.expr | None, eventos: frozenset[str],
                   nombres: set[str]) -> bool:
    if isinstance(nodo, ast.Name):
        return nodo.id in nombres
    if not (isinstance(nodo, ast.Constant) and isinstance(nodo.value, str)):
        return False
    return bool(nodo.value) and nodo.value in eventos


def detectar_avisar(archivo: str, arbol: ast.Module,
                    eventos: frozenset[str] | None = None) -> list[Hallazgo]:
    # Un envoltorio que reenvía el sonido que recibió es válido aunque no
    # vigile qué le pasan sus llamadores: esa parte queda fuera de esta regla.
    funciones, modulos = _nombres_avisar(arbol)
    disponibles = eventos_de_sonido() if eventos is None else eventos
    constantes = _constantes_de_sonido(arbol, disponibles)
    hallazgos = []
    for nodo in ast.walk(arbol):
        if not isinstance(nodo, ast.Call):
            continue
        if not _es_llamada_avisar(nodo.func, funciones, modulos):
            continue
        nombres = set(constantes) | _parametros_de(arbol, nodo.lineno)
        if not _sonido_valido(_sonido_de(nodo), disponibles, nombres):
            hallazgos.append(Hallazgo(archivo, nodo.lineno))
    return sorted(hallazgos, key=lambda hallazgo: hallazgo.linea)


def _clave_de_sonido(nodo: ast.expr | None,
                     constantes: dict[str, str]) -> str | None:
    if isinstance(nodo, ast.Constant) and isinstance(nodo.value, str):
        return nodo.value
    if isinstance(nodo, ast.Name):
        return constantes.get(nodo.id)
    return None


def _pide_error(llamada: ast.Call) -> bool:
    return any(palabra.arg == "error"
               and isinstance(palabra.value, ast.Constant)
               and palabra.value.value is True
               for palabra in llamada.keywords)


def detectar_avisar_error(archivo: str,
                          arbol: ast.Module) -> list[Hallazgo]:
    funciones, modulos = _nombres_avisar(arbol)
    constantes = _constantes_de_sonido(arbol, eventos_de_sonido())
    hallazgos = []
    for nodo in ast.walk(arbol):
        if not isinstance(nodo, ast.Call):
            continue
        if not _es_llamada_avisar(nodo.func, funciones, modulos):
            continue
        if not _pide_error(nodo):
            continue
        clave = _clave_de_sonido(_sonido_de(nodo), constantes)
        if clave is not None and FAMILIAS.get(clave) not in FAMILIAS_DE_ERROR:
            hallazgos.append(Hallazgo(archivo, nodo.lineno))
    return sorted(hallazgos, key=lambda hallazgo: hallazgo.linea)
