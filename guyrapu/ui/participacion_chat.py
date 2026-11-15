# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Cuántos mensajes escribió cada persona en el directo conectado.

Puro y sin wx. Única razón para cambiar: cómo se cuentan y se ordenan los
mensajes por persona y cómo se escribe cada línea.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass

from guyrapu.core import plataformas
from guyrapu.core.config import TIPO_SUPERCHAT, TIPO_TEXTO
from guyrapu.core.idioma import ngettext

# Traductores: una línea de participación; {nombre} es la persona y {n} la cantidad de mensajes.
TEXTO_UNO = "{nombre}: {n} mensaje"
TEXTO_VARIOS = "{nombre}: {n} mensajes"


@dataclass
class _Cuenta:
    nombre: str
    plataforma: str
    mensajes: int


def _clave_de_orden(nombre: str) -> str:
    """Nombre sin tildes y en minúsculas, para desempatar en el orden."""
    sin_tildes = "".join(
        letra for letra in unicodedata.normalize("NFKD", nombre)
        if not unicodedata.combining(letra))
    return sin_tildes.casefold()


class Participacion:
    """Conteo de mensajes por persona, con el último nombre visto."""

    def __init__(self):
        self._cuentas: dict[tuple[str, str], _Cuenta] = {}

    def sumar(self, registro) -> None:
        """Suma el registro si es un mensaje escrito por una persona."""
        if registro.tipo not in (TIPO_TEXTO, TIPO_SUPERCHAT):
            return
        clave = (registro.plataforma,
                 registro.identificador or registro.autor)
        cuenta = self._cuentas.get(clave)
        if cuenta is None:
            self._cuentas[clave] = _Cuenta(
                registro.autor, registro.plataforma, 1)
        else:
            cuenta.nombre = registro.autor
            cuenta.mensajes += 1

    def limpiar(self) -> None:
        self._cuentas.clear()

    def vacia(self) -> bool:
        return not self._cuentas

    def lineas(self) -> list[str]:
        """Una línea por persona, de más a menos mensajes."""
        varias = len({cuenta.plataforma
                      for cuenta in self._cuentas.values()}) > 1
        ordenadas = sorted(
            self._cuentas.values(),
            key=lambda cuenta: (-cuenta.mensajes,
                                _clave_de_orden(cuenta.nombre)))
        return [self._linea(cuenta, varias) for cuenta in ordenadas]

    @staticmethod
    def _linea(cuenta: _Cuenta, varias: bool) -> str:
        nombre = cuenta.nombre
        if varias:
            nombre_plataforma = plataformas.nombre(cuenta.plataforma)
            if nombre_plataforma:
                nombre = f"{nombre} ({nombre_plataforma})"
        return ngettext(TEXTO_UNO, TEXTO_VARIOS, cuenta.mensajes).format(
            nombre=nombre, n=cuenta.mensajes)
