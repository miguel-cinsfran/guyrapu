# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Conexión con el WebSocket de estado de Restream y su reconexión.

Un hilo conecta con la dirección indicada, entrega cada texto a la función
recibida y reintenta con espera creciente hasta que se pide la parada. El
token se lee en cada intento y nunca se registra, ni en la dirección ni en
el texto de la excepción.
"""

from __future__ import annotations

import threading
import time
from urllib.parse import quote

from websockets.sync.client import connect

from guyrapu.core import diagnostico, esperas

logger = diagnostico.obtener_logger(__name__)

DIRECCION = "wss://streaming.api.restream.io/ws"
ESPERA_MINIMA = 2.0
ESPERA_MAXIMA = 30.0
INTERVALO_LECTURA = 1.0


class _CadenciaDeReintento:
    """Crece con cada espera y vuelve al mínimo tras una conexión abierta."""

    def __init__(self):
        self._intentos = 0
        self._creciente = esperas.Creciente(ESPERA_MINIMA, ESPERA_MAXIMA)

    def reiniciar(self):
        self._intentos = 0

    def espera(self, intento, transcurrido):
        valor = self._creciente.espera(self._intentos, transcurrido)
        self._intentos += 1
        return valor


class _TiempoDeVigia:
    """Reloj real y el dormir que inyectan las pruebas."""

    def __init__(self, esperar):
        self._esperar = esperar

    def ahora(self):
        return time.monotonic()

    def dormir(self, segundos, parada=None):
        return bool(self._esperar(segundos))


def direccion_con_token(direccion, token):
    """Agrega el token a la dirección, sin dejarlo en el registro."""
    separador = "&" if "?" in direccion else "?"
    return f"{direccion}{separador}accessToken={quote(token, safe='')}"


class VigiaSenal:
    """Vigila el estado de Restream mientras dura una transmisión."""

    def __init__(self, leer_token, al_recibir, direccion=DIRECCION,
                 conectar_fn=None, parada=None, debe_seguir=None,
                 esperar=None, intervalo=INTERVALO_LECTURA):
        self._leer_token = leer_token
        self._al_recibir = al_recibir
        self._direccion = direccion
        self._conectar_fn = conectar_fn or connect
        self._parada = parada or threading.Event()
        self._debe_seguir = debe_seguir or (lambda: True)
        self._esperar = esperar or self._parada.wait
        self._intervalo = intervalo
        self._hilo = None

    @property
    def activa(self):
        return self._hilo is not None and self._hilo.is_alive()

    def iniciar(self):
        if self.activa:
            return
        self._parada.clear()
        self._hilo = diagnostico.crear_hilo(self._vigilar, "VigiaRestream")
        self._hilo.start()

    def detener(self):
        self._parada.set()
        hilo = self._hilo
        if hilo is not None and hilo is not threading.current_thread():
            hilo.join(2.0)

    def _seguir(self):
        return not self._parada.is_set() and self._debe_seguir()

    def _token(self):
        try:
            return self._leer_token() or ""
        except Exception as error:
            logger.warning("no se pudo leer el token de Restream: %s",
                           type(error).__name__)
            return ""

    def _vigilar(self):
        cadencia = _CadenciaDeReintento()

        def consultar():
            if not self._seguir():
                return False
            token = self._token()
            if not token:
                return True
            try:
                with self._conectar_fn(
                        direccion_con_token(self._direccion, token)) as conexion:
                    cadencia.reiniciar()
                    self._escuchar(conexion)
            except Exception as error:
                logger.warning("se cortó la conexión con Restream: %s",
                               type(error).__name__)
            return self._seguir()

        esperas.esperar(
            consultar, lambda valor: not valor, cadencia=cadencia,
            parada=self._parada, tiempo=_TiempoDeVigia(self._esperar))

    def _escuchar(self, conexion):
        while self._seguir():
            try:
                mensaje = conexion.recv(timeout=self._intervalo)
            except TimeoutError:
                continue
            try:
                self._al_recibir(mensaje)
            except Exception as error:
                logger.warning("no se pudo procesar un mensaje de Restream: %s",
                               type(error).__name__)
