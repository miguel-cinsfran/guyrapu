# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Compara la geometría aprobada de las vistas de la galería con una corrida.

Lee los JSON de una carpeta de la galería y los compara con los aprobados en
el repositorio. No abre ventanas ni importa wx.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

APROBADAS = Path(__file__).resolve().parent / "visual" / "aprobadas"

# De cada control se compara solo lo que dibuja: posición, tamaño, texto y
# colores. `id` y `padre` son números de ventana que wx reasigna en cada
# proceso y cambian sin tocar el código; el orden de `controles` también puede
# variar, por eso se empareja por nombre y clase. Medido el 24/11/2026 sobre
# dos corridas de la galería con la misma geometría.

_DETALLES = {
    "movido": "movido de {antes} a {despues}",
    "tamaño": "cambió de tamaño de {antes} a {despues}",
    "texto": "cambió de texto de «{antes}» a «{despues}»",
    "fg": "cambió de color de texto de {antes} a {despues}",
    "bg": "cambió de color de fondo de {antes} a {despues}",
    "apareció": "apareció",
    "se fue": "se fue",
}


def _nombres(carpeta):
    return sorted(ruta.stem for ruta in carpeta.glob("*.json"))


def leer(carpeta):
    """Las vistas de los `*.json` de una carpeta, por nombre de archivo."""
    return {nombre: json.loads(
        (carpeta / (nombre + ".json")).read_text(encoding="utf-8"))
        for nombre in _nombres(carpeta)}


def _cambio(control, tipo, antes, despues):
    return {"control": control["nombre"], "clase": control["clase"],
            "tipo": tipo, "antes": antes, "despues": despues}


def _diferencias_control(aprobado, corrido):
    cambios = []
    antes, despues = aprobado["rect"], corrido["rect"]
    if antes[:2] != despues[:2]:
        cambios.append(_cambio(aprobado, "movido", antes[:2], despues[:2]))
    if antes[2:] != despues[2:]:
        cambios.append(_cambio(aprobado, "tamaño", antes[2:], despues[2:]))
    for campo, tipo in (("etiqueta", "texto"), ("fg", "fg"), ("bg", "bg")):
        if aprobado[campo] != corrido[campo]:
            cambios.append(_cambio(aprobado, tipo,
                                   aprobado[campo], corrido[campo]))
    return cambios


def _agrupar(controles):
    grupos = {}
    for control in controles:
        clave = (control["nombre"], control["clase"])
        grupos.setdefault(clave, []).append(control)
    return grupos


def _comparar_grupo(aprobados, corridos):
    cambios = []
    for antes, despues in zip(aprobados, corridos):
        cambios.extend(_diferencias_control(antes, despues))
    for control in aprobados[len(corridos):]:
        cambios.append(_cambio(control, "se fue", None, None))
    for control in corridos[len(aprobados):]:
        cambios.append(_cambio(control, "apareció", None, None))
    return cambios


def comparar_vistas(aprobada, corrida):
    """Los cambios de una vista, con los controles emparejados por identidad."""
    aprobados = _agrupar(aprobada["controles"])
    corridos = _agrupar(corrida["controles"])
    cambios = []
    for clave in sorted(set(aprobados) | set(corridos)):
        cambios.extend(_comparar_grupo(aprobados.get(clave, []),
                                       corridos.get(clave, [])))
    return cambios


def comparar(corrida, aprobadas):
    """El estado de cada vista: igual, distinta, nueva o falta."""
    vistas_corrida = leer(corrida)
    vistas_aprobadas = leer(aprobadas)
    resultados = []
    for nombre in sorted(set(vistas_corrida) | set(vistas_aprobadas)):
        if nombre not in vistas_aprobadas:
            estado, cambios = "nueva", []
        elif nombre not in vistas_corrida:
            estado, cambios = "falta", []
        else:
            cambios = comparar_vistas(vistas_aprobadas[nombre],
                                      vistas_corrida[nombre])
            estado = "distinta" if cambios else "igual"
        resultados.append({"vista": nombre, "estado": estado,
                           "cambios": cambios})
    return resultados


def formatear(resultados):
    """Una línea por estado y otra por cambio, para leer con lector de pantalla."""
    lineas = []
    for resultado in resultados:
        vista = resultado["vista"]
        lineas.append(f"{resultado['estado']} {vista}")
        for cambio in resultado["cambios"]:
            detalle = _DETALLES[cambio["tipo"]].format(**cambio)
            lineas.append(f"{vista} {cambio['control']} "
                          f"({cambio['clase']}) {detalle}")
    return lineas


def aprobar(corrida, aprobadas, vistas=None):
    """Copia las vistas de la corrida a lo aprobado y devuelve sus nombres."""
    encontradas = _nombres(corrida)
    if vistas:
        desconocidas = [nombre for nombre in vistas if nombre not in encontradas]
        if desconocidas:
            raise ValueError("No hay vista con este nombre: "
                             + ", ".join(desconocidas))
        elegidas = list(vistas)
    else:
        elegidas = encontradas
    aprobadas.mkdir(parents=True, exist_ok=True)
    for nombre in elegidas:
        shutil.copy2(corrida / (nombre + ".json"),
                     aprobadas / (nombre + ".json"))
    return elegidas


def main(argv=None, aprobadas=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("accion", choices=("comparar", "aprobar"),
                        help="comparar una corrida o aprobar sus vistas")
    parser.add_argument("carpeta", help="carpeta con los JSON de la galería")
    parser.add_argument("--maquina", choices=("casa", "oficina"), required=True,
                        help="máquina que aprobó las vistas")
    parser.add_argument("--vista", action="append", default=[],
                        metavar="NOMBRE", help="aprobar solo esta vista")
    argumentos = parser.parse_args(argv)
    raiz = Path(aprobadas) if aprobadas else APROBADAS
    destino = raiz / argumentos.maquina
    corrida = Path(argumentos.carpeta)
    if argumentos.accion == "aprobar":
        try:
            copiadas = aprobar(corrida, destino, argumentos.vista)
        except ValueError as exc:
            print(exc, file=sys.stderr)
            return 2
        for nombre in copiadas:
            print("aprobada " + nombre)
        return 0
    if not _nombres(destino):
        print(f"No hay aprobadas de {argumentos.maquina} para comparar.")
        return 3
    resultados = comparar(corrida, destino)
    lineas = formatear(resultados)
    if lineas:
        print("\n".join(lineas))
    else:
        print("Sin vistas.")
    return 1 if any(r["estado"] != "igual" for r in resultados) else 0


if __name__ == "__main__":
    sys.exit(main())
