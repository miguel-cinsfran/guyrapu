# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Vigilancia en segundo plano del estado de OBS."""

from __future__ import annotations

from dataclasses import dataclass
import logging
import threading
import time

from guyrapu.core import diagnostico, esperas, vigilancia
from guyrapu.core.idioma import N_, _
from guyrapu.core.tiempo import TiempoDeFunciones
from guyrapu.obs import obs_activacion
from guyrapu.obs.obs_panel import GestorPanelObs

PLAZO_FRESCURA = 12.0
INTERVALO_SONDEO = 5.0
INTERVALO_SIN_OBS = 15.0

MENSAJE_SIN_RESPUESTA = N_("OBS no responde. Se sigue intentando.")
MENSAJE_RESPONDE = N_("OBS volvió a responder.")


@dataclass(frozen=True)
class EstadoObs:
    transmision: dict | None = None
    grabacion: dict | None = None
    escena: str = ""


class _CadenciaDeSondeo:
    """Espera según cómo salió la última lectura de OBS."""

    def __init__(self):
        self.buena = True

    def espera(self, intento, transcurrido):
        return INTERVALO_SONDEO if self.buena else INTERVALO_SIN_OBS


class VigilanteObs:
    """Conserva una conexión a OBS y una copia segura para el hilo de GUI."""

    def __init__(self, crear_gestor=GestorPanelObs, reloj=time.monotonic,
                 en_ejecucion=obs_activacion.obs_esta_en_ejecucion,
                 al_anunciar=None):
        self._crear_gestor = crear_gestor
        self._reloj = reloj
        self._en_ejecucion = en_ejecucion
        self._al_anunciar = al_anunciar or (lambda frase, sonido: None)
        self._parada = threading.Event()
        self._cerrojo = threading.Lock()
        self._estado = EstadoObs()
        self._ultimo_sondeo = None
        self._hilo = None
        self._gestor = None

    def iniciar(self):
        if self._hilo is not None and self._hilo.is_alive():
            return
        self._parada.clear()
        self._hilo = diagnostico.crear_hilo(self._vigilar, "VigilanteObs")
        self._hilo.start()

    def detener(self):
        self._parada.set()
        hilo = self._hilo
        if hilo is not None:
            hilo.join(1.0)

    def estado(self, ahora=None) -> EstadoObs | None:
        if ahora is None:
            ahora = self._reloj()
        with self._cerrojo:
            if not dato_fresco(self._ultimo_sondeo, ahora):
                return None
            return self._estado

    def _vigilar(self):
        logger = diagnostico.obtener_logger(__name__)
        gestor = self._crear_gestor()
        self._gestor = gestor
        vigia = self._vigilancia(logger)
        cadencia = _CadenciaDeSondeo()
        try:
            esperas.esperar(
                lambda: self._ronda(logger, gestor, vigia, cadencia),
                lambda valor: False, cadencia=cadencia, parada=self._parada,
                tiempo=TiempoDeFunciones(self._reloj, self._parada.wait))
        finally:
            try:
                gestor.cerrar()
            except Exception as error:
                logger.debug("no se pudo cerrar el gestor de OBS: %s", error)
            self._gestor = None

    def _ronda(self, logger, gestor, vigia, cadencia):
        try:
            if not gestor.conectado:
                gestor.conectar(self._parada)
            estado = EstadoObs(gestor.estado_transmision(self._parada),
                               gestor.estado_grabacion(self._parada),
                               gestor.escena_al_aire(self._parada))
            with self._cerrojo:
                self._estado = estado
                self._ultimo_sondeo = self._reloj()
            vigia.leida(True)
            cadencia.buena = True
        except Exception:
            if self._parada.is_set():
                # Al cerrar la app la petición en vuelo se cancela; ese
                # aviso se anuncia en voz alta y OBS no tiene la culpa.
                cadencia.buena = False
                return
            self._fallo_visto(logger, gestor, vigia)
            cadencia.buena = False

    def _fallo_visto(self, logger, gestor, vigia):
        """Registra un sondeo fallido y cierra el gestor."""
        if self._sigue_en_ejecucion(logger):
            vigia.leida(False)
        else:
            logger.debug("OBS no está en ejecución; se reintentará")
        try:
            gestor.cerrar()
        except Exception as error:
            logger.debug("no se pudo cerrar el gestor de OBS: %s", error)

    def _sigue_en_ejecucion(self, logger):
        try:
            return bool(self._en_ejecucion())
        except Exception as error:
            # Un fallo al comprobar la ejecución no puede callar una falla
            # real de OBS.
            logger.debug("no se pudo comprobar si OBS está en ejecución: %s",
                         error)
            return True

    def _vigilancia(self, logger):
        return vigilancia.Vigilancia(
            lambda frase, sonido: self._anuncio_de_vigilancia(
                logger, frase, sonido),
            caida=vigilancia.Aviso(_(MENSAJE_SIN_RESPUESTA),
                                   "obs_sin_respuesta"),
            vuelta=vigilancia.Aviso(_(MENSAJE_RESPONDE), "obs_responde"),
            rendicion=vigilancia.Aviso(_(MENSAJE_SIN_RESPUESTA),
                                      "obs_sin_respuesta"),
            tiempo=TiempoDeFunciones(self._reloj, lambda segundos: None))

    def _anuncio_de_vigilancia(self, logger, frase, sonido):
        if sonido == "obs_sin_respuesta":
            logger.warning("OBS no responde; se reintentará")
        elif sonido == "obs_responde":
            logger.info("OBS volvió a responder")
        self._avisar(logger, frase, sonido)

    def _avisar(self, logger, frase, sonido):
        try:
            self._al_anunciar(frase, sonido)
        except Exception as error:
            logger.debug("no se pudo anunciar el estado de OBS: %s", error)


def dato_fresco(ultimo_sondeo: float | None, ahora: float) -> bool:
    """Indica si un sondeo de OBS todavía puede anunciarse."""
    return ultimo_sondeo is not None and ahora - ultimo_sondeo <= PLAZO_FRESCURA
