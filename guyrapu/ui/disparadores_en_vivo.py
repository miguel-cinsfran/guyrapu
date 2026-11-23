# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Atiende los disparadores del directo y pone su tarjeta en el vídeo.

Une la decisión pura de `disparadores` con la app: carga los disparadores y
las palabras bloqueadas del archivo, arma el evento desde el mensaje y, con
el chat conectado, agrega la tarjeta al vídeo.

La atiende `chat_vivo.encolar`, que registra cualquier error sin cortar la
lectura del chat.
"""

from __future__ import annotations

from guyrapu.core import diagnostico, paths
from guyrapu.interaction import (
    comandos, conversion_disparadores, disparadores, disparadores_guardados,
    ensayo, filtro_publico, medio_en_video)
from guyrapu.interaction.cola_pantalla import Pieza
from guyrapu.interaction.evento import desde_entrante
from guyrapu.ui import gui_envio_chat

logger = diagnostico.obtener_logger(__name__)


def _en_vivo(frame):
    en_vivo = getattr(frame, "_disparadores_en_vivo", None)
    if en_vivo is None:
        en_vivo = DisparadoresEnVivo(frame)
        frame._disparadores_en_vivo = en_vivo
    return en_vivo


def atender(frame, registro, ahora) -> None:
    """Atiende el mensaje con la instancia de disparadores de esa ventana."""
    _en_vivo(frame).atender(registro, ahora)


def _evento(registro):
    return desde_entrante(
        registro.autor, registro.texto, registro.tipo, registro.monto,
        registro.identificador, registro.rol, registro.plataforma)


class DisparadoresEnVivo:
    """Los disparadores de una sesión y su tarjeta en el vídeo."""

    def __init__(self, frame):
        conversion_disparadores.convertir_en_disco()
        self._frame = frame
        self._disparadores = []
        self._palabras_bloqueadas = []
        self._esperas = comandos.Esperas()
        self._contadores: dict[str, int] = {}
        self._cargado = False
        self._mtime = None
        self._cargado_palabras = False
        self._mtime_palabras = None

    def atender(self, registro, ahora) -> None:
        if not ensayo.en_vivo_o_ensayo(self._frame):
            return
        self._recargar()
        evento = _evento(registro)
        for disparador in disparadores.cumplidos(
                self._disparadores, evento, self._esperas, ahora):
            self._poner(disparador, evento)

    def _poner(self, disparador, evento) -> None:
        tarjeta = (disparador.tarjeta or "").strip()
        medio = medio_en_video.resolver(disparador.medio)
        if not tarjeta and medio is None:
            return
        contador = self._contadores.get(disparador.nombre, 0) + 1
        self._contadores[disparador.nombre] = contador
        if tarjeta:
            texto = disparadores.texto_de_tarjeta(
                disparador, evento, contador, self._palabras_bloqueadas)
        else:
            texto = ""
        segundos = disparador.segundos
        datos = {"estilo": disparador.estilo, "nombre": disparador.nombre}
        datos, segundos = medio_en_video.con_medio(datos, segundos, medio)
        pieza = Pieza(tipo="disparador", texto=texto, segundos=segundos,
                      datos=datos)
        gui_envio_chat.capa_de_video(self._frame).agregar_pieza(pieza)

    def _recargar(self) -> None:
        """Vuelve a leer los disparadores y las palabras si cambiaron."""
        self._recargar_disparadores()
        self._recargar_palabras()

    def _recargar_disparadores(self) -> None:
        ruta = paths.disparadores()
        try:
            mtime = ruta.stat().st_mtime_ns
        except OSError:
            mtime = None
        if self._cargado and mtime == self._mtime:
            return
        self._cargado = True
        self._mtime = mtime
        self._disparadores = [
            disparadores_guardados.a_disparador(datos)
            for datos in disparadores_guardados.cargar(ruta)]

    def _recargar_palabras(self) -> None:
        ruta = paths.palabras_bloqueadas()
        try:
            mtime = ruta.stat().st_mtime_ns
        except OSError:
            mtime = None
        if self._cargado_palabras and mtime == self._mtime_palabras:
            return
        self._cargado_palabras = True
        self._mtime_palabras = mtime
        self._palabras_bloqueadas = filtro_publico.cargar(ruta)
