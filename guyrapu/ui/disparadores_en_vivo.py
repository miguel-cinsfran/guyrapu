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

import time

from guyrapu.core import diagnostico, paths, plataformas
from guyrapu.core.config import TIPO_TEXTO
from guyrapu.core.idioma import _
from guyrapu.core.sonidos_eventos import ROL_PROPIETARIO
from guyrapu.interaction import (
    comandos, disparadores, disparadores_guardados, filtro_publico,
    medios_guardados)
from guyrapu.interaction.cola_pantalla import Pieza
from guyrapu.interaction.evento import desde_entrante
from guyrapu.ui import gui_envio_chat
from guyrapu.ui.accesibilidad import anunciar_con_sonido

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


def disparar(frame, numero, ahora=None) -> None:
    """Dispara los disparadores de ese número con la instancia de la ventana."""
    _en_vivo(frame).disparar(numero, ahora)


def _evento(registro):
    return desde_entrante(
        registro.autor, registro.texto, registro.tipo, registro.monto,
        registro.identificador, registro.rol, registro.plataforma)


def _evento_del_dueno():
    return desde_entrante(
        "", "", TIPO_TEXTO, "", "", ROL_PROPIETARIO,
        plataformas.YOUTUBE)


class DisparadoresEnVivo:
    """Los disparadores de una sesión y su tarjeta en el vídeo."""

    def __init__(self, frame):
        self._frame = frame
        self._disparadores = []
        self._palabras_bloqueadas = []
        self._esperas = comandos.Esperas()
        self._cargado = False
        self._mtime = None
        self._cargado_palabras = False
        self._mtime_palabras = None

    def atender(self, registro, ahora) -> None:
        if not self._frame._conectado:
            return
        self._recargar()
        evento = _evento(registro)
        for disparador in disparadores.cumplidos(
                self._disparadores, evento, self._esperas, ahora):
            self._poner(disparador, evento)

    def disparar(self, numero, ahora=None) -> None:
        """Dispara los activos de ese número como si los pidiera el dueño."""
        if not self._frame._conectado:
            anunciar_con_sonido(
                _("Conecta un directo para usar los disparadores"), "error")
            return
        self._recargar()
        elegidos = disparadores.por_atajo(self._disparadores, numero)
        if not elegidos:
            anunciar_con_sonido(
                _("Ningún disparador usa Ctrl+Alt+Mayús+{numero}").format(
                    numero=numero), "error")
            return
        if ahora is None:
            ahora = time.monotonic()
        evento = _evento_del_dueno()
        for disparador in elegidos:
            if not self._esperas.libre(disparador, evento, ahora):
                continue
            self._esperas.anotar(disparador, evento, ahora)
            self._poner(disparador, evento)

    def _poner(self, disparador, evento) -> None:
        tarjeta = (disparador.tarjeta or "").strip()
        medio = self._medio(disparador.medio)
        if not tarjeta and medio is None:
            return
        if tarjeta:
            texto = (disparador.tarjeta or "").replace(
                "{usuario}",
                filtro_publico.tapar(evento.autor or "",
                                     self._palabras_bloqueadas))
        else:
            texto = ""
        segundos = disparador.segundos
        datos = {"estilo": disparador.estilo, "nombre": disparador.nombre}
        if medio is not None:
            datos["medio"] = medio
            if medio["tipo"] in ("sonido", "video") and medio["duracion"]:
                segundos = max(1, medio["duracion"])
        pieza = Pieza(tipo="disparador", texto=texto, segundos=segundos,
                      datos=datos)
        gui_envio_chat.capa_de_video(self._frame).agregar_pieza(pieza)

    def _medio(self, nombre):
        """El medio de la biblioteca con ese nombre, o None si ya no está."""
        return medios_guardados.medio_para_video(
            medios_guardados.cargar(paths.medios()),
            paths.carpeta_medios(), nombre)

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
