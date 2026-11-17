# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Cómo se reconoce un comando y si se puede usar ahora.

Puro y sin wx. Única razón para cambiar: qué comandos existen, cómo se
encuentran, quién puede usarlos y cuánto esperan entre usos.
"""

from __future__ import annotations

from dataclasses import dataclass

from guyrapu.core.idioma import _
from guyrapu.core.sonidos_eventos import ROL_MODERADOR, ROL_PROPIETARIO
from guyrapu.interaction.evento import EventoDirecto, persona
from guyrapu.interaction.texto import normalizar


@dataclass(frozen=True, slots=True)
class Invocacion:
    """El comando que nombra un texto y lo que le sigue."""

    nombre: str
    argumentos: str


def leer(texto: str) -> Invocacion | None:
    """El comando invocado en un texto, o None si no lo es."""
    limpio = (texto or "").strip()
    if not limpio.startswith("!"):
        return None
    resto = limpio[1:]
    if not resto or resto[0].isspace():
        return None
    partes = resto.split(None, 1)
    return Invocacion(normalizar(partes[0]),
                      partes[1].strip() if len(partes) > 1 else "")


def _sin_signo(texto: str) -> str:
    limpio = (texto or "").strip()
    if limpio.startswith("!"):
        limpio = limpio[1:].strip()
    return limpio


@dataclass(frozen=True, slots=True)
class Comando:
    """Un comando del chat con su respuesta, su permiso y sus esperas."""

    nombre: str
    alias: tuple[str, ...]
    respuesta: str
    destino: str = "video"
    permiso: str = "todos"
    nombres: tuple[str, ...] = ()
    espera_general: float = 5
    espera_persona: float = 30
    activo: bool = True

    def __post_init__(self):
        object.__setattr__(self, "nombre", _sin_signo(self.nombre))
        object.__setattr__(self, "alias",
                           tuple(_sin_signo(alias) for alias in self.alias))


def buscar(comandos, invocacion: Invocacion | None) -> Comando | None:
    """El primer comando activo que responde a ese nombre o alias."""
    if invocacion is None:
        return None
    for comando in comandos:
        if not comando.activo:
            continue
        if normalizar(comando.nombre) == invocacion.nombre:
            return comando
        if any(normalizar(alias) == invocacion.nombre
               for alias in comando.alias):
            return comando
    return None


def _es_del_equipo(evento: EventoDirecto) -> bool:
    return bool(evento.roles & {ROL_PROPIETARIO, ROL_MODERADOR})


def puede_usarlo(comando: Comando, evento: EventoDirecto) -> bool:
    """Si esa persona puede usar el comando según su permiso."""
    if _es_del_equipo(evento):
        return True
    if comando.permiso == "todos":
        return True
    if comando.permiso == "moderadores":
        return False
    if comando.permiso == "lista":
        nombres = {normalizar(nombre) for nombre in comando.nombres}
        return normalizar(evento.autor) in nombres
    return False


class Esperas:
    """Últimos usos de cada comando, general y por persona."""

    def __init__(self):
        self._general: dict[str, float] = {}
        self._persona: dict[tuple[str, tuple[str, str]], float] = {}

    def libre(self, comando: Comando, evento: EventoDirecto, ahora) -> bool:
        """Si el comando se puede usar ahora sin esperar."""
        if _es_del_equipo(evento):
            return True
        ultimo = self._general.get(comando.nombre)
        if ultimo is not None and ahora - ultimo < comando.espera_general:
            return False
        ultimo = self._persona.get((comando.nombre, persona(evento)))
        if ultimo is not None and ahora - ultimo < comando.espera_persona:
            return False
        return True

    def anotar(self, comando: Comando, evento: EventoDirecto, ahora) -> None:
        """Guarda el uso, salvo el del dueño y los moderadores."""
        if _es_del_equipo(evento):
            return
        self._general[comando.nombre] = ahora
        self._persona[(comando.nombre, persona(evento))] = ahora


def _nombres_de(comando: Comando):
    return (comando.nombre, *comando.alias)


def _solo_cifras(texto: str) -> bool:
    return normalizar(texto).isdecimal()


def validar(comando: Comando, otros) -> str:
    """Un texto de error, o "" si el comando se puede guardar."""
    if not normalizar(comando.nombre):
        # Traductores: validación de comandos del chat (error).
        return _("El comando necesita un nombre.")
    if any(_solo_cifras(nombre) for nombre in _nombres_de(comando)):
        # Traductores: validación de comandos del chat (error). Las cifras son las de votar encuestas.
        return _("Un comando no puede llamarse solo con números.")
    if any(len(nombre.split()) > 1 for nombre in _nombres_de(comando)):
        # Traductores: validación de comandos del chat (error).
        return _("El nombre de un comando no puede tener espacios.")
    propios = {normalizar(nombre) for nombre in _nombres_de(comando)}
    for otro in otros:
        repetidos = propios & {
            normalizar(nombre) for nombre in _nombres_de(otro)}
        if repetidos:
            # Traductores: validación de comandos del chat (error). {nombre} es el comando que ya existe.
            return _("El comando {nombre} ya existe.").format(
                nombre=sorted(repetidos)[0])
    if not (comando.respuesta or "").strip():
        # Traductores: validación de comandos del chat (error).
        return _("El comando necesita una respuesta.")
    return ""
