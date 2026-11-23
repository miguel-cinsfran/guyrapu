# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Qué se responde a un mensaje del chat con un comando.

Puro y sin wx ni captura. Su única razón para cambiar es qué respuesta
merece un mensaje del chat: los permisos, las esperas, las variables, el
destino, el freno de cuota y el eco de lo que la app mandó al chat.

El estado del chat y de la cuota llega como argumento. Acá viven las esperas,
los contadores de la sesión y las respuestas que salieron al chat.
"""

from __future__ import annotations

from dataclasses import dataclass

from guyrapu.core import plataformas
from guyrapu.core.config import TIPO_TEXTO
from guyrapu.core.idioma import _
from guyrapu.interaction import (
    comandos, descripcion_comando, filtro_publico, informe_ensayo)
from guyrapu.interaction.texto import normalizar

ESPERA_CHAT = 30
VENTANA_ECO = 120


@dataclass(frozen=True, slots=True)
class Respuesta:
    """Lo que la app contesta, a qué destinos y con qué estilo y segundos."""

    texto: str
    al_video: bool
    al_chat: bool
    estilo: str
    segundos: int
    nombre: str
    freno_cuota: bool = False
    medio: str = ""


def repartir(destino, evento, ahora, chat_disponible, cuota_baja, ultimo_chat):
    """A dónde va lo que sale, si la cuota cortó el chat y el último envío.

    Lo comparten las respuestas de los comandos y las alertas: cada una lleva
    su propio último envío al chat.
    """
    pide_chat = destino in ("chat", "ambos")
    al_video = destino in ("video", "ambos")
    if not pide_chat:
        return al_video, False, False, ultimo_chat
    al_chat = (evento.plataforma == plataformas.YOUTUBE
               and chat_disponible)
    freno = False
    if al_chat and cuota_baja:
        al_chat = False
        freno = True
    elif al_chat and ultimo_chat is not None and (
            ahora - ultimo_chat < ESPERA_CHAT):
        al_chat = False
    if al_chat:
        ultimo_chat = ahora
    return al_video or not al_chat, al_chat, freno, ultimo_chat


class Atencion:
    """Decide la respuesta de un mensaje y guarda el estado de la sesión."""

    def __init__(self, disponibles=()):
        self._comandos = list(disponibles)
        self._palabras_bloqueadas = []
        self._esperas = comandos.Esperas()
        self._contadores: dict[str, int] = {}
        self._al_chat: list[tuple[float, str]] = []
        self._ultimo_chat = None

    def fijar_comandos(self, disponibles) -> None:
        self._comandos = list(disponibles)

    def fijar_palabras_bloqueadas(self, palabras) -> None:
        self._palabras_bloqueadas = list(palabras)

    def atender(self, evento, ahora, *, chat_disponible=False,
                cuota_baja=False, atajo=0):
        """La respuesta que merece el mensaje o el atajo, o None."""
        if evento.tipo != TIPO_TEXTO or self._es_eco(evento, ahora):
            return None
        if atajo:
            comando = next((c for c in self._comandos
                            if c.activo and c.atajo == atajo), None)
            invocacion = (comandos.Invocacion(comando.nombre, "")
                          if comando is not None else None)
        else:
            invocacion = comandos.leer(evento.texto)
            if invocacion is not None:
                comando = comandos.buscar(self._comandos, invocacion)
            else:
                comando = comandos.buscar_en_mensaje(
                    self._comandos, evento.texto)
                invocacion = (comandos.Invocacion(comando.nombre, "")
                              if comando is not None else None)
            if comando is not None and not comandos.puede_usarlo(comando, evento):
                comando = None
        if comando is None or invocacion is None:
            return None
        if comando.lista and not self._lista_de():
            return None
        if not self._esperas.libre(comando, evento, ahora):
            return None
        self._esperas.anotar(comando, evento, ahora)
        return self._respuesta(comando, invocacion, evento, ahora,
                               chat_disponible, cuota_baja)

    def motivo(self, evento, ahora):
        """Por qué no respondió, sin consumir esperas ni cambiar el estado."""
        if evento.tipo != TIPO_TEXTO or self._eco(evento):
            return ""
        comando = self._comando_de(evento)
        if comando is None:
            return ""
        if not comando.activo:
            return _(informe_ensayo.MOTIVO_PAUSA_COMANDO).format(
                nombre=comando.nombre)
        if not comandos.puede_usarlo(comando, evento):
            return _(informe_ensayo.MOTIVO_PERMISO).format(
                nombre=comando.nombre,
                permiso=descripcion_comando._quien(comando))
        segundos = self._esperas.faltan(comando, evento, ahora)
        if segundos:
            return _(informe_ensayo.MOTIVO_ESPERA_COMANDO).format(
                nombre=comando.nombre, segundos=segundos)
        return ""

    def _comando_de(self, evento):
        invocacion = comandos.leer(evento.texto)
        if invocacion is not None:
            return comandos.buscar(self._comandos, invocacion, activos=False)
        return comandos.buscar_en_mensaje(
            self._comandos, evento.texto, activos=False)

    def _lista_de(self):
        """Los nombres de los comandos activos que pidieron aparecer."""
        return ", ".join(
            ("" if comando.ubicacion == "cualquiera" else "!")
            + comando.nombre for comando in self._comandos
            if comando.activo and comando.en_lista and not comando.lista
            and comando.permiso != "solo_atajo")

    def _respuesta(self, comando, invocacion, evento, ahora,
                   chat_disponible, cuota_baja):
        contador = self._contadores.get(comando.nombre, 0) + 1
        self._contadores[comando.nombre] = contador
        texto = (comando.respuesta or "")
        if comando.lista:
            texto = texto.replace("{lista}", self._lista_de())
        texto = texto.replace(
            "{usuario}",
            filtro_publico.tapar(evento.autor or "",
                                 self._palabras_bloqueadas))
        texto = texto.replace("{contador}", str(contador))
        publico = invocacion.argumentos
        if filtro_publico.es_casi_todo_simbolos(publico):
            publico = ""
        publico = filtro_publico.tapar(publico, self._palabras_bloqueadas)
        texto = texto.replace("{texto}", publico[:100])
        al_video, al_chat, freno = self._destinos(
            comando.destino, evento, ahora, chat_disponible, cuota_baja)
        if al_chat:
            self._recordar(texto, ahora)
        return Respuesta(texto, al_video, al_chat, comando.estilo,
                         comando.segundos, comando.nombre, freno,
                         comando.medio)

    def _destinos(self, destino, evento, ahora, chat_disponible,
                  cuota_baja):
        """A dónde va la respuesta y si la cuota cortó el envío al chat."""
        al_video, al_chat, freno, self._ultimo_chat = repartir(
            destino, evento, ahora, chat_disponible, cuota_baja,
            self._ultimo_chat)
        return al_video, al_chat, freno

    def _es_eco(self, evento, ahora):
        if evento.plataforma != plataformas.YOUTUBE:
            return False
        self._podar(ahora)
        return self._eco(evento)

    def _eco(self, evento):
        clave = normalizar(evento.texto)
        return any(texto == clave for _instante, texto in self._al_chat)

    def _recordar(self, texto, ahora):
        self._al_chat.append((ahora, normalizar(texto)))
        self._podar(ahora)

    def _podar(self, ahora):
        self._al_chat = [
            (instante, texto) for instante, texto in self._al_chat
            if ahora - instante < VENTANA_ECO]
