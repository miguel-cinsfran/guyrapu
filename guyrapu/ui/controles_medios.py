# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Controles de medios de Windows para la ventana principal de Guyrapu.

Una sola responsabilidad: hablar con `SystemMediaTransportControls`. El
paquete es opcional: si falta o Windows lo rechaza, no se toma ninguna tecla
y queda anotado en el registro, sin avisos para el usuario.
"""

from __future__ import annotations

import wx

from guyrapu.core import diagnostico
from guyrapu.music import medios_sistema

try:
    from winrt.windows.media import (
        MediaPlaybackStatus, MediaPlaybackType)
    from winrt.windows.media.interop import get_for_window
except Exception:
    MediaPlaybackStatus = MediaPlaybackType = None
    get_for_window = None


logger = diagnostico.obtener_logger(__name__)


class ControlesMedios:
    """Prende, apaga y pone al día los controles de medios de una ventana."""

    def __init__(self, ventana, ejecutar_atajo) -> None:
        self._ventana = ventana
        self._ejecutar = ejecutar_atajo
        self._controles = None
        self._mostrado = None
        self._anotado = False

    def poner_al_dia(self, estado, activo: bool) -> None:
        """Toma o suelta las teclas y muestra el tema y la pausa."""
        if not activo or estado is None or not estado.cola:
            self.desactivar()
            return
        controles = self._tomar()
        if controles is None:
            return
        try:
            controles.is_enabled = True
            for nombre in ("is_play_enabled", "is_pause_enabled",
                           "is_next_enabled", "is_previous_enabled",
                           "is_stop_enabled"):
                setattr(controles, nombre, True)
            self._mostrar(controles, estado)
        except Exception as error:
            self._anotar("el sistema rechazó los controles de medios", error)
            self.desactivar()

    def desactivar(self) -> None:
        """Suelta las teclas para que vuelvan a quien las tenía."""
        self._mostrado = None
        if self._controles is None:
            return
        try:
            self._controles.is_enabled = False
        except Exception as error:
            self._anotar("no se pudieron soltar los controles de medios", error)

    def soltar(self) -> None:
        """Suelta las teclas al cerrar la aplicación."""
        self.desactivar()
        self._controles = None

    def _tomar(self):
        """Los controles de la ventana, o None si no están o los rechazan."""
        if self._controles is not None:
            return self._controles
        if get_for_window is None:
            self._anotar("no están los controles de medios de Windows")
            return None
        try:
            controles = get_for_window(self._ventana.GetHandle())
            controles.add_button_pressed(self._al_boton)
        except Exception as error:
            self._anotar("el sistema rechazó los controles de medios", error)
            return None
        self._controles = controles
        return controles

    def _mostrar(self, controles, estado) -> None:
        """Llena título, artista y estado de reproducción del panel."""
        titulo, artista = medios_sistema.titulo_y_artista(estado.actual)
        pausado = bool(estado.pausado)
        if self._mostrado == (titulo, artista, pausado):
            return
        self._mostrado = (titulo, artista, pausado)
        actualizador = controles.display_updater
        actualizador.type = MediaPlaybackType.MUSIC
        propiedades = actualizador.music_properties
        propiedades.title = titulo
        propiedades.artist = artista
        actualizador.update()
        controles.playback_status = (
            MediaPlaybackStatus.PAUSED if pausado
            else MediaPlaybackStatus.PLAYING)

    def _al_boton(self, _controles, argumentos) -> None:
        """Manda al hilo de la interfaz la acción del botón que llegó."""
        accion = medios_sistema.accion_de_boton(
            getattr(getattr(argumentos, "button", None), "name", ""))
        if accion is None:
            return
        wx.CallAfter(self._ejecutar, accion)

    def _anotar(self, motivo, error=None) -> None:
        """Anota una sola vez que los controles no están disponibles."""
        if self._anotado:
            return
        self._anotado = True
        logger.warning("%s: %s", motivo, error or "no disponible")
