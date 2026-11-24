# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Cómo se escribe la transcripción de una ventana del carril.

Arma una línea por paso con la tecla, la fase, lo que NVDA dijo y los datos
del foco, lee y escribe la transcripción aprobada, y devuelve el diff cuando
la nueva difiere. No toca NVDA ni ventanas: lo único que lee de la PC son las
voces y el carácter de las teclas físicas, y la tabla de entradas lo escribe
con marcador.
"""

from __future__ import annotations

import difflib
import logging
import re
from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple

from guyrapu.core import atajos, tecla_fisica
from guyrapu.voice import motores

logger = logging.getLogger(__name__)

CARPETA = Path(__file__).resolve().parent / "transcripciones"
CANDIDATAS = Path(__file__).resolve().parents[2] / "qa" / "salida" / "nvda" / "candidatas"
CARPETA_APP = Path(__file__).resolve().parents[2]

_TEMPORAL = re.compile(r"[A-Za-z]:\\(?:[^\\]+\\)*Temp\\tmp[^\\]*",
                       re.IGNORECASE)


def _sin_repeticion_final(dicho, nombre):
    """Quita el tramo final repetido que empieza con el nombre del foco."""
    if not nombre:
        return dicho
    inicio = dicho.rfind(nombre)
    while inicio != -1:
        if inicio == 0 or dicho[inicio - 1] == " ":
            tramo = dicho[inicio:]
            if dicho.endswith(f"{tramo} {tramo}"):
                return dicho[:-len(tramo) - 1]
        inicio = dicho.rfind(nombre, 0, inicio)
    return dicho


def _habla(paso, variable=False) -> str:
    dicho = " ".join(str(evento.get("texto") or "")
                     for evento in paso.get("habla") or ()).strip()
    nombre = str((paso.get("foco") or {}).get("nombre") or "").strip()
    dicho = _sin_repeticion_final(dicho, nombre)
    if variable:
        atajo = str((paso.get("foco") or {}).get("atajo") or "").strip()
        for forma in (atajo.replace("+", "+ "), atajo):
            if forma:
                pos = dicho.casefold().find(forma.casefold())
                if pos != -1:
                    return dicho[:pos + len(forma)].rstrip()
    return dicho


def _sin_temporal(valor):
    """Escribe <temporal> la ruta de la carpeta que cambia en cada corrida."""
    if not isinstance(valor, str):
        return valor
    return _TEMPORAL.sub("<temporal>", valor)


class Entrada(NamedTuple):
    """De dónde salen los valores de esta PC y cómo se escriben en la línea."""

    valores: Callable[[], list[tuple[str, str]]]
    aplicar: Callable[[str, list[tuple[str, str]]], str]


def aplicar_texto(texto, pares):
    """Escribe el marcador de cada valor, primero el más largo."""
    for valor, marcador in sorted(pares, key=lambda par: len(par[0]),
                                  reverse=True):
        if valor:
            texto = texto.replace(valor, marcador)
    return texto


def aplicar_carpeta(texto, pares):
    """Escribe <carpeta de la app> la raíz del árbol que cambia por PC.

    Windows no distingue mayúsculas en las rutas y la transcripción muestra
    las barras dobladas por `repr`, así que el patrón admite una o dos barras
    y compara sin mirar el caso. Medido el 24/11/2026.
    """
    for valor, marcador in pares:
        patron = re.escape(valor).replace(r"\\", r"\\{1,2}")
        texto = re.sub(patron, marcador, texto, flags=re.IGNORECASE)
    return texto


_COMBINACION = re.compile(r"[^\s,;()\"]+(?:\+[^\s,;()\"]+)+")


def aplicar_teclas(texto, pares):
    """Escribe el marcador de la tecla física solo dentro de combinaciones."""
    return _COMBINACION.sub(
        lambda combinacion: aplicar_texto(combinacion.group(), pares), texto)


def valores_carpeta():
    return [(str(CARPETA_APP), "<carpeta de la app>")]


def valores_voces():
    pares = []
    for motor in ("sapi", "onecore"):
        try:
            nombres = motores.listar_voces(motor)
        except Exception as exc:
            logger.warning("no se pudieron listar las voces de %s: %s",
                           motor, exc)
            continue
        pares.extend((nombre, "<voz de Windows>") for nombre in nombres)
    return pares


def valores_teclas():
    pares = []
    for valores in (atajos.ATAJOS_FIJOS_DEFAULTS, atajos.ATAJOS_DEFAULTS):
        for valor in valores.values():
            for parte in valor.split("+"):
                if (len(parte) == 4 and parte.startswith("sc")
                        and all(c in "0123456789abcdef" for c in parte[2:])):
                    caracter = tecla_fisica.texto_tecla(int(parte[2:], 16))
                    if caracter:
                        pares.append((caracter, f"<tecla {parte}>"))
    return pares


# Lo que cambia por PC se declara acá una sola vez: de dónde salen los
# valores de esta PC y qué marcador llevan. Sumar otro valor es sumar su
# entrada.
ENTRADAS = (
    Entrada(valores_carpeta, aplicar_carpeta),
    Entrada(valores_voces, aplicar_texto),
    Entrada(valores_teclas, aplicar_teclas),
)


def normalizar(texto, valores_de_la_pc):
    if not isinstance(texto, str):
        return texto
    for entrada, valores in zip(ENTRADAS, valores_de_la_pc):
        texto = entrada.aplicar(texto, valores)
    return texto


def _linea(paso, valor_variable=(), valores_de_la_pc=()) -> str:
    foco = paso.get("foco") or {}
    variable = foco.get("nombre") in valor_variable
    estados = sorted(str(estado) for estado in foco.get("estados") or ()
                     if str(estado).casefold() != "focused")
    rol = foco.get("rol_nombre") or foco.get("rol")
    dicho = normalizar(_sin_temporal(_habla(paso, variable)), valores_de_la_pc)
    valor = ("" if variable else
             normalizar(_sin_temporal(foco.get("valor")), valores_de_la_pc))
    atajo = normalizar(foco.get("atajo"), valores_de_la_pc)
    linea = (f"tecla={paso.get('tecla')} fase={paso.get('fase')} "
             f"dijo={dicho!r} "
             f"foco={{nombre={foco.get('nombre')!r}, "
             f"rol={rol!r}, estados={estados!r}, "
             f"valor={valor!r}, atajo={atajo!r}}}")
    if paso.get("espera"):
        linea += (f" espera={paso['espera']!r} "
                  f"oída={bool(paso.get('oida'))}")
    sonidos = paso.get("sonidos") or []
    if sonidos:
        linea += f" sonó={[str(sonido) for sonido in sonidos]!r}"
    return linea


def texto(datos, valor_variable=()) -> str:
    """Una línea por paso, sin horas, milisegundos, hwnd ni pid.

    Los pasos de fase `pagina` no se escriben: solo sirven para llegar a la
    página que deja abierta la ventana anterior. Los nombres en
    `valor_variable` escriben el habla hasta el atajo y dejan el valor vacío:
    su contenido cambia según la PC y no es de la app.
    """
    valores_de_la_pc = [entrada.valores() for entrada in ENTRADAS]
    lineas = [_linea(paso, valor_variable, valores_de_la_pc)
              for paso in datos.get("pasos") or ()
              if paso.get("fase") != "pagina"]
    return "\n".join(lineas) + ("\n" if lineas else "")


def diferencia(aprobada: str, nueva: str) -> str:
    return "".join(difflib.unified_diff(
        aprobada.splitlines(keepends=True),
        nueva.splitlines(keepends=True),
        fromfile="aprobada", tofile="nueva"))


def _ruta(nombre, carpeta=None) -> Path:
    return Path(carpeta or CARPETA) / f"{nombre}.txt"


def leer(nombre, carpeta=None):
    """La transcripción aprobada, o None si todavía no hay."""
    try:
        return _ruta(nombre, carpeta).read_text(encoding="utf-8")
    except FileNotFoundError:
        return None


def escribir(nombre, contenido, carpeta=None) -> Path:
    ruta = _ruta(nombre, carpeta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(contenido, encoding="utf-8", newline="\n")
    return ruta


def comparar(nombre, nueva, aprobar=False, carpeta=None) -> str:
    """Guarda la aprobada y deja la nueva como candidata si cambió."""
    aprobada = leer(nombre, carpeta)
    if aprobar or aprobada is None:
        escribir(nombre, nueva, carpeta)
        _ruta(nombre, CANDIDATAS).unlink(missing_ok=True)
        return ""
    diff = diferencia(aprobada, nueva)
    if diff:
        escribir(nombre, nueva, CANDIDATAS)
    else:
        _ruta(nombre, CANDIDATAS).unlink(missing_ok=True)
    return diff
