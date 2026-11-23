# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Cómo se reconoce un comando y si se puede usar ahora.

Puro y sin wx. Única razón para cambiar: qué comandos existen, cómo se
encuentran, quién puede usarlos y cuánto esperan entre usos.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, replace

from guyrapu.core.idioma import _, idioma_actual
from guyrapu.core.sonidos_eventos import ROL_MODERADOR, ROL_PROPIETARIO
from guyrapu.interaction.evento import EventoDirecto, persona
from guyrapu.interaction.texto import normalizar

DESTINOS = ("video", "chat", "ambos")
PERMISOS = ("todos", "moderadores", "lista", "solo_atajo")
UBICACIONES = ("principio", "cualquiera")
VARIABLES = ("usuario", "contador", "texto")
MAXIMO_CHAT = 200

_VARIABLE_RE = re.compile(r"\{([^{}]*)\}")


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
    medio: str = ""
    destino: str = "video"
    permiso: str = "todos"
    nombres: tuple[str, ...] = ()
    espera_general: float = 5
    espera_persona: float = 30
    activo: bool = True
    estilo: str = ""
    segundos: int = 8
    lista: bool = False
    en_lista: bool = True
    ubicacion: str = "principio"
    atajo: int = 0

    def __post_init__(self):
        object.__setattr__(self, "nombre", _sin_signo(self.nombre))
        object.__setattr__(self, "alias",
                           tuple(_sin_signo(alias) for alias in self.alias))
        object.__setattr__(self, "segundos",
                           max(3, min(60, int(self.segundos))))
        object.__setattr__(self, "ubicacion",
                           self.ubicacion if self.ubicacion in UBICACIONES
                           else "principio")
        object.__setattr__(self, "atajo", max(0, min(9, int(self.atajo))))


def comando_de_lista(codigo: str | None = None) -> Comando:
    """El comando de lista de fábrica para el idioma indicado."""
    codigo = idioma_actual() if codigo is None else codigo
    alias = ("comandos",) if codigo.lower().startswith(("es", "pt")) else ()
    # Traductores: respuesta del comando de lista del chat. {lista} son los nombres de los comandos activos.
    respuesta = _("Comandos: {lista}.")
    return Comando(
        "commands", alias, respuesta,
        destino="video", estilo="", segundos=8,
        espera_general=5, espera_persona=30, lista=True)


def asegurar_lista(disponibles, codigo: str | None = None) -> list[Comando]:
    """Una colección con un solo comando de lista, el primero si hay varios."""
    elementos = list(disponibles)
    primera = next((indice for indice, comando in enumerate(elementos)
                    if comando.lista), None)
    if primera is None:
        return [comando_de_lista(codigo), *elementos]
    return [replace(comando, lista=False)
            if comando.lista and indice != primera else comando
            for indice, comando in enumerate(elementos)]


def separar_alias(texto: str) -> tuple[str, ...]:
    """Los alias escritos con espacios o comas, sin las partes vacías."""
    return tuple(parte for parte in re.split(r"[,\s]+", texto or "")
                 if parte)


def separar_nombres(texto: str) -> tuple[str, ...]:
    """Los nombres de una lista, separados por comas, punto y coma o líneas."""
    return tuple(parte.strip() for parte in re.split(r"[,;\n]+", texto or "")
                 if parte.strip())


def buscar(comandos, invocacion: Invocacion | None, *, activos=True) -> Comando | None:
    """El primer comando que responde a ese nombre o alias."""
    if invocacion is None:
        return None
    for comando in comandos:
        if (activos and not comando.activo) or comando.ubicacion != "principio":
            continue
        if normalizar(comando.nombre) == invocacion.nombre:
            return comando
        if any(normalizar(alias) == invocacion.nombre
               for alias in comando.alias):
            return comando
    return None


def _palabra_en(mensaje: str, palabra: str) -> bool:
    if not palabra:
        return False
    if not (palabra[0].isalnum() and palabra[-1].isalnum()):
        return palabra in mensaje
    inicio = 0
    while (pos := mensaje.find(palabra, inicio)) >= 0:
        antes = mensaje[pos - 1] if pos else ""
        fin = pos + len(palabra)
        despues = mensaje[fin:fin + 1]
        if not antes.isalnum() and not despues.isalnum():
            return True
        inicio = pos + 1
    return False


def buscar_en_mensaje(comandos, mensaje: str, *, activos=True) -> Comando | None:
    """El primer comando de cualquier parte cuyo nombre o alias aparece."""
    if not mensaje or leer(mensaje) is not None:
        return None
    texto = normalizar(mensaje)
    for comando in comandos:
        if (activos and not comando.activo) or comando.ubicacion != "cualquiera":
            continue
        if any(_palabra_en(texto, normalizar(nombre))
               for nombre in _nombres_de(comando)):
            return comando
    return None


def _es_del_equipo(evento: EventoDirecto) -> bool:
    return bool(evento.roles & {ROL_PROPIETARIO, ROL_MODERADOR})


