# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Detectores y revisión de las reglas de arquitectura, con ast.

Leen archivos, no importan wx ni la aplicación. La tabla de reglas vive en
tests/reglas_arquitectura.py.
"""

from __future__ import annotations

import ast
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple

from guyrapu.core.eventos_sonido import EVENTOS as EVENTOS_SONIDO

if TYPE_CHECKING:
    from tests.reglas_arquitectura import Regla

RAIZ = Path(__file__).resolve().parent.parent
FUENTES = RAIZ / "guyrapu"
MAIN = RAIZ / "main.py"

ATRIBUTOS_CUADRO = {"MessageBox", "MessageDialog"}


class Hallazgo(NamedTuple):
    archivo: str
    linea: int


def _termina_en_wx(nodo: ast.expr) -> bool:
    if isinstance(nodo, ast.Name):
        return nodo.id == "wx"
    return isinstance(nodo, ast.Attribute) and nodo.attr == "wx"


def detectar_cuadros(archivo: str, arbol: ast.Module) -> list[Hallazgo]:
    hallazgos = [
        Hallazgo(archivo, nodo.lineno)
        for nodo in ast.walk(arbol)
        if isinstance(nodo, ast.Attribute)
        and nodo.attr in ATRIBUTOS_CUADRO
        and _termina_en_wx(nodo.value)
    ]
    return sorted(hallazgos, key=lambda hallazgo: hallazgo.linea)


def _modulo_ui(nombre: str) -> bool:
    return nombre == "guyrapu.ui" or nombre.startswith("guyrapu.ui.")


def detectar_capas(archivo: str, arbol: ast.Module) -> list[Hallazgo]:
    hallazgos = []
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            hallazgos.extend(Hallazgo(archivo, nodo.lineno)
                             for alias in nodo.names if _modulo_ui(alias.name))
        elif isinstance(nodo, ast.ImportFrom) and _modulo_ui(nodo.module or ""):
            hallazgos.append(Hallazgo(archivo, nodo.lineno))
    return sorted(hallazgos, key=lambda hallazgo: hallazgo.linea)


def _modulo_red(nombre: str) -> bool:
    raices = ("urllib.request", "httpx", "requests")
    return any(nombre == raiz or nombre.startswith(raiz + ".") for raiz in raices)


def detectar_red(archivo: str, arbol: ast.Module) -> list[Hallazgo]:
    hallazgos = []
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            hallazgos.extend(Hallazgo(archivo, nodo.lineno)
                             for alias in nodo.names if _modulo_red(alias.name))
        elif isinstance(nodo, ast.ImportFrom):
            modulo = nodo.module or ""
            if _modulo_red(modulo):
                hallazgos.append(Hallazgo(archivo, nodo.lineno))
            elif modulo == "urllib" and any(alias.name == "request"
                                            for alias in nodo.names):
                hallazgos.append(Hallazgo(archivo, nodo.lineno))
    return sorted(hallazgos, key=lambda hallazgo: hallazgo.linea)


def detectar_escape(archivo: str, arbol: ast.Module) -> list[Hallazgo]:
    hallazgos = [
        Hallazgo(archivo, nodo.lineno)
        for nodo in ast.walk(arbol)
        if (isinstance(nodo, ast.Name) and nodo.id == "WXK_ESCAPE")
        or (isinstance(nodo, ast.Attribute) and nodo.attr == "WXK_ESCAPE")
    ]
    return sorted(hallazgos, key=lambda hallazgo: hallazgo.linea)


@lru_cache(maxsize=None)
def eventos_de_sonido() -> frozenset[str]:
    return frozenset(EVENTOS_SONIDO)


def _nombres_avisar(arbol: ast.Module) -> tuple[set[str], set[str]]:
    funciones: set[str] = set()
    modulos: set[str] = set()
    for nodo in ast.walk(arbol):
        if not isinstance(nodo, ast.ImportFrom):
            continue
        modulo = nodo.module or ""
        if modulo == "guyrapu.ui.aviso_importante":
            funciones.update(alias.asname or alias.name
                             for alias in nodo.names
                             if alias.name == "avisar")
        elif modulo == "guyrapu.ui":
            modulos.update(alias.asname or alias.name
                           for alias in nodo.names
                           if alias.name == "aviso_importante")
    return funciones, modulos


def _es_llamada_avisar(func: ast.expr, funciones: set[str],
                       modulos: set[str]) -> bool:
    if isinstance(func, ast.Name):
        return func.id in funciones
    return (isinstance(func, ast.Attribute)
            and func.attr == "avisar"
            and isinstance(func.value, ast.Name)
            and func.value.id in modulos)


def _sonido_de(llamada: ast.Call) -> ast.expr | None:
    sonido = llamada.args[1] if len(llamada.args) >= 2 else None
    for palabra in llamada.keywords:
        if palabra.arg == "sonido":
            sonido = palabra.value
    return sonido


def _sonido_valido(nodo: ast.expr | None, eventos: frozenset[str]) -> bool:
    if not (isinstance(nodo, ast.Constant) and isinstance(nodo.value, str)):
        return False
    return bool(nodo.value) and nodo.value in eventos


def detectar_avisar(archivo: str, arbol: ast.Module,
                    eventos: frozenset[str] | None = None) -> list[Hallazgo]:
    funciones, modulos = _nombres_avisar(arbol)
    disponibles = eventos_de_sonido() if eventos is None else eventos
    hallazgos = []
    for nodo in ast.walk(arbol):
        if not isinstance(nodo, ast.Call):
            continue
        if not _es_llamada_avisar(nodo.func, funciones, modulos):
            continue
        if not _sonido_valido(_sonido_de(nodo), disponibles):
            hallazgos.append(Hallazgo(archivo, nodo.lineno))
    return sorted(hallazgos, key=lambda hallazgo: hallazgo.linea)


def _enable_prohibido(llamada: ast.Call) -> bool:
    total = len(llamada.args) + len(llamada.keywords)
    if total != 1:
        return False
    argumento = llamada.args[0] if llamada.args else llamada.keywords[0].value
    return not (isinstance(argumento, ast.Constant) and argumento.value is True)


def detectar_controles(archivo: str, arbol: ast.Module) -> list[Hallazgo]:
    hallazgos = []
    for nodo in ast.walk(arbol):
        if not isinstance(nodo, ast.Call):
            continue
        if not isinstance(nodo.func, ast.Attribute):
            continue
        if nodo.func.attr == "Disable":
            hallazgos.append(Hallazgo(archivo, nodo.lineno))
        elif nodo.func.attr == "Enable" and _enable_prohibido(nodo):
            hallazgos.append(Hallazgo(archivo, nodo.lineno))
    return sorted(hallazgos, key=lambda hallazgo: hallazgo.linea)


def _todo(archivo: str) -> bool:
    return True


def _paquete(archivo: str) -> bool:
    return archivo.startswith("guyrapu/")


def _controles(archivo: str) -> bool:
    return archivo.startswith(("guyrapu/ui/", "guyrapu/player/"))


def _rutas() -> list[Path]:
    return [*sorted(FUENTES.rglob("*.py")), MAIN]


def hallazgos_por_archivo(regla: Regla) -> dict[str, list[Hallazgo]]:
    resultado: dict[str, list[Hallazgo]] = {}
    for ruta in _rutas():
        archivo = ruta.relative_to(RAIZ).as_posix()
        if not regla.ambito(archivo):
            continue
        arbol = ast.parse(ruta.read_text(encoding="utf-8"), filename=archivo)
        encontrados = regla.detectar(archivo, arbol)
        if encontrados:
            resultado[archivo] = encontrados
    return resultado


def _es_dueno(regla: Regla, archivo: str) -> bool:
    for dueno in regla.duenos:
        if dueno.endswith("/"):
            if archivo.startswith(dueno):
                return True
        elif archivo == dueno:
            return True
    return False


def revisar(regla: Regla, hallazgos: dict[str, list[Hallazgo]]):
    ajenos = []
    for archivo, encontrados in hallazgos.items():
        if _es_dueno(regla, archivo):
            continue
        if archivo not in regla.pendientes:
            ajenos.extend(encontrados)
    ajenos.sort(key=lambda hallazgo: (hallazgo.archivo, hallazgo.linea))
    vencidos = []
    for archivo, pendiente in regla.pendientes.items():
        real = len(hallazgos.get(archivo, ()))
        if real != pendiente.cantidad:
            vencidos.append((archivo, pendiente.cantidad, real))
    return ajenos, vencidos


def detalle_ajenos(regla: Regla, ajenos: list[Hallazgo]) -> str:
    if not ajenos:
        return ""
    lineas = [f"{hallazgo.archivo}:{hallazgo.linea}: {regla.prohibido}"
              for hallazgo in ajenos]
    return (f"La regla {regla.id} encontró código prohibido en archivos "
            "que no son dueños ni están en pendientes:\n" + "\n".join(lineas))


def detalle_vencidos(regla: Regla, vencidos: list[tuple[str, int, int]]) -> str:
    if not vencidos:
        return ""
    lineas = []
    for archivo, esperada, real in vencidos:
        if real == 0:
            lineas.append(f"{archivo}: ya no tiene lo prohibido por {regla.id}. "
                          "Sacalo de pendientes.")
        elif real < esperada:
            lineas.append(f"{archivo}: tiene {real} caso(s) y la lista dice "
                          f"{esperada}. Bajá la cantidad.")
        else:
            lineas.append(f"{archivo}: tiene {real} caso(s) y la lista dice "
                          f"{esperada}. No agregues casos a un archivo pendiente: "
                          "arreglalos en el código.")
    return (f"Los pendientes de {regla.id} no coinciden con el código:\n"
            + "\n".join(lineas))
