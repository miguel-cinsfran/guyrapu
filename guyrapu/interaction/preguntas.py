# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Las preguntas del público de la sesión.

Puro y sin wx. Única razón para cambiar: cómo entra, se ordena y sale una
pregunta del público.
"""

from __future__ import annotations

from dataclasses import dataclass

from guyrapu.interaction import comandos, filtro_publico
from guyrapu.interaction.evento import persona

NOMBRES = ("pregunta", "q")
MAXIMO = 50
LARGO = 300

SUMADA = "sumada"
LLENA = "llena"
IGNORADA = "ignorada"


def leer(texto):
    """La invocación si el texto pide una pregunta, o None si no."""
    invocacion = comandos.leer(texto)
    if invocacion is None or invocacion.nombre not in NOMBRES:
        return None
    return invocacion


@dataclass(frozen=True)
class Pregunta:
    """Una pregunta del público con su lugar y su autor."""

    id: int
    plataforma: str
    autor_id: str
    autor: str
    texto: str
    instante: float
    identidad: tuple[str, str]


def _texto(argumentos, bloqueadas) -> str:
    """El texto tapado y recortado, o vacío si no hay pregunta que guardar."""
    if not argumentos or filtro_publico.es_casi_todo_simbolos(argumentos):
        return ""
    texto = filtro_publico.tapar(argumentos, bloqueadas)
    if len(texto) > LARGO:
        texto = texto[:LARGO - 1] + "…"
    return texto


class ColaPreguntas:
    """Las preguntas pendientes de una sesión, en el orden en que llegaron."""

    def __init__(self):
        self._pendientes: list[Pregunta] = []
        self._siguiente = 0
        self._llena_avisada = False
        self._suscriptores = []

    def agregar(self, evento, argumentos, bloqueadas, ahora) -> str:
        """Suma o reemplaza la pregunta y dice si entró o por qué no."""
        texto = _texto(argumentos, bloqueadas)
        if not texto:
            return IGNORADA
        identidad = persona(evento)
        for posicion, pendiente in enumerate(self._pendientes):
            if pendiente.identidad != identidad:
                continue
            self._pendientes[posicion] = Pregunta(
                id=pendiente.id, plataforma=pendiente.plataforma,
                autor_id=pendiente.autor_id, autor=pendiente.autor,
                texto=texto, instante=ahora, identidad=identidad)
            self._cambiada()
            return SUMADA
        if len(self._pendientes) >= MAXIMO:
            return LLENA
        self._siguiente += 1
        self._pendientes.append(Pregunta(
            id=self._siguiente, plataforma=evento.plataforma,
            autor_id=evento.autor_id,
            autor=filtro_publico.tapar(evento.autor or "", bloqueadas),
            texto=texto, instante=ahora, identidad=identidad))
        self._cambiada()
        return SUMADA

    def pendientes(self) -> list[Pregunta]:
        """Las preguntas pendientes, en el orden en que llegaron."""
        return list(self._pendientes)

    def siguiente(self):
        """La pregunta más vieja pendiente, o None si no hay ninguna."""
        return self._pendientes[0] if self._pendientes else None

    def responder(self, id) -> bool:
        """Saca de la cola la pregunta respondida."""
        return self._quitar(id)

    def descartar(self, id) -> bool:
        """Saca de la cola la pregunta descartada."""
        return self._quitar(id)

    def vaciar(self) -> None:
        """Descarta todas las preguntas pendientes."""
        if not self._pendientes:
            return
        self._pendientes.clear()
        self._cambiada()

    def suscribir(self, aviso) -> None:
        """Avisa a esa función cada vez que la cola cambia."""
        self._suscriptores.append(aviso)

    def avisar_llena(self) -> bool:
        """Si toca avisar que está llena, una vez hasta que vuelva a haber lugar."""
        if len(self._pendientes) < MAXIMO or self._llena_avisada:
            return False
        self._llena_avisada = True
        return True

    def _quitar(self, id) -> bool:
        for posicion, pendiente in enumerate(self._pendientes):
            if pendiente.id == id:
                del self._pendientes[posicion]
                self._cambiada()
                return True
        return False

    def _cambiada(self) -> None:
        if len(self._pendientes) < MAXIMO:
            self._llena_avisada = False
        for aviso in tuple(self._suscriptores):
            aviso()
