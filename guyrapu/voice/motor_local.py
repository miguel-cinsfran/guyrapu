# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Motor de voz local con la interfaz de `MotorPrism`.

El sintetizador entrega trozos float32 y este módulo los pasa por los ajustes
de audio antes de encolarlos en el reproductor PCM. La síntesis y el consumo
de la frase corren en un hilo propio con prioridad baja para no quitarle CPU
a OBS.
"""

from __future__ import annotations

import sys
import threading
from collections.abc import Iterator
from typing import Protocol

from guyrapu.core import diagnostico
from guyrapu.voice import ajustes_audio
from guyrapu.voice import escala_voz
from guyrapu.voice import reproductor_pcm

logger = diagnostico.obtener_logger(__name__)

HILOS_SINTESIS = 2

# THREAD_PRIORITY_BELOW_NORMAL de Windows.
_PRIORIDAD_BAJA = -1


class Sintetizador(Protocol):
    """Lo que el motor local espera de un sintetizador de trozos."""

    tasa: int
    rango_velocidad: tuple[float, float]
    ganancia_voz: float

    def voces(self) -> list[str]:
        ...

    def elegir_voz(self, idx) -> bool:
        ...

    def sintetizar(self, texto: str, velocidad_propia: float) -> Iterator:
        ...

    def cerrar(self) -> None:
        ...


def _bajar_prioridad() -> None:
    """Baja la prioridad del hilo que llama, solo en Windows."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.GetCurrentThread.restype = ctypes.c_void_p
        kernel32.SetThreadPriority.argtypes = [ctypes.c_void_p, ctypes.c_int]
        kernel32.SetThreadPriority.restype = ctypes.c_int
        kernel32.SetThreadPriority(kernel32.GetCurrentThread(), _PRIORIDAD_BAJA)
    except Exception as exc:
        logger.debug("No se pudo bajar la prioridad del hilo de voz: %s", exc)


def _inicializar_com() -> bool:
    """Inicializa COM en este hilo para que WASAPI pueda abrir el flujo.

    wx deja COM como STA en el hilo principal y los hilos nuevos no lo
    heredan. Sin esto, abrir la salida desde el hilo de síntesis falla con un
    error de WDM-KS.
    """
    if sys.platform != "win32":
        return False
    try:
        import ctypes
        # COINIT_MULTITHREADED; S_OK o S_FALSE cuentan como inicialización.
        return ctypes.windll.ole32.CoInitializeEx(None, 0) in (0, 1)
    except Exception as exc:
        logger.debug("No se pudo inicializar COM en el hilo de voz: %s", exc)
        return False


def _cerrar_com() -> None:
    try:
        import ctypes
        ctypes.windll.ole32.CoUninitialize()
    except Exception as exc:
        logger.debug("No se pudo cerrar COM en el hilo de voz: %s", exc)


