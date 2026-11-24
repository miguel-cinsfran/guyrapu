# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Cómo se escribe la transcripción de una ventana del carril.

Arma una línea por paso con la tecla, la fase, lo que NVDA dijo y los datos
del foco, lee y escribe la transcripción aprobada, y devuelve el diff cuando
la nueva difiere. No toca NVDA ni ventanas: los valores de la PC y su marcador
viven en `qa/valores_de_la_pc.py`.
"""

from __future__ import annotations

import difflib
import re
from pathlib import Path

from qa import valores_de_la_pc

CARPETA = Path(__file__).resolve().parent / "transcripciones"
CANDIDATAS = Path(__file__).resolve().parents[2] / "qa" / "salida" / "nvda" / "candidatas"

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


def _linea(paso, valor_variable=(), valores=()) -> str:
    foco = paso.get("foco") or {}
    variable = foco.get("nombre") in valor_variable
    estados = sorted(str(estado) for estado in foco.get("estados") or ()
                     if str(estado).casefold() != "focused")
    rol = foco.get("rol_nombre") or foco.get("rol")
    dicho = valores_de_la_pc.normalizar(
        _sin_temporal(_habla(paso, variable)), valores)
    valor = ("" if variable else
             valores_de_la_pc.normalizar(
                 _sin_temporal(foco.get("valor")), valores))
    atajo = valores_de_la_pc.normalizar(foco.get("atajo"), valores)
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
    valores = valores_de_la_pc.calcular()
    lineas = [_linea(paso, valor_variable, valores)
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
