# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Cómo se vota y se cuenta una encuesta.

Puro y sin wx. Única razón para cambiar: cómo se registran los votos, cuándo
se cierra una encuesta y cómo se resume.
"""

from __future__ import annotations

from guyrapu.core.idioma import _, ngettext
from guyrapu.interaction import comandos
from guyrapu.interaction.evento import persona


MINIMO_OPCIONES = 2
MAXIMO_OPCIONES = 9


class Encuesta:
    """Una encuesta votable con `!` y el número de la opción."""

    def __init__(self, pregunta, opciones, segundos=None):
        self.pregunta = pregunta
        self.opciones = tuple(opciones)
        self.segundos = segundos
        self._inicio: float | None = None
        self._cerrada = False
        self._votantes: dict[tuple[str, str], int] = {}

    def abrir(self, ahora) -> None:
        """Marca el comienzo de la encuesta."""
        self._inicio = ahora
        self._cerrada = False

    def votar(self, evento, ahora) -> int | None:
        """Anota el voto y devuelve la opción contada, o None."""
        if not self.abierta(ahora):
            return None
        invocacion = comandos.leer(evento.texto)
        if invocacion is None or not invocacion.nombre.isdecimal():
            return None
        numero = int(invocacion.nombre)
        if not 1 <= numero <= len(self.opciones):
            return None
        quien = persona(evento)
        if quien in self._votantes:
            return None
        self._votantes[quien] = numero - 1
        return numero

    def votos(self) -> list[int]:
        """Los votos de cada opción, en el orden de las opciones."""
        conteo = [0] * len(self.opciones)
        for indice in self._votantes.values():
            conteo[indice] += 1
        return conteo

    def total(self) -> int:
        """Cuántas personas votaron."""
        return len(self._votantes)

    def segundos_restantes(self, ahora) -> int | None:
        """Los segundos que le quedan, o None si no tiene tiempo."""
        if self.segundos is None or self._inicio is None:
            return None
        return int(self._inicio + self.segundos - ahora)

    def cerrar(self) -> None:
        """Cierra la encuesta a mano."""
        self._cerrada = True

    def abierta(self, ahora) -> bool:
        """Si todavía acepta votos."""
        if self._cerrada or self._inicio is None:
            return False
        if self.segundos is None:
            return True
        return ahora - self._inicio < self.segundos

    def ganadoras(self) -> list[int]:
        """Los números de las opciones con más votos, o vacío sin votos."""
        conteo = self.votos()
        if not any(conteo):
            return []
        maximo = max(conteo)
        return [numero for numero, votos in enumerate(conteo, 1)
                if votos == maximo]

    def resumen(self, ahora) -> str:
        """La encuesta en una frase, para F2 y para el cierre."""
        partes = []
        # Traductores: resumen de una encuesta; {pregunta} es su pregunta.
        partes.append(_("Encuesta: {pregunta}.").format(pregunta=self.pregunta))
        for numero, (opcion, votos) in enumerate(
                zip(self.opciones, self.votos()), 1):
            partes.append(
                # Traductores: una opción de la encuesta; {numero} es su número, {opcion} su texto y {votos} cuántos votos tiene.
                _("{numero}, {opcion}: {votos}.").format(
                    numero=numero, opcion=opcion,
                    votos=ngettext("{n} voto", "{n} votos",
                                   votos).format(n=votos)))
        total = self.total()
        partes.append(
            # Traductores: total de votos de una encuesta.
            _("Total: {votos}.").format(
                votos=ngettext("{n} voto", "{n} votos",
                               total).format(n=total)))
        if not self.abierta(ahora):
            # Traductores: una encuesta que ya no acepta votos.
            partes.append(_("Cerrada."))
        elif self.segundos is not None:
            restante = self.segundos_restantes(ahora)
            partes.append(
                # Traductores: tiempo que le queda a una encuesta; {n} son los segundos.
                ngettext("Queda {n} segundo.", "Quedan {n} segundos.",
                         restante).format(n=restante))
        return " ".join(partes)


def validar_encuesta(pregunta, opciones) -> str:
    """Un texto de error, o "" si la encuesta se puede abrir."""
    if not (pregunta or "").strip():
        # Traductores: validación de una encuesta del chat (error).
        return _("La encuesta necesita una pregunta.")
    if not MINIMO_OPCIONES <= len(opciones) <= MAXIMO_OPCIONES:
        # Traductores: validación de una encuesta del chat (error).
        return _("La encuesta necesita entre {minimo} y {maximo} "
                 "opciones.").format(minimo=MINIMO_OPCIONES,
                                     maximo=MAXIMO_OPCIONES)
    if any(not (opcion or "").strip() for opcion in opciones):
        # Traductores: validación de una encuesta del chat (error).
        return _("Ninguna opción de la encuesta puede estar vacía.")
    return ""