def puede_usarlo(comando: Comando, evento: EventoDirecto) -> bool:
    """Si esa persona puede usar el comando según su permiso."""
    if comando.permiso == "solo_atajo":
        return False
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

    def faltan(self, comando: Comando, evento: EventoDirecto, ahora) -> int:
        """Segundos que faltan para usar el comando, o 0 si ya se puede."""
        if self.libre(comando, evento, ahora):
            return 0
        restantes = []
        ultimo = self._general.get(comando.nombre)
        if ultimo is not None:
            restantes.append(comando.espera_general - (ahora - ultimo))
        ultimo = self._persona.get((comando.nombre, persona(evento)))
        if ultimo is not None:
            restantes.append(comando.espera_persona - (ahora - ultimo))
        return math.ceil(max(restantes))


def _nombres_de(comando: Comando):
    return (comando.nombre, *comando.alias)


def _solo_cifras(texto: str) -> bool:
    return normalizar(texto).isdecimal()


def _error_de_nombre(comando: Comando) -> str:
    if not normalizar(comando.nombre):
        # Traductores: validación de comandos del chat (error).
        return _("El comando necesita un nombre.")
    if any(_solo_cifras(nombre) for nombre in _nombres_de(comando)):
        # Traductores: validación de comandos del chat (error). Las cifras son las de votar encuestas.
        return _("Un comando no puede llamarse solo con números.")
    if (comando.ubicacion != "cualquiera"
            and any(len(nombre.split()) > 1 for nombre in _nombres_de(comando))):
        # Traductores: validación de comandos del chat (error).
        return _("El nombre de un comando no puede tener espacios.")
    return ""


def _error_de_atajo(comando: Comando, otros) -> str:
    if not comando.atajo:
        return ""
    for otro in otros:
        if otro.activo and otro.atajo == comando.atajo:
            # Traductores: validación de comandos del chat (error). {n} es el número del atajo y {nombre} el comando que ya lo usa.
            return _("Ctrl+Alt+Mayús+{n} ya lo usa el comando {nombre}.").format(
                n=comando.atajo, nombre=otro.nombre)
    return ""


def _error_de_permiso(comando: Comando) -> str:
    if comando.permiso == "solo_atajo" and not comando.atajo:
        # Traductores: validación de comandos del chat (error).
        return _("Elige un atajo para un comando que solo usa el atajo.")
    return ""


def _error_de_repetido(comando: Comando, otros) -> str:
    propios = {normalizar(nombre) for nombre in _nombres_de(comando)}
    for otro in otros:
        repetidos = propios & {
            normalizar(nombre) for nombre in _nombres_de(otro)}
        if repetidos:
            # Traductores: validación de comandos del chat (error). {nombre} es el comando que ya existe.
            return _("El comando {nombre} ya existe.").format(
                nombre=sorted(repetidos)[0])
    return ""


def _error_de_respuesta(comando: Comando) -> str:
    if not (comando.respuesta or "").strip() and not (comando.medio or "").strip():
        # Traductores: validación de comandos del chat (error).
        return _("El comando necesita una respuesta o un medio.")
    return ""


def _error_de_variables(comando: Comando) -> str:
    respuesta = comando.respuesta or ""
    permitidas = VARIABLES + (("lista",) if comando.lista else ())
    desconocidas = [variable for variable in _VARIABLE_RE.findall(respuesta)
                    if variable not in permitidas]
    if desconocidas:
        # Traductores: validación de comandos del chat (error). {variable} es la variable desconocida y las demás son las que se pueden usar.
        return _("La variable {variable} no existe. Puedes usar {usuario}, "
                 "{contador} y {texto}.").format(
                     variable="{" + desconocidas[0] + "}",
                     usuario="{" + VARIABLES[0] + "}",
                     contador="{" + VARIABLES[1] + "}",
                     texto="{" + VARIABLES[2] + "}")
    return ""


def _error_de_longitud(comando: Comando) -> str:
    respuesta = comando.respuesta or ""
    if comando.destino in ("chat", "ambos") and len(respuesta) > MAXIMO_CHAT:
        # Traductores: validación de comandos del chat (error). {actual} es el largo y {maximo} el tope del chat.
        return _("La respuesta tiene {actual} caracteres y el máximo para el "
                 "chat es {maximo}.").format(
                     actual=len(respuesta), maximo=MAXIMO_CHAT)
    return ""


def _error_de_lista(comando: Comando) -> str:
    if comando.permiso == "lista" and not any(
            str(nombre).strip() for nombre in comando.nombres):
        # Traductores: validación de comandos del chat (error).
        return _("La lista de nombres no puede estar vacía.")
    return ""


def validar(comando: Comando, otros) -> str:
    """Un texto de error, o "" si el comando se puede guardar."""
    return (_error_de_nombre(comando)
            or _error_de_repetido(comando, otros)
            or _error_de_atajo(comando, otros)
            or _error_de_permiso(comando)
            or _error_de_respuesta(comando)
            or _error_de_variables(comando)
            or _error_de_longitud(comando)
            or _error_de_lista(comando))
