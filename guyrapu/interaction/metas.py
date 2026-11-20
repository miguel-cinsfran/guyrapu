# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Qué es una meta del directo y cómo avanza con los eventos.

Puro y sin wx. Única razón para cambiar: qué datos tiene una meta y cómo
la hace avanzar cada evento del directo.
"""

from __future__ import annotations

from dataclasses import dataclass

from guyrapu.core import avisos_tiktok, plataformas
from guyrapu.core.idioma import N_, _
from guyrapu.interaction.disparadores import cantidad_de
from guyrapu.interaction.evento import persona
from guyrapu.interaction.texto import normalizar

QUE_CUENTA = ("me_gusta", "seguidores", "miembros", "regalos", "super_chat")

NOMBRES_QUE_CUENTA = {
    "me_gusta": N_("Me gusta"),
    "seguidores": N_("Seguidores nuevos"),
    "miembros": N_("Membresías"),
    "regalos": N_("Regalos de TikTok en diamantes"),
    "super_chat": N_("Super Chats de YouTube"),
}


@dataclass(frozen=True, slots=True)
class Meta:
    """Una meta del directo y los textos que la acompañan."""

    nombre: str
    que_cuenta: str
    objetivo: int
    estilo: str = ""
    festejo: str = ""
    activa: bool = True
    en_video: bool = False


class Progreso:
    """El avance de una meta durante la sesión del directo."""

    def __init__(self, meta: Meta):
        self.meta = meta
        self._valor: float = 0
        self._personas: set[tuple[str, str]] = set()
        self._anunciada = False

    @property
    def valor(self) -> float:
        return self._valor

    @property
    def cumplida(self) -> bool:
        return self._valor >= self.meta.objetivo

    def recien_cumplida(self) -> bool:
        """Verdadero una sola vez, al consultar después de cumplirse."""
        if not self.cumplida or self._anunciada:
            return False
        self._anunciada = True
        return True

    def sumar(self, evento) -> bool:
        """Suma el evento si cuenta para la meta; dice si hizo avanzar."""
        cantidad = self._cantidad(evento)
        if cantidad <= 0:
            return False
        self._valor += cantidad
        return True

    def _cantidad(self, evento) -> float:
        clase = avisos_tiktok.evento_de(evento.tipo)
        if self.meta.que_cuenta == "seguidores":
            if clase != "seguir":
                return 0
            identidad = persona(evento)
            if identidad in self._personas:
                return 0
            self._personas.add(identidad)
            return 1
        if self.meta.que_cuenta == "me_gusta":
            return cantidad_de(evento.monto) if clase == "me_gusta" else 0
        if self.meta.que_cuenta == "miembros":
            return 1 if clase == "miembro" else 0
        if self.meta.que_cuenta == "regalos":
            return self._monto(evento, clase, plataformas.TIKTOK)
        if self.meta.que_cuenta == "super_chat":
            return self._monto(evento, clase, plataformas.YOUTUBE)
        return 0

    @staticmethod
    def _monto(evento, clase, plataforma) -> float:
        if clase != "superchat" or evento.plataforma != plataforma:
            return 0
        return cantidad_de(evento.monto)


def texto(meta: Meta, valor) -> str:
    """La línea de la tarjeta que muestra el avance de una meta."""
    if valor >= meta.objetivo:
        # Traductores: línea de la tarjeta de una meta cumplida.
        return _("{nombre}: meta cumplida").format(nombre=meta.nombre)
    if meta.que_cuenta == "super_chat":
        mostrado = f"{valor:.2f}"
    else:
        mostrado = f"{valor:.0f}"
    # Traductores: línea de la tarjeta de una meta en curso. {nombre} es la
    # meta, {valor} lo logrado y {objetivo} lo que hay que lograr.
    return _("{nombre}: {valor} de {objetivo}").format(
        nombre=meta.nombre, valor=mostrado, objetivo=meta.objetivo)


def texto_en_video(progresos) -> str:
    """Las líneas de la pieza fija en el vídeo, una por meta."""
    return "\n".join(texto(progreso.meta, progreso.valor)
                     for progreso in progresos)


def validar(meta: Meta, otras) -> str:
    """Un texto de error, o "" si la meta se puede guardar."""
    if not normalizar(meta.nombre):
        # Traductores: validación de metas del directo (error).
        return _("La meta necesita un nombre.")
    for otra in otras:
        if normalizar(otra.nombre) == normalizar(meta.nombre):
            # Traductores: validación de metas del directo (error). {nombre}
            # es la meta que ya existe.
            return _("La meta {nombre} ya existe.").format(
                nombre=meta.nombre)
    if (isinstance(meta.objetivo, bool)
            or not isinstance(meta.objetivo, int)
            or meta.objetivo <= 0):
        # Traductores: validación de metas del directo (error).
        return _("El objetivo tiene que ser un número entero mayor que cero.")
    if meta.que_cuenta not in QUE_CUENTA:
        # Traductores: validación de metas del directo (error).
        return _("Ese tipo de meta no existe.")
    return ""
