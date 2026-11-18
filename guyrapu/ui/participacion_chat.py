# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Cuántos mensajes y regalos sumó cada persona en el directo conectado.

Puro y sin wx. Única razón para cambiar: cómo se cuentan y se ordenan los
mensajes y los regalos por persona y cómo se escribe cada línea.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

from guyrapu.capture.montos import sumar_monto
from guyrapu.core import plataformas
from guyrapu.core.config import TIPO_STICKER, TIPO_SUPERCHAT, TIPO_TEXTO
from guyrapu.core.idioma import N_, ngettext

# Traductores: una línea de participación; {nombre} es la persona y {n} la cantidad de mensajes.
TEXTO_UNO = "{nombre}: {n} mensaje"
TEXTO_VARIOS = "{nombre}: {n} mensajes"
# Traductores: regalo de TikTok; {n} es la cantidad de diamantes.
TEXTO_UN_DIAMANTE = "{n} diamante"
TEXTO_DIAMANTES = "{n} diamantes"

ORDEN_MENSAJES = "mensajes"
ORDEN_REGALOS = "regalos"
# Traductores: criterios del cuadro «Ordenar por» de Participación.
ORDENES = ((ORDEN_MENSAJES, N_("Mensajes")),
           (ORDEN_REGALOS, N_("Regalos")))

_DIAMANTES_RE = re.compile(r"^\s*(\d+)\s+diamantes?\s*$", re.IGNORECASE)


@dataclass
class _Cuenta:
    nombre: str
    plataforma: str
    mensajes: int = 0
    diamantes: int = 0
    importes: dict[str, float] = field(default_factory=dict)

    def anotar(self, registro) -> None:
        self.nombre = registro.autor
        self.mensajes += 1
        _sumar_regalo(self, registro.monto)


def _es_mensaje(registro) -> bool:
    """Si el registro es texto, Super Chat o un sticker con importe."""
    return (registro.tipo in (TIPO_TEXTO, TIPO_SUPERCHAT)
            or (registro.tipo == TIPO_STICKER and bool(registro.monto)))


def _diamantes(monto: str):
    encontrado = _DIAMANTES_RE.match(monto)
    if encontrado is None:
        return None
    return int(encontrado.group(1))


def _sumar_regalo(cuenta: _Cuenta, monto: str) -> None:
    if not monto:
        return
    diamantes = _diamantes(monto)
    if diamantes is None:
        sumar_monto(cuenta.importes, monto)
    else:
        cuenta.diamantes += diamantes


def _texto_regalos(cuenta: _Cuenta) -> str:
    partes = []
    if cuenta.diamantes:
        partes.append(ngettext(TEXTO_UN_DIAMANTE, TEXTO_DIAMANTES,
                               cuenta.diamantes).format(n=cuenta.diamantes))
    for divisa, valor in cuenta.importes.items():
        partes.append(f"{valor:.2f}".replace(".", ",") + f" {divisa}")
    return ", ".join(partes)


def _clave_de_orden(nombre: str) -> str:
    """Nombre sin tildes y en minúsculas, para desempatar en el orden."""
    sin_tildes = "".join(
        letra for letra in unicodedata.normalize("NFKD", nombre)
        if not unicodedata.combining(letra))
    return sin_tildes.casefold()


def _clave_de_regalos(cuenta: _Cuenta):
    """Diamantes, después Super Chats y al final quien no regaló, por mensajes."""
    nombre = _clave_de_orden(cuenta.nombre)
    if cuenta.diamantes:
        return (0, -cuenta.diamantes, 0.0, 0, nombre)
    if cuenta.importes:
        return (1, 0, -max(cuenta.importes.values()), 0, nombre)
    return (2, 0, 0.0, -cuenta.mensajes, nombre)


class Participacion:
    """Conteo de mensajes y regalos por persona, con el último nombre visto."""

    def __init__(self):
        self._cuentas: dict[tuple[str, str], _Cuenta] = {}

    def sumar(self, registro) -> None:
        """Suma el registro si es un mensaje escrito por una persona."""
        if not _es_mensaje(registro):
            return
        clave = (registro.plataforma,
                 registro.identificador or registro.autor)
        cuenta = self._cuentas.get(clave)
        if cuenta is None:
            cuenta = self._cuentas[clave] = _Cuenta(
                registro.autor, registro.plataforma)
        cuenta.anotar(registro)

    def limpiar(self) -> None:
        self._cuentas.clear()

    def vacia(self) -> bool:
        return not self._cuentas

    def lineas(self, orden=ORDEN_MENSAJES) -> list[str]:
        """Una línea por persona, de más a menos mensajes o de más a menos regalos."""
        varias = len({cuenta.plataforma
                      for cuenta in self._cuentas.values()}) > 1
        clave = (_clave_de_regalos if orden == ORDEN_REGALOS
                 else lambda cuenta: (-cuenta.mensajes,
                                      _clave_de_orden(cuenta.nombre)))
        ordenadas = sorted(self._cuentas.values(), key=clave)
        return [self._linea(cuenta, varias) for cuenta in ordenadas]

    @staticmethod
    def _linea(cuenta: _Cuenta, varias: bool) -> str:
        nombre = cuenta.nombre
        if varias:
            nombre_plataforma = plataformas.nombre(cuenta.plataforma)
            if nombre_plataforma:
                nombre = f"{nombre} ({nombre_plataforma})"
        texto = ngettext(TEXTO_UNO, TEXTO_VARIOS, cuenta.mensajes).format(
            nombre=nombre, n=cuenta.mensajes)
        regalos = _texto_regalos(cuenta)
        return f"{texto}, {regalos}" if regalos else texto
