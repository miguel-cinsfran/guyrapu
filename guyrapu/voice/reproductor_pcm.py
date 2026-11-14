# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Reproductor de trozos PCM float32 mono por una salida WASAPI.

Es el único módulo que importa sounddevice. Después del constructor ningún
error de la biblioteca sale de acá: se registra y el reproductor queda mudo,
como el motor de Prism.
"""

from __future__ import annotations

import threading

import numpy as np
import sounddevice as sd

from guyrapu.core import diagnostico

logger = diagnostico.obtener_logger(__name__)

_NOMBRE_WASAPI = "WASAPI"
_SEGUNDOS_COLA = 2.0


def _hostapi_wasapi():
    try:
        for indice, api in enumerate(sd.query_hostapis()):
            if _NOMBRE_WASAPI in api.get("name", ""):
                return indice, api
    except Exception as exc:
        logger.warning("No se pudieron consultar las APIs de audio: %s", exc)
    return None, None


def _salidas_wasapi():
    _indice, api = _hostapi_wasapi()
    if api is None:
        return []
    salidas = []
    for dispositivo in api.get("devices", []):
        try:
            datos = sd.query_devices(dispositivo)
        except Exception as exc:
            logger.debug("No se pudo consultar el dispositivo %s: %s",
                         dispositivo, exc)
            continue
        if datos.get("max_output_channels", 0) > 0:
            salidas.append((int(dispositivo), datos["name"]))
    return salidas


def listar_salidas() -> list[str]:
    """Devuelve los nombres de las salidas de audio de la API WASAPI."""
    return [nombre for _indice, nombre in _salidas_wasapi()]


def _salida_predeterminada():
    _indice, api = _hostapi_wasapi()
    if api is not None:
        predeterminada = api.get("default_output_device")
        if predeterminada is not None and int(predeterminada) >= 0:
            return int(predeterminada)
    return None


class ReproductorPCM:
    """Reproduce trozos float32 mono con corte, pausa y reanudación."""

    def __init__(self, dispositivo=None):
        self._cerrado = False
        self._mudo = False
        self._stream = None
        self._tasa = None
        self._audio = np.empty(0, np.float32)
        self._fin = False
        self._sonando = False
        self._pausado = False
        self._generacion = 0
        self._cond = threading.Condition()
        self._consumidas = 0
        self._corte_confirmado = threading.Event()
        self._esperando_corte = False
        self._aviso_dispositivo = False
        self._dispositivo = self._elegir_dispositivo(dispositivo)

    def _elegir_dispositivo(self, nombre):
        if nombre is None:
            return _salida_predeterminada()
        salidas = _salidas_wasapi()
        for indice, etiqueta in salidas:
            if etiqueta == nombre:
                return indice
        if not self._aviso_dispositivo:
            logger.warning(
                "No existe la salida de audio «%s»; se usa la predeterminada.",
                nombre)
            self._aviso_dispositivo = True
        return _salida_predeterminada()

    def empezar(self, tasa: int) -> None:
        """Abre o reabre el flujo si cambió la tasa de muestreo."""
        if self._cerrado:
            return
        tasa = int(tasa)
        if self._stream is not None and self._tasa == tasa:
            return
        self._cerrar_stream()
        try:
            self._stream = sd.OutputStream(
                samplerate=tasa, channels=1, dtype="float32",
                device=self._dispositivo,
                extra_settings=sd.WasapiSettings(auto_convert=True),
                callback=self._callback)
            self._stream.start()
            self._tasa = tasa
            self._mudo = False
        except Exception as exc:
            logger.warning("No se pudo abrir la salida de audio a %s Hz: %s",
                           tasa, exc)
            self._stream = None
            self._tasa = None
            self._mudo = True

    def encolar(self, trozo) -> None:
        """Encola muestras y espera si la cola ya pasa de dos segundos."""
        if self._cerrado or self._mudo or self._stream is None:
            return
        datos = np.asarray(trozo, dtype=np.float32).reshape(-1)
        if not len(datos):
            return
        with self._cond:
            generacion = self._generacion
            limite = int(self._tasa * _SEGUNDOS_COLA) if self._tasa else 0
            while (not self._cerrado and generacion == self._generacion
                   and limite and len(self._audio) > limite):
                self._cond.wait(0.05)
            if self._cerrado or generacion != self._generacion:
                return
            self._audio = np.concatenate([self._audio, datos])
            self._fin = False
            self._sonando = True
            self._cond.notify_all()

    def terminar(self) -> None:
        """Marca el fin de la frase que se está encolando."""
        if self._cerrado:
            return
        with self._cond:
            self._fin = True
            if not len(self._audio):
                self._sonando = False
            self._cond.notify_all()

    def cortar(self) -> None:
        """Vacía la cola y desbloquea a quien espera en `encolar`."""
        if self._cerrado:
            return
        with self._cond:
            self._generacion += 1
            self._audio = np.empty(0, np.float32)
            self._fin = False
            self._sonando = False
            self._esperando_corte = True
            self._corte_confirmado.clear()
            self._cond.notify_all()
        if (self._stream is None or self._mudo
                or not self._stream.active):
            self._corte_confirmado.set()

    def pausar(self) -> None:
        """Detiene el sonido sin perder lo encolado."""
        if self._cerrado:
            return
        with self._cond:
            self._pausado = True

    def reanudar(self) -> None:
        """Retoma el sonido desde donde quedó."""
        if self._cerrado:
            return
        with self._cond:
            self._pausado = False
            self._cond.notify_all()

    @property
    def sonando(self) -> bool:
        return self._sonando

    def cerrar(self) -> None:
        """Suelta el dispositivo; después todo es no-op."""
        if self._cerrado:
            return
        self._cerrado = True
        with self._cond:
            self._generacion += 1
            self._audio = np.empty(0, np.float32)
            self._fin = False
            self._sonando = False
            self._cond.notify_all()
        self._cerrar_stream()

    def _cerrar_stream(self) -> None:
        stream, self._stream = self._stream, None
        self._tasa = None
        if stream is None:
            return
        try:
            stream.stop()
        except Exception as exc:
            logger.debug("No se pudo detener la salida de audio: %s", exc)
        try:
            stream.close()
        except Exception as exc:
            logger.debug("No se pudo cerrar la salida de audio: %s", exc)

    def _callback(self, salida, cuadros, tiempo, estado) -> None:
        try:
            self._rellenar(salida, cuadros)
        except Exception as exc:
            salida.fill(0)
            logger.debug("No se pudo rellenar la salida de audio: %s", exc)

    def _rellenar(self, salida, cuadros: int) -> None:
        with self._cond:
            if self._esperando_corte:
                self._esperando_corte = False
                self._corte_confirmado.set()
            if self._cerrado or self._pausado:
                salida.fill(0)
                return
            tomar = min(cuadros, len(self._audio))
            if tomar:
                salida[:tomar, 0] = self._audio[:tomar]
            if tomar < cuadros:
                salida[tomar:, 0] = 0
            if tomar:
                self._audio = self._audio[tomar:]
                self._consumidas += tomar
            if self._fin and not len(self._audio):
                self._sonando = False
            self._cond.notify_all()
