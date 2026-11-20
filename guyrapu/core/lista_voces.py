# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Las filas de la lista de motores y de la lista de voces, sin wx."""

from __future__ import annotations

import unicodedata
from typing import NamedTuple

from guyrapu.core import voces_disponibles
from guyrapu.core.idioma import ngettext


class FilaVoz(NamedTuple):
    """Una voz, con el paquete al que pertenece y su puesto en él."""

    texto: str
    paquete: object
    indice: int


def _normalizar(texto) -> str:
    descompuesto = unicodedata.normalize("NFD", str(texto or ""))
    return "".join(c for c in descompuesto
                   if not unicodedata.combining(c)).casefold()


def filas_motores(entradas) -> list[tuple[str, str]]:
    """Un motor por fila, con el total de voces y cuántas están instaladas."""
    filas = []
    for _nombre, motor in voces_disponibles.opciones_motor(entradas)[1:]:
        propios = [entrada for entrada in entradas
                   if voces_disponibles.motor_de(entrada) == motor]
        total = sum(len(voces_disponibles.voces(entrada))
                    for entrada in propios)
        if not total:
            continue
        instaladas = sum(len(voces_disponibles.voces(entrada))
                         for entrada in propios if entrada.instalado is not None)
        filas.append((
            "{}, {}, {}".format(
                voces_disponibles.nombre_motor(propios[0]),
                ngettext("{n} voz", "{n} voces", total).format(n=total),
                ngettext("{n} instalada", "{n} instaladas", instaladas).format(
                    n=instaladas)),
            motor))
    return filas


def filas_voces(entradas, motor, texto="") -> list[FilaVoz]:
    """Todas las voces del motor, filtradas por nombre sin tildes ni caso."""
    buscado = _normalizar(texto)
    filas = []
    for entrada in entradas:
        if voces_disponibles.motor_de(entrada) != motor:
            continue
        estado = voces_disponibles.estado(entrada)
        aviso = voces_disponibles.aviso_uso(entrada)
        for indice, voz in enumerate(voces_disponibles.voces(entrada)):
            nombre = str(voz.get("nombre") or "")
            if buscado and buscado not in _normalizar(nombre):
                continue
            genero = voces_disponibles.nombre_genero(voz.get("genero"))
            filas.append(FilaVoz(
                ", ".join(parte for parte in (nombre, genero, estado, aviso)
                          if parte),
                entrada, indice))
    return filas
