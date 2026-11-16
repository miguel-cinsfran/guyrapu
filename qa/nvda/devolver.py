# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Devuelve el NVDA de la PC. Es lo que corre la tarea de respaldo.

Lee el estado que anotó el carril antes de cerrar el NVDA de la PC y hace
una de tres cosas: arrancar el ejecutable anotado, cerrar la copia portátil
si antes no había ninguna, o nada si ya está devuelto. Al terminar bien,
borra el estado. Si no hay estado, no hace nada.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from qa.nvda import nvda_local, perfil  # noqa: E402


def _misma_ruta(una, otra) -> bool:
    if not una or not otra:
        return False
    return (os.path.normcase(os.path.abspath(str(una)))
            == os.path.normcase(os.path.abspath(str(otra))))


def decidir_devolucion(estado, actual, ruta_portatil, instalado):
    """(acción, ejecutable) para volver a dejar el NVDA como estaba.

    Acciones: «nada», «cerrar» y «lanzar». `actual` es lo que corre ahora,
    con la forma que devuelve `nvda_local.nvda_en_marcha`.
    """
    if estado is None:
        return "nada", None
    anotado = str(estado.get("ejecutable") or "")
    actual_exe = (actual or {}).get("ejecutable") or ""
    if not estado.get("habia"):
        if perfil.dentro_de(actual_exe, ruta_portatil):
            return "cerrar", None
        return "nada", None
    if actual:
        if anotado and _misma_ruta(actual_exe, anotado):
            return "nada", None
        if perfil.dentro_de(actual_exe, ruta_portatil):
            return "lanzar", str(instalado)
        return "nada", None
    if not anotado or perfil.dentro_de(anotado, ruta_portatil):
        return "lanzar", str(instalado)
    return "lanzar", anotado


def leer_estado(ruta):
    try:
        with open(ruta, encoding="utf-8") as archivo:
            return json.load(archivo)
    except FileNotFoundError:
        return None
    except (OSError, ValueError) as exc:
        print(f"estado del carril ilegible: {exc}")
        return None


def ejecutar_devolucion(ruta_estado, ruta_portatil, instalado) -> bool:
    """Deja el NVDA como estaba y dice si lo logró.

    Con «nada» ya estaba devuelto, con «lanzar» se arrancó el ejecutable y
    con «cerrar» solo se da por bueno si el portátil terminó de cerrarse.
    """
    try:
        estado = leer_estado(ruta_estado)
        actual = nvda_local.nvda_en_marcha()
        accion, destino = decidir_devolucion(
            estado, actual, ruta_portatil, instalado)
        if accion == "cerrar":
            if not nvda_local.cerrar(actual):
                print("no se pudo cerrar la copia portátil")
                return False
        elif accion == "lanzar":
            nvda_local.lanzar(destino)
        if estado is not None:
            Path(ruta_estado).unlink(missing_ok=True)
        return True
    except OSError as exc:
        print(f"No se pudo devolver el NVDA: {exc}")
        return False


def main() -> int:
    version = perfil.version_esperada()
    ruta_portatil = perfil.ruta_portatil(version)
    instalado = nvda_local.instalado_por_defecto()
    devuelto = ejecutar_devolucion(
        perfil.ruta_estado(), ruta_portatil, instalado)
    print("devolución del carril: " + ("hecha" if devuelto else "falló"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