class MotorLocal:
    """Un motor con la interfaz de `MotorPrism` sobre un sintetizador de trozos."""

    def __init__(self, sintetizador, reproductor=None):
        self._sintetizador = sintetizador
        self._reproductor = (reproductor if reproductor is not None
                             else reproductor_pcm.ReproductorPCM())
        self._velocidad = escala_voz.VELOCIDAD_NORMAL
        self._volumen = 100
        self._tono = escala_voz.VELOCIDAD_NORMAL
        self._hablando = False
        self._cerrado = False
        self._generacion = 0
        self._parada = threading.Event()
        self._hilo = None
        self._bloqueo = threading.Lock()

    def voces(self) -> list[str]:
        if self._cerrado:
            return []
        try:
            return list(self._sintetizador.voces())
        except Exception as exc:
            logger.warning("Listar voces del motor local: %s", exc)
            return []

    def elegir_voz(self, idx) -> bool:
        if self._cerrado:
            return False
        try:
            return bool(self._sintetizador.elegir_voz(idx))
        except Exception as exc:
            logger.warning("Elegir voz %s en el motor local: %s", idx, exc)
            return False

    def hablar(self, texto) -> bool:
        """Lanza la frase sin bloquear. False con texto vacío o motor cerrado."""
        if self._cerrado:
            return False
        limpio = (texto or "").replace("\x00", "")
        if not limpio:
            return False
        with self._bloqueo:
            if self._cerrado:
                return False
            anterior = self._hilo
            if anterior is not None and anterior.is_alive():
                self._parada.set()
                self._reproductor.cortar()
            self._generacion += 1
            generacion = self._generacion
            parada = threading.Event()
            self._parada = parada
            self._hablando = True
            hilo = threading.Thread(
                target=self._sintetizar,
                args=(limpio, generacion, parada),
                name="guyrapu-voz-local", daemon=True)
            self._hilo = hilo
            hilo.start()
        return True

    def hablando(self) -> bool:
        return self._hablando and not self._cerrado

    def parar(self) -> None:
        if self._cerrado:
            return
        with self._bloqueo:
            self._parada.set()
            self._generacion += 1
            self._hablando = False
            self._reproductor.cortar()

    def pausar(self) -> None:
        if not self._cerrado:
            self._reproductor.pausar()

    def reanudar(self) -> None:
        if not self._cerrado:
            self._reproductor.reanudar()

    def fijar_velocidad(self, pct) -> None:
        if self._cerrado:
            return
        try:
            self._velocidad = max(escala_voz.VELOCIDAD_MIN,
                                  min(escala_voz.VELOCIDAD_MAX, int(pct)))
        except (TypeError, ValueError):
            pass

    def fijar_volumen(self, pct) -> None:
        if self._cerrado:
            return
        try:
            self._volumen = max(escala_voz.VELOCIDAD_MIN,
                                min(escala_voz.VELOCIDAD_MAX, int(pct)))
        except (TypeError, ValueError):
            pass

    def fijar_tono(self, pct) -> None:
        if self._cerrado:
            return
        try:
            self._tono = max(escala_voz.VELOCIDAD_MIN,
                             min(escala_voz.VELOCIDAD_MAX, int(pct)))
        except (TypeError, ValueError):
            pass

    def cerrar(self) -> None:
        if self._cerrado:
            return
        self._cerrado = True
        with self._bloqueo:
            self._parada.set()
            self._generacion += 1
            self._hablando = False
        try:
            self._reproductor.cortar()
        except Exception as exc:
            logger.debug("No se pudo cortar el reproductor local: %s", exc)
        try:
            self._reproductor.cerrar()
        except Exception as exc:
            logger.debug("No se pudo cerrar el reproductor local: %s", exc)
        try:
            self._sintetizador.cerrar()
        except Exception as exc:
            logger.warning("No se pudo cerrar el sintetizador local: %s", exc)
        hilo = self._hilo
        if (hilo is not None and hilo.is_alive()
                and hilo is not threading.current_thread()):
            hilo.join(timeout=1.0)

    def _sintetizar(self, texto, generacion, parada) -> None:
        _bajar_prioridad()
        com = _inicializar_com()
        try:
            propio, estiramiento = escala_voz.repartir_velocidad(
                escala_voz.factor_velocidad_local(self._velocidad),
                *self._sintetizador.rango_velocidad)
            tasa = int(self._sintetizador.tasa)
            estirador = ajustes_audio.Estirador(tasa, estiramiento)
            cambio = ajustes_audio.CambioTono(
                tasa, escala_voz.semitonos_local(self._tono))
            ganancia = (float(self._sintetizador.ganancia_voz)
                        * escala_voz.ganancia_local(self._volumen))
            self._reproductor.empezar(tasa)
            for trozo in self._sintetizador.sintetizar(texto, propio):
                if parada.is_set() or self._cerrado:
                    return
                self._enviar(trozo, estirador, cambio, ganancia, parada)
            if parada.is_set() or self._cerrado:
                return
            self._enviar_salida(cambio.procesar(estirador.vaciar()),
                                ganancia, parada)
            self._enviar_salida(cambio.vaciar(), ganancia, parada)
            self._reproductor.terminar()
        except Exception as exc:
            logger.warning("Fallo en la síntesis local: %s", exc)
            try:
                self._reproductor.terminar()
            except Exception as error:
                logger.debug("No se pudo terminar la frase local: %s", error)
        finally:
            self._esperar_fin(generacion, parada)
            if com:
                _cerrar_com()

    def _enviar(self, trozo, estirador, cambio, ganancia, parada) -> None:
        salida = cambio.procesar(estirador.procesar(trozo))
        self._enviar_salida(salida, ganancia, parada)

    def _enviar_salida(self, salida, ganancia, parada) -> None:
        if parada.is_set() or self._cerrado or not len(salida):
            return
        ajustada = ajustes_audio.limitar(
            ajustes_audio.aplicar_ganancia(salida, ganancia))
        if parada.is_set() or self._cerrado:
            return
        self._reproductor.encolar(ajustada)

    def _esperar_fin(self, generacion, parada) -> None:
        while not parada.is_set() and not self._cerrado:
            if not self._reproductor.sonando:
                break
            parada.wait(0.01)
        if not parada.is_set() and generacion == self._generacion:
            self._hablando = False
