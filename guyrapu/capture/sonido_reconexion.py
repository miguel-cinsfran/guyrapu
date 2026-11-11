# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Qué sonido le toca a cada estado de la conexión de un chat.

Una sesión de conexión recuerda si llegó a conectarse alguna vez y si
ahora lo está. Cada estado que recibe devuelve el evento que hay que
sonar, o None si no toca ninguno. Es puro: sin wx ni audio.
"""


class SonidoReconexion:
    def __init__(self):
        self._hubo_conexion = False
        self._conectado = False

    def recibir(self, estado):
        """Evento que suena para `estado`, o None."""
        if estado == "reintentando":
            if self._conectado:
                self._conectado = False
                return "chat_cortado"
            return "conectando"
        if estado in ("conectado", "reconectado"):
            self._conectado = True
            if self._hubo_conexion:
                return "chat_reconectado"
            self._hubo_conexion = True
            return "conectado"
        if estado == "conectando":
            return "conectando"
        return None
