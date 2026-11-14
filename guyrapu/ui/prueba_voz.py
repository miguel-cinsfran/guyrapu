# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Prueba de voz de la página Voces.

Hace sonar una voz de prueba y cierra su motor. No conoce la página ni el
diálogo: recibe los valores ya leídos de los controles.
"""

from __future__ import annotations

import threading
import time

import wx

from guyrapu.core import diagnostico
from guyrapu.core.idioma import _
from guyrapu.ui.accesibilidad import anunciar

logger = diagnostico.obtener_logger(__name__)

VIDA_PRUEBA_VOZ = 30.0


class PruebaVoz:
    """Motor de la prueba de voz, compartido por los motores locales y
    ElevenLabs."""

    def __init__(self):
        self._probando_eleven = False
        self._corte_motor = None

    def probar_motor(self, motor, indice_voz, velocidad, volumen, tono):
        self._cortar_prueba_motor()
        corte = threading.Event()
        self._corte_motor = corte
        diagnostico.crear_hilo(
            lambda: self._sonar_prueba_motor(
                motor, indice_voz, velocidad, volumen, tono, corte),
            "ProbarVoz").start()

    def _sonar_prueba_motor(self, motor, indice_voz, velocidad, volumen, tono,
                            corte) -> None:
        # El motor de la prueba se crea, usa y cierra dentro de su hilo.
        from guyrapu.voice import motores

        prueba = None
        try:
            prueba = motores.crear_motor(motor)
        except motores.MotorNoDisponible:
            self._soltar_prueba_motor(corte)
            wx.CallAfter(anunciar, _("No se pudo iniciar el motor de voz elegido."))
            return
        try:
            prueba.elegir_voz(indice_voz)
            prueba.fijar_velocidad(velocidad)
            prueba.fijar_volumen(volumen)
            prueba.fijar_tono(tono)
            prueba.hablar(_("Así suena esta voz."))
            corte.wait(VIDA_PRUEBA_VOZ)
        except Exception as exc:
            logger.warning("Prueba de voz: %s", exc)
        finally:
            self._cerrar_prueba_motor(prueba, corte)

    def _cerrar_prueba_motor(self, prueba, corte) -> None:
        try:
            prueba.cerrar()
        except Exception as exc:
            logger.debug("Cerrar motor de prueba: %s", exc)
        self._soltar_prueba_motor(corte)

    def _soltar_prueba_motor(self, corte) -> None:
        if self._corte_motor is corte:
            self._corte_motor = None

    def _cortar_prueba_motor(self) -> None:
        if self._corte_motor is not None:
            self._corte_motor.set()

    def probar_elevenlabs(self, clave, voz, velocidad, volumen):
        if self._probando_eleven:
            return
        self._probando_eleven = True
        diagnostico.crear_hilo(
            lambda: self._sonar_prueba_elevenlabs(clave, voz, velocidad, volumen),
            "ProbarVozEleven").start()

    def _sonar_prueba_elevenlabs(self, clave, voz, velocidad, volumen) -> None:
        # El motor de la prueba se crea, usa y cierra dentro de su hilo.
        from guyrapu.voice import escala_voz
        from guyrapu.voice import motor_elevenlabs

        prueba = None
        try:
            prueba = motor_elevenlabs.MotorElevenLabs(clave)
            idx = escala_voz.resolver_voz(voz, prueba.voces())
            prueba.elegir_voz(0 if idx is None else idx)
            prueba.fijar_velocidad(velocidad)
            prueba.fijar_volumen(volumen)
            prueba.hablar(_("Así suena esta voz."))
            while prueba.hablando():
                time.sleep(0.05)
        except Exception as exc:
            wx.CallAfter(anunciar, str(exc))
        finally:
            if prueba is not None:
                try:
                    prueba.cerrar()
                except Exception as exc:
                    logger.debug("Cerrar la prueba de ElevenLabs: %s", exc)
            wx.CallAfter(self._fin_prueba_elevenlabs)

    def _fin_prueba_elevenlabs(self) -> None:
        self._probando_eleven = False

    def cerrar(self) -> None:
        self._cortar_prueba_motor()
