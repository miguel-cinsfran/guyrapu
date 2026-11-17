# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Traducciones del chat pedidas en segundo plano.

Un único servicio del proceso, como `chat_adicional`: la interfaz le dice
con `configurar` si traduce, a qué idioma y para quién, y `pedir` devuelve
un `Pedido` que se puede esperar sin tocar la red. El hilo del traductor
junta lo que llega en lotes de medio segundo, usa la `Cola` y la `Memoria`
del paquete, y avisa la caída y la vuelta una sola vez cada una.
"""

from __future__ import annotations

import atexit
import threading
import time

from guyrapu.core import diagnostico, esperas, vigilancia
from guyrapu.core.idioma import N_, _
from guyrapu.translation import filtro, idiomas
from guyrapu.translation.cola import Cola
from guyrapu.translation.memoria import Memoria
from guyrapu.translation.proveedores import obtener
from guyrapu.translation.proveedores.base import ErrorTraduccion

logger = diagnostico.obtener_logger(__name__)

TEXTO_CAIDA = N_("La traducción no responde. Se leen los mensajes originales.")
TEXTO_VUELTA = N_("La traducción volvió.")

# Cuánto se espera al proveedor y cada cuánto se mira la cola.
PLAZO = 5.0
INTERVALO = 0.1
# Espera entre intentos después de una falla: crece hasta un minuto.
CADENCIA = esperas.Creciente(5.0, 60.0)


class Pedido:
    """Una traducción pedida, con su espera y su resultado."""

    def __init__(self, texto, destino):
        self.texto = texto
        self.destino = destino
        self._evento = threading.Event()
        self._lock = threading.Lock()
        self._resultado = None
        self._callbacks = []

    @property
    def resultado(self):
        return self._resultado

    def esperar(self, segundos):
        """Espera a que llegue el resultado, sin red ni trabajo propio."""
        self._evento.wait(segundos)
        return self._resultado

    def al_terminar(self, funcion):
        """Llama a `funcion` cuando hay resultado, desde el hilo del traductor."""
        with self._lock:
            listo = self._evento.is_set()
            if not listo:
                self._callbacks.append(funcion)
        if listo:
            funcion()

    def _terminar(self, resultado):
        with self._lock:
            if self._evento.is_set():
                return
            self._resultado = resultado
            self._evento.set()
            callbacks, self._callbacks = self._callbacks, []
        for funcion in callbacks:
            funcion()


class _Servicio:
    """El traductor del proceso: pedidos, lotes, memoria y avisos."""

    def __init__(self, proveedor=None):
        self._lock = threading.RLock()
        self._config = {}
        self._activado = False
        self._modo = "voz_lista"
        self._destino = "es"
        self._memoria = Memoria()
        self._cola = None
        self._en_curso = {}
        self._pedidos = []
        self._descartar = 0
        self._intento = 0
        self._hilo = None
        self._parada = threading.Event()
        self._al_avisar = None
        self._proveedor = proveedor or obtener("google")
        self._vigilancia = vigilancia.Vigilancia(
            self._avisar,
            caida=vigilancia.Aviso(_(TEXTO_CAIDA), "chat_cortado"),
            vuelta=vigilancia.Aviso(_(TEXTO_VUELTA), "chat_reconectado"),
            rendicion=vigilancia.Aviso(_(TEXTO_CAIDA), "chat_cortado"))

    def configurar(self, config, al_avisar=None):
        """Aplica lo que eligió la interfaz: si traduce, modo y destino."""
        with self._lock:
            self._config = config
            if al_avisar is not None:
                self._al_avisar = al_avisar
            self._activado = bool(config.get("traducir_chat", False))
            self._modo = config.get("traducir_que", "voz_lista")
            destino = idiomas.destino(config)
            if destino != self._destino or self._cola is None:
                self._destino = destino
                self._cola = Cola(destino, self._memoria)
                self._en_curso.clear()
                self._pedidos.clear()
                self._descartar = 0

    def traduce_lista(self):
        """Si la lista del chat muestra la traducción."""
        with self._lock:
            return self._activado and self._modo == "voz_lista"

    def pedir(self, texto):
        """El pedido de ese texto, o None si no hay que traducirlo."""
        with self._lock:
            if not self._activado:
                return None
            if (self._modo == "solo_voz"
                    and self._config.get("silenciar_lectura", False)):
                return None
            if not texto or not filtro.traducible(texto):
                return None
            clave = texto.strip().lower()
            pedido = self._en_curso.get(clave)
            if pedido is not None:
                return pedido
            cacheada = self._memoria.obtener(texto, self._destino)
            pedido = Pedido(texto, self._destino)
            if cacheada is not None:
                pedido._terminar(cacheada)
                return pedido
            self._en_curso[clave] = pedido
            self._pedidos.append(pedido)
            self._cola.agregar(texto, time.monotonic())
            self._asegurar_hilo()
            return pedido

    def detener(self):
        """Para el hilo del traductor y suelta lo que esperaba."""
        with self._lock:
            self._parada.set()
            hilo, self._hilo = self._hilo, None
        if hilo is not None:
            hilo.join(timeout=5.0)

    def _asegurar_hilo(self):
        if self._hilo is not None and self._hilo.is_alive():
            return
        self._parada.clear()
        self._hilo = threading.Thread(
            target=self._correr, name="TraductorChat", daemon=True)
        self._hilo.start()

    def _correr(self):
        while not self._parada.is_set():
            cola = self._cola
            lote = self._lote(cola)
            if lote:
                self._traducir(cola, lote)
            self._recoger(cola)
            self._parada.wait(INTERVALO)

    def _lote(self, cola):
        if cola is None:
            return []
        with self._lock:
            if self._cola is not cola:
                return []
            return cola.lote_listo(time.monotonic())

    def _traducir(self, cola, lote):
        with self._lock:
            destino = self._destino
        try:
            traducciones = self._proveedor.traducir(lote, destino, PLAZO)
        except ErrorTraduccion as exc:
            logger.warning("traducción: %s", exc)
            self._fallar(cola, lote)
            return
        with self._lock:
            if self._cola is not cola:
                return
            cola.recibir(traducciones)
            self._intento = 0
            self._vigilancia.leida(True)

    def _fallar(self, cola, lote):
        with self._lock:
            if self._cola is not cola:
                return
            cola.fallo()
            self._descartar += len(lote)
            self._vigilancia.leida(False)
            self._intento += 1
            retraso = CADENCIA.espera(self._intento - 1, 0)
        for _texto in lote:
            self._entregar(None)
        self._parada.wait(retraso)

    def _recoger(self, cola):
        if cola is None:
            return
        with self._lock:
            if self._cola is not cola:
                return
            resultados = cola.entregables(time.monotonic())
            if self._descartar:
                cuantos = min(self._descartar, len(resultados))
                self._descartar -= cuantos
                resultados = resultados[cuantos:]
        for resultado in resultados:
            self._entregar(
                resultado if resultado is not None and resultado.origen else None)

    def _entregar(self, resultado):
        with self._lock:
            if not self._pedidos:
                return
            pedido = self._pedidos.pop(0)
            self._en_curso.pop(pedido.texto.strip().lower(), None)
        pedido._terminar(resultado)

    def _avisar(self, frase, sonido):
        llamar = self._al_avisar
        if llamar is None:
            logger.warning("%s", frase)
            return
        try:
            llamar(frase, sonido)
        except Exception as exc:
            logger.debug("no se pudo avisar de la traducción: %s", exc)


_SERVICIO = None


def _servicio():
    global _SERVICIO
    if _SERVICIO is None:
        _SERVICIO = _Servicio()
    return _SERVICIO


def configurar(config, al_avisar=None):
    _servicio().configurar(config, al_avisar)


def pedir(texto):
    return _servicio().pedir(texto)


def traduce_lista():
    return _servicio().traduce_lista()


def detener():
    global _SERVICIO
    servicio, _SERVICIO = _SERVICIO, None
    if servicio is not None:
        servicio.detener()


atexit.register(detener)
