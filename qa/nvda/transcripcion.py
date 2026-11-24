# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Cómo se escribe la transcripción de una ventana del carril.

Arma una línea por paso con la tecla, la fase, lo que NVDA dijo y los datos
del foco, lee y escribe la transcripción aprobada, y devuelve el diff cuando
la nueva difiere. Es puro: no toca NVDA, ni Windows, ni ventanas.
"""

from __future__ import annotations

import difflib
import re
from pathlib import Path

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


def _sin_carpeta_app(valor):
    """Escribe <carpeta de la app> la raíz del árbol que cambia por PC.

    Windows no distingue mayúsculas en las rutas y la transcripción muestra
    las barras dobladas por `repr`, así que el patrón admite una o dos barras
    y compara sin mirar el caso. Medido el 24/11/2026.
    """
    if not isinstance(valor, str):
        return valor
    patron = re.escape(str(CARPETA_APP)).replace(r"\\", r"\\{1,2}")
    return re.sub(patron, "<carpeta de la app>", valor,
                  flags=re.IGNORECASE)


def _linea(paso, valor_variable=()) -> str:
    foco = paso.get("foco") or {}
    variable = foco.get("nombre") in valor_variable
    estados = sorted(str(estado) for estado in foco.get("estados") or ()
                     if str(estado).casefold() != "focused")
    rol = foco.get("rol_nombre") or foco.get("rol")
    valor = "" if variable else _sin_carpeta_app(
        _sin_temporal(foco.get("valor")))
    linea = (f"tecla={paso.get('tecla')} fase={paso.get('fase')} "
             f"dijo={_sin_carpeta_app(_sin_temporal(_habla(paso, variable)))!r} "
             f"foco={{nombre={foco.get('nombre')!r}, "
             f"rol={rol!r}, estados={estados!r}, "
             f"valor={valor!r}, atajo={foco.get('atajo')!r}}}")
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
    lineas = [_linea(paso, valor_variable)
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
