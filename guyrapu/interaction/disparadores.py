# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Cuándo se cumple un disparador de la interacción con el público.

Puro y sin wx. Única razón para cambiar: qué datos tiene un disparador y
cuándo un mensaje del directo lo cumple.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from guyrapu.core import avisos_tiktok
from guyrapu.core.idioma import _
from guyrapu.interaction import comandos
from guyrapu.interaction.texto import normalizar

CUANDOS = ("comando", "evento")
EVENTOS_DEL_DIRECTO = tuple(tipo for tipo, _modo in avisos_tiktok.EVENTOS
                            if tipo != "comando")

_NUMERO_RE = re.compile(r"\d+(?:[.,]\d+)*")
_DECIMAL_RE = re.compile(r"[.,]\d{2}$")


def _sin_signo(texto: str) -> str:
    limpio = (texto or "").strip()
    if limpio.startswith("!"):
        limpio = limpio[1:].strip()
    return limpio


@dataclass(frozen=True, slots=True)
class Disparador:
    """Un disparador con su cuándo, su qué y sus reglas."""

    nombre: str
    cuando: str = "comando"
    comandos: tuple[str, ...] = ()
    evento: str = ""
    minimo: float | None = None
    medio: str = ""
    tarjeta: str = ""
    estilo: str = "clasico"
    segundos: int = 8
    permiso: str = "todos"
    nombres: tuple[str, ...] = ()
    espera_general: float = 5
    espera_persona: float = 30
    activo: bool = True

    def __post_init__(self):
        object.__setattr__(self, "comandos",
                           tuple(_sin_signo(nombre)
                                 for nombre in self.comandos))
        object.__setattr__(self, "segundos",
                           max(3, min(60, int(self.segundos))))


def cantidad_de(monto) -> float:
    """La cantidad que trae el monto: el primer número que aparece."""
    encontrado = _NUMERO_RE.search(str(monto or ""))
    if encontrado is None:
        return 0
    numero = encontrado.group(0)
    if _DECIMAL_RE.search(numero):
        entero = re.sub(r"[.,]", "", numero[:-3]) or "0"
        return float(entero + "." + numero[-2:])
    return float(re.sub(r"[.,]", "", numero))


def _cumple_comando(disparador: Disparador, evento) -> bool:
    invocacion = comandos.leer(evento.texto)
    if invocacion is None:
        return False
    return any(normalizar(nombre) == invocacion.nombre
               for nombre in disparador.comandos)


def _cumple_evento(disparador: Disparador, evento) -> bool:
    if avisos_tiktok.evento_de(evento.tipo) != disparador.evento:
        return False
    if disparador.minimo is None:
        return True
    return cantidad_de(evento.monto) >= disparador.minimo


def _cumple(disparador: Disparador, evento) -> bool:
    if disparador.cuando == "comando":
        return _cumple_comando(disparador, evento)
    if disparador.cuando == "evento":
        return _cumple_evento(disparador, evento)
    return False


def cumplidos(disparadores, evento, esperas, ahora) -> list[Disparador]:
    """Los disparadores que ese mensaje cumple, en el orden de la lista.

    Anota el uso de cada uno que devuelve, para que sus esperas cuenten.
    """
    logrados = []
    for disparador in disparadores:
        if not disparador.activo:
            continue
        if not _cumple(disparador, evento):
            continue
        if not comandos.puede_usarlo(disparador, evento):
            continue
        if not esperas.libre(disparador, evento, ahora):
            continue
        esperas.anotar(disparador, evento, ahora)
        logrados.append(disparador)
    return logrados


def _error_de_nombre(disparador: Disparador, otros) -> str:
    if not normalizar(disparador.nombre):
        # Traductores: validación de disparadores del directo (error).
        return _("El disparador necesita un nombre.")
    for otro in otros:
        if normalizar(otro.nombre) == normalizar(disparador.nombre):
            # Traductores: validación de disparadores del directo (error). {nombre} es el disparador que ya existe.
            return _("El disparador {nombre} ya existe.").format(
                nombre=disparador.nombre)
    return ""


def _error_de_cuando(disparador: Disparador) -> str:
    if disparador.cuando not in CUANDOS:
        # Traductores: validación de disparadores del directo (error).
        return _("Ese tipo de disparador todavía no existe.")
    return ""


def _error_de_comando(disparador: Disparador, otros) -> str:
    if disparador.cuando != "comando":
        return ""
    propios = {normalizar(nombre) for nombre in disparador.comandos}
    propios.discard("")
    if not propios:
        # Traductores: validación de disparadores del directo (error).
        return _("El disparador de comando necesita al menos un nombre.")
    for otro in otros:
        repetidos = propios & {normalizar(nombre)
                               for nombre in otro.comandos}
        if repetidos:
            # Traductores: validación de disparadores del directo (error). {nombre} es el comando del chat que ya usa otro disparador.
            return _("El comando {nombre} ya lo usa otro disparador.").format(
                nombre=sorted(repetidos)[0])
    return ""


def _error_de_evento(disparador: Disparador) -> str:
    if disparador.cuando != "evento":
        return ""
    if disparador.evento not in EVENTOS_DEL_DIRECTO:
        # Traductores: validación de disparadores del directo (error). {evento} es el nombre del evento desconocido.
        return _("El evento {evento} no existe.").format(
            evento=disparador.evento)
    if disparador.minimo is not None and disparador.minimo < 0:
        # Traductores: validación de disparadores del directo (error).
        return _("El mínimo no puede ser negativo.")
    return ""


def _error_de_que(disparador: Disparador) -> str:
    if not (disparador.medio or "").strip() \
            and not (disparador.tarjeta or "").strip():
        # Traductores: validación de disparadores del directo (error).
        return _("El disparador necesita un medio o una tarjeta de texto.")
    return ""


def validar(disparador: Disparador, otros) -> str:
    """Un texto de error, o "" si el disparador se puede guardar."""
    return (_error_de_nombre(disparador, otros)
            or _error_de_cuando(disparador)
            or _error_de_comando(disparador, otros)
            or _error_de_evento(disparador)
            or _error_de_que(disparador))
