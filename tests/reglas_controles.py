# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Detectores de las reglas sobre controles y confirmaciones, con ast.

Leen archivos, no importan wx ni la aplicación. R11 a R15.
"""

from __future__ import annotations

import ast

from tests.reglas_detectores import (
    Hallazgo,
    _recorrer_sin_funciones,
    _termina_en_wx,
)

CONSTRUCTORES = frozenset((
    "Button", "CheckBox", "RadioButton", "TextCtrl", "Choice", "ComboBox",
    "ListBox", "ListCtrl", "CheckListBox", "Slider", "SpinCtrl",
    "ToggleButton"))
ROTULADOS = frozenset(("Button", "CheckBox", "RadioButton"))


def _nombres_preguntar(arbol: ast.Module) -> tuple[set[str], set[str]]:
    funciones: set[str] = set()
    modulos: set[str] = set()
    for nodo in ast.walk(arbol):
        if not isinstance(nodo, ast.ImportFrom):
            continue
        modulo = nodo.module or ""
        if modulo == "guyrapu.ui.confirmar":
            funciones.update(alias.asname or alias.name
                             for alias in nodo.names
                             if alias.name == "preguntar")
        elif modulo == "guyrapu.ui":
            modulos.update(alias.asname or alias.name
                           for alias in nodo.names
                           if alias.name == "confirmar")
    return funciones, modulos


def _es_llamada_preguntar(func: ast.expr, funciones: set[str],
                          modulos: set[str]) -> bool:
    if isinstance(func, ast.Name):
        return func.id in funciones
    return (isinstance(func, ast.Attribute)
            and func.attr == "preguntar"
            and isinstance(func.value, ast.Name)
            and func.value.id in modulos)


def _predeterminado_explicito(llamada: ast.Call) -> bool:
    return any(palabra.arg == "predeterminado_si"
               for palabra in llamada.keywords)


def detectar_predeterminado(archivo: str,
                            arbol: ast.Module) -> list[Hallazgo]:
    funciones, modulos = _nombres_preguntar(arbol)
    hallazgos = [
        Hallazgo(archivo, nodo.lineno)
        for nodo in ast.walk(arbol)
        if isinstance(nodo, ast.Call)
        and _es_llamada_preguntar(nodo.func, funciones, modulos)
        and not _predeterminado_explicito(nodo)
    ]
    return sorted(hallazgos, key=lambda hallazgo: hallazgo.linea)


def _referencia(nodo: ast.expr) -> tuple | None:
    if isinstance(nodo, ast.Name):
        return ("nombre", nodo.id)
    if isinstance(nodo, ast.Attribute):
        base = _referencia(nodo.value)
        if base is not None:
            return ("atributo", base, nodo.attr)
    return None


def _destinos(llamada: ast.Call, nodos) -> list[tuple]:
    destinos = []
    for nodo in nodos:
        if isinstance(nodo, ast.Assign) and nodo.value is llamada:
            destinos.extend(_referencia(objetivo) for objetivo in nodo.targets)
        elif isinstance(nodo, ast.AnnAssign) and nodo.value is llamada:
            destinos.append(_referencia(nodo.target))
    return [destino for destino in destinos if destino is not None]


def _es_constructor(nodo: ast.Call) -> bool:
    return (isinstance(nodo.func, ast.Attribute)
            and nodo.func.attr in CONSTRUCTORES
            and _termina_en_wx(nodo.func.value))


def _es_nombre_accesible(nodo: ast.Call) -> bool:
    return ((isinstance(nodo.func, ast.Name)
             and nodo.func.id == "nombre_accesible")
            or (isinstance(nodo.func, ast.Attribute)
                and nodo.func.attr == "nombre_accesible"))


def _nombre_de(llamada: ast.Call) -> ast.expr | None:
    for palabra in llamada.keywords:
        if palabra.arg == "name":
            return palabra.value
    return None


def _ambitos(arbol: ast.Module):
    for nodo in ast.walk(arbol):
        if isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield nodo.body
    yield arbol.body


def detectar_nombres_de_control(archivo: str,
                                arbol: ast.Module) -> list[Hallazgo]:
    hallazgos = []
    for cuerpo in _ambitos(arbol):
        nodos = list(_recorrer_sin_funciones(cuerpo))
        llamadas = [nodo for nodo in nodos if isinstance(nodo, ast.Call)]
        nombrados = {
            (_referencia(llamada.args[0]), llamada.lineno)
            for llamada in llamadas
            if _es_nombre_accesible(llamada) and llamada.args
            and _referencia(llamada.args[0]) is not None
        }
        for llamada in llamadas:
            if not _es_constructor(llamada):
                continue
            nombre = _nombre_de(llamada)
            if nombre is not None:
                if isinstance(nombre, ast.Constant) and nombre.value == "":
                    hallazgos.append(Hallazgo(archivo, llamada.lineno))
                continue
            posteriores = {destino for destino, linea in nombrados
                           if linea > llamada.lineno}
            if not any(destino in posteriores
                       for destino in _destinos(llamada, nodos)):
                hallazgos.append(Hallazgo(archivo, llamada.lineno))
    return sorted(hallazgos, key=lambda hallazgo: hallazgo.linea)


def _etiqueta(llamada: ast.Call) -> ast.expr | None:
    for palabra in llamada.keywords:
        if palabra.arg == "label":
            return palabra.value
    if len(llamada.args) >= 3:
        return llamada.args[2]
    return None


def _traduccion_literal(nodo: ast.expr | None) -> bool:
    return (isinstance(nodo, ast.Call)
            and isinstance(nodo.func, ast.Name)
            and nodo.func.id == "_"
            and bool(nodo.args)
            and isinstance(nodo.args[0], ast.Constant)
            and isinstance(nodo.args[0].value, str))


def _cantidad_mnemonicos(texto: str) -> int:
    cantidad = 0
    indice = 0
    while indice < len(texto):
        if texto[indice] == "&":
            if indice + 1 < len(texto) and texto[indice + 1] == "&":
                indice += 2
                continue
            cantidad += 1
        indice += 1
    return cantidad


def detectar_mnemonico(archivo: str, arbol: ast.Module) -> list[Hallazgo]:
    hallazgos = []
    for nodo in ast.walk(arbol):
        if not (isinstance(nodo, ast.Call)
                and isinstance(nodo.func, ast.Attribute)
                and nodo.func.attr in ROTULADOS
                and _termina_en_wx(nodo.func.value)):
            continue
        etiqueta = _etiqueta(nodo)
        # Los rótulos que no son _("...") literal (variables, f-strings o una
        # cadena vacía que se rellena después) no se reconocen leyendo el
        # código y no se juzgan.
        if not _traduccion_literal(etiqueta):
            continue
        texto = etiqueta.args[0].value
        if texto == "":
            continue
        if _cantidad_mnemonicos(texto) != 1:
            hallazgos.append(Hallazgo(archivo, nodo.lineno))
    return sorted(hallazgos, key=lambda hallazgo: hallazgo.linea)


def _es_notebook(nodo: ast.Call) -> bool:
    return (isinstance(nodo.func, ast.Attribute)
            and nodo.func.attr == "Notebook"
            and _termina_en_wx(nodo.func.value))


def _es_enlace_de_pestana(func: ast.expr) -> bool:
    return ((isinstance(func, ast.Name)
             and func.id == "enlazar_anuncio_de_pestana")
            or (isinstance(func, ast.Attribute)
                and func.attr == "enlazar_anuncio_de_pestana"))


def _pestanas_anunciadas(nodos) -> set[tuple]:
    anunciadas = set()
    for nodo in nodos:
        if (isinstance(nodo, ast.Call) and nodo.args
                and _es_enlace_de_pestana(nodo.func)):
            referencia = _referencia(nodo.args[0])
            if referencia is not None:
                anunciadas.add(referencia)
    return anunciadas


def detectar_pestana_sin_anuncio(archivo: str,
                                 arbol: ast.Module) -> list[Hallazgo]:
    nodos = list(ast.walk(arbol))
    anunciadas = _pestanas_anunciadas(nodos)
    hallazgos = []
    for nodo in nodos:
        if not (isinstance(nodo, ast.Call) and _es_notebook(nodo)):
            continue
        destinos = _destinos(nodo, nodos)
        if not destinos or not all(destino in anunciadas
                                   for destino in destinos):
            hallazgos.append(Hallazgo(archivo, nodo.lineno))
    return sorted(hallazgos, key=lambda hallazgo: hallazgo.linea)


BASES_CUADRO = frozenset(("Dialog", "Frame"))
BOTONES = frozenset(("Button", "boton", "_boton"))


def _es_base_de_cuadro(base: ast.expr) -> bool:
    return (isinstance(base, ast.Attribute)
            and base.attr in BASES_CUADRO
            and _termina_en_wx(base.value))


def _es_id_cancel(nodo: ast.expr) -> bool:
    return (isinstance(nodo, ast.Attribute) and nodo.attr == "ID_CANCEL"
            and _termina_en_wx(nodo.value))


def _nombre_de_llamada(func: ast.expr) -> str | None:
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _tiene_boton_cancelar(llamada: ast.Call) -> bool:
    return (_nombre_de_llamada(llamada.func) in BOTONES
            and any(_es_id_cancel(argumento)
                    for argumento in (*llamada.args,
                                      *(palabra.value
                                        for palabra in llamada.keywords))))


def _tiene_via_de_escape(clase: ast.ClassDef) -> bool:
    for nodo in ast.walk(clase):
        if isinstance(nodo, ast.Name) and nodo.id in (
                "tecla_escape", "WXK_ESCAPE"):
            return True
        if isinstance(nodo, ast.Attribute) and nodo.attr in (
                "SetEscapeId", "tecla_escape", "WXK_ESCAPE"):
            return True
        if isinstance(nodo, ast.Call) and _tiene_boton_cancelar(nodo):
            return True
        if isinstance(nodo, ast.Import) and any(
                alias.name.endswith("tecla_escape") for alias in nodo.names):
            return True
        if isinstance(nodo, ast.ImportFrom) and (
                (nodo.module or "").endswith("tecla_escape")
                or any(alias.name == "tecla_escape" for alias in nodo.names)):
            return True
    return False


def detectar_cuadro_sin_escape(archivo: str,
                               arbol: ast.Module) -> list[Hallazgo]:
    # La ventana principal no se cierra con Escape a propósito: es la ventana
    # de la aplicación y Escape no debe apagarla.
    if archivo == "guyrapu/ui/gui.py":
        return []
    hallazgos = [
        Hallazgo(archivo, nodo.lineno)
        for nodo in ast.walk(arbol)
        if isinstance(nodo, ast.ClassDef)
        and any(_es_base_de_cuadro(base) for base in nodo.bases)
        and not _tiene_via_de_escape(nodo)
    ]
    return sorted(hallazgos, key=lambda hallazgo: hallazgo.linea)
