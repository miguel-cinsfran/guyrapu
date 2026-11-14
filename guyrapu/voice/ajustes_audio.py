# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Ajustes de audio puros para los motores de voz locales.

Ganancia y limitador se aplican muestra por muestra. La velocidad se cambia
con WSOLA, que mantiene el tono, y el tono con un estiramiento seguido de un
remuestreo. Estirador y CambioTono guardan estado entre trozos: procesar cada
trozo por separado dejaría un clic en cada unión.
"""

from __future__ import annotations

import numpy as np

PICO_LIMITE = 0.98
_VENTANA_S = 0.03
_BUSQUEDA_S = 0.01


def aplicar_ganancia(trozo, ganancia: float) -> np.ndarray:
    """Escala el trozo completo por la ganancia pedida."""
    return np.asarray(trozo, dtype=np.float32) * float(ganancia)


def limitar(trozo) -> np.ndarray:
    """Baja el pico a 0.98 escalando el trozo entero, sin recortar muestras."""
    datos = np.asarray(trozo, dtype=np.float32)
    pico = float(np.max(np.abs(datos))) if len(datos) else 0.0
    if pico <= PICO_LIMITE:
        return datos
    return datos * (PICO_LIMITE / pico)


class Estirador:
    """Cambia la velocidad sin cambiar el tono con WSOLA y estado entre trozos.

    El factor es la velocidad: 2.0 dura la mitad y 1.0 devuelve las mismas
    muestras sin pasar por el algoritmo.
    """

    def __init__(self, tasa: int, factor: float):
        self._factor = float(factor)
        self._n = max(1, int(round(tasa * _VENTANA_S)))
        self._salto = max(1, self._n // 2)
        self._busqueda = max(1, int(round(tasa * _BUSQUEDA_S)))
        self._ventana = (0.5 - 0.5 * np.cos(
            2 * np.pi * np.arange(self._n) / self._n)).astype(np.float32)
        self._ha = self._factor * self._salto
        self._entrada = np.empty(0, np.float32)
        self._base = 0
        self._k = 0
        self._prev = None
        self._salida = np.empty(0, np.float32)
        self._inicio_salida = 0
        self._terminado = False

    @property
    def _fin_entrada(self) -> int:
        return self._base + len(self._entrada)

    def procesar(self, trozo) -> np.ndarray:
        """Devuelve el audio que ya puede salir y retiene el resto."""
        if self._terminado:
            return np.empty(0, np.float32)
        datos = np.asarray(trozo, dtype=np.float32).reshape(-1)
        if self._factor == 1.0:
            return datos.copy()
        self._entrada = np.concatenate([self._entrada, datos])
        return self._producir(False)

    def vaciar(self) -> np.ndarray:
        """Devuelve lo que queda al final de la frase."""
        if self._terminado:
            return np.empty(0, np.float32)
        self._terminado = True
        if self._factor == 1.0:
            return np.empty(0, np.float32)
        return self._producir(True)

    def _producir(self, flush: bool) -> np.ndarray:
        emitidos = []
        while True:
            nominal = int(round(self._k * self._ha))
            if flush:
                if nominal >= self._fin_entrada:
                    break
            elif nominal + self._n > self._fin_entrada:
                break
            self._agregar_frame(nominal, flush)
            self._k += 1
            if not flush:
                limite = self._k * self._salto
                if limite > self._inicio_salida:
                    emitidos.append(self._tomar_hasta(limite))
            self._recortar()
        if flush:
            objetivo = int(round(self._fin_entrada / self._factor))
            if objetivo > self._inicio_salida:
                emitidos.append(self._tomar_hasta(objetivo))
        if emitidos:
            return np.concatenate(emitidos)
        return np.empty(0, np.float32)

    def _agregar_frame(self, nominal: int, flush: bool) -> None:
        n, salto = self._n, self._salto
        if self._prev is None:
            inicio = 0
        else:
            objetivo = self._prev[salto:]
            desde = max(self._base, nominal - self._busqueda)
            hasta = min(nominal + self._busqueda, self._fin_entrada - n)
            inicio = nominal
            mejor = -np.inf
            norma_objetivo = float(np.linalg.norm(objetivo))
            for candidato in range(desde, hasta + 1):
                segmento = self._leer(candidato, False)[:salto]
                norma = float(np.linalg.norm(segmento)) * norma_objetivo
                puntaje = (float(np.dot(segmento, objetivo)) / norma
                           if norma else 0.0)
                if puntaje > mejor:
                    mejor = puntaje
                    inicio = candidato
        frame = self._leer(inicio, flush)
        self._prev = frame.copy()
        posicion = self._k * salto
        self._asegurar(posicion + n)
        relativa = posicion - self._inicio_salida
        self._salida[relativa:relativa + n] += frame * self._ventana

    def _leer(self, inicio: int, rellenar: bool):
        desde = inicio - self._base
        if desde >= 0 and desde + self._n <= len(self._entrada):
            return self._entrada[desde:desde + self._n].copy()
        if not rellenar:
            return None
        salida = np.zeros(self._n, np.float32)
        if desde < 0:
            return salida
        fin = min(self._n, len(self._entrada) - desde)
        if fin > 0:
            salida[:fin] = self._entrada[desde:desde + fin]
        return salida

    def _asegurar(self, final: int) -> None:
        relativa = final - self._inicio_salida
        if relativa > len(self._salida):
            faltan = relativa - len(self._salida)
            self._salida = np.concatenate(
                [self._salida, np.zeros(faltan, np.float32)])

    def _tomar_hasta(self, limite: int) -> np.ndarray:
        relativa = limite - self._inicio_salida
        if relativa <= 0:
            return np.empty(0, np.float32)
        parte = self._salida[:relativa].copy()
        self._salida = self._salida[relativa:]
        self._inicio_salida = limite
        return parte

    def _recortar(self) -> None:
        proximo = int(round(self._k * self._ha)) - self._busqueda
        corte = min(len(self._entrada), max(0, proximo - self._base))
        if corte > 0:
            self._entrada = self._entrada[corte:]
            self._base += corte


class CambioTono:
    """Cambia el tono sin cambiar la duración, con estado entre trozos.

    Estira el audio por el factor de los semitonos y lo vuelve a la tasa
    original remuestreando. Con 0 semitonos devuelve las mismas muestras.
    """

    def __init__(self, tasa: int, semitonos: float):
        self._ratio = float(2 ** (float(semitonos) / 12))
        self._estirador = Estirador(tasa, 1.0 / self._ratio)
        self._buffer = np.empty(0, np.float32)
        self._pos = 0.0
        self._terminado = False

    def procesar(self, trozo) -> np.ndarray:
        """Devuelve el audio ajustado que ya puede salir."""
        if self._terminado:
            return np.empty(0, np.float32)
        datos = np.asarray(trozo, dtype=np.float32).reshape(-1)
        if self._ratio == 1.0:
            return datos.copy()
        return self._resamplear(self._estirador.procesar(datos))

    def vaciar(self) -> np.ndarray:
        """Devuelve lo que queda al final de la frase."""
        if self._terminado:
            return np.empty(0, np.float32)
        self._terminado = True
        if self._ratio == 1.0:
            return np.empty(0, np.float32)
        return self._resamplear(self._estirador.vaciar())

    def _resamplear(self, datos) -> np.ndarray:
        if len(datos):
            self._buffer = np.concatenate([self._buffer, datos])
        salida = []
        posicion = self._pos
        while int(np.floor(posicion)) + 1 < len(self._buffer):
            indice = int(np.floor(posicion))
            resto = posicion - indice
            salida.append(self._buffer[indice] * (1.0 - resto)
                          + self._buffer[indice + 1] * resto)
            posicion += self._ratio
        corte = int(np.floor(posicion))
        if corte:
            self._buffer = self._buffer[corte:]
        self._pos = posicion - corte
        if salida:
            return np.asarray(salida, np.float32)
        return np.empty(0, np.float32)
