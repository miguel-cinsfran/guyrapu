# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Candado compartido para que las consultas a OBS no caigan en un cambio.

OBS 33 se cierra si recibe una consulta de estadísticas o de estado de una
salida mientras aplica un cambio de perfil o de vídeo. Los pedidos entran
por clientes distintos en hilos distintos, así que el candado vive en el
proceso y no en cada cliente.

Es un candado de lectores y escritores con preferencia por el escritor:
varias consultas conviven, el cambio entra solo, y apenas un cambio espera
dejan de entrar consultas nuevas para que no lo pospongan sin fin.
"""

import threading

PEDIDOS_QUE_CAMBIAN = frozenset({
    "SetCurrentProfile",
    "CreateProfile",
    "RemoveProfile",
    "SetVideoSettings",
})

PEDIDOS_QUE_LEEN = frozenset({
    "GetStats",
    "GetStreamStatus",
    "GetRecordStatus",
    "GetReplayBufferStatus",
    "GetVirtualCamStatus",
    "GetOutputStatus",
    "GetOutputList",
})


class EsperaCancelada(Exception):
    """La parada del pedido se puso mientras esperaba el candado."""


class CandadoDelProceso:
    """Candado de lectores y escritores que comparten los clientes.

    El escritor es reentrante por hilo, así el propio pedido que cambia
    puede consultar el perfil sin soltarlo. Se toma siempre antes del
    cerrojo de cada cliente: el orden inverso traba dos hilos.
    """

    def __init__(self):
        self._condicion = threading.Condition(threading.Lock())
        self._lectores = 0
        self._escritor = None
        self._profundidad = 0
        self._escritores_esperando = 0

    def adquirir(self, parada=None, escribe=False):
        hilo = threading.get_ident()
        with self._condicion:
            if escribe:
                self._entrar_escritor(hilo, parada)
            else:
                self._entrar_lector(hilo, parada)

    def _entrar_escritor(self, hilo, parada):
        if self._escritor == hilo:
            self._profundidad += 1
            return
        self._escritores_esperando += 1
        try:
            while self._escritor is not None or self._lectores:
                self._esperar(parada)
            self._escritor = hilo
            self._profundidad = 1
        finally:
            self._escritores_esperando -= 1

    def _entrar_lector(self, hilo, parada):
        if self._escritor == hilo:
            return
        while self._escritor is not None or self._escritores_esperando:
            self._esperar(parada)
        self._lectores += 1

    def _esperar(self, parada):
        if parada is not None and parada.is_set():
            raise EsperaCancelada()
        self._condicion.wait(0.1)
        if parada is not None and parada.is_set():
            raise EsperaCancelada()

    def liberar(self, escribe=False):
        with self._condicion:
            if escribe:
                self._liberar_escritor()
            else:
                self._liberar_lector()

    def _liberar_escritor(self):
        if self._escritor != threading.get_ident():
            raise RuntimeError("El candado no lo tiene este hilo.")
        self._profundidad -= 1
        if self._profundidad == 0:
            self._escritor = None
            self._condicion.notify_all()

    def _liberar_lector(self):
        if self._escritor == threading.get_ident():
            # Lectura pedida por el mismo escritor: no sumó al contador.
            return
        self._lectores -= 1
        if self._lectores == 0:
            self._condicion.notify_all()


CANDADO = CandadoDelProceso()
