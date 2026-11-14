# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Proveedores de los motores de voz de Windows, con Prism.

Prism unifica SAPI 5 y OneCore bajo una misma API. Este módulo aísla a la
aplicación de esa API: crea el motor pedido, traduce los porcentajes de la
app con `escala_voz` y no deja salir ningún error después del constructor.
Cambiar de motor o elegir mal una voz no debe tumbar el hilo de voz.

Importar este módulo no importa Prism: la biblioteca se carga al crear un
motor, para que quien no la use no la pague.
"""

from __future__ import annotations

from guyrapu.core import diagnostico
from guyrapu.core.idioma import N_, _
from guyrapu.voice import escala_voz
from guyrapu.voice.proveedores.base import (
    Capacidades,
    MotorNoDisponible,
    Proveedor,
)

logger = diagnostico.obtener_logger(__name__)

# Solo los motores de Prism tienen backend id. ElevenLabs tiene su propio
# MotorElevenLabs, así que la validación de `MotorPrism` va contra `_IDS` y no
# contra el registro: pedir «elevenlabs» desde Prism debe dar
# MotorNoDisponible.
_IDS = {"sapi": "SAPI", "onecore": "ONE_CORE"}

_NOMBRES = {
    "sapi": N_("Windows SAPI 5"),
    "onecore": N_("Windows OneCore"),
}

_LICENCIA = N_("Voz de Windows")

_MSG_DESCONOCIDO = N_("Motor de voz desconocido: {motor} (válidos: {validos})")
_MSG_SIN_PRISM = N_("No se pudo importar Prism para el motor {nombre}: {detalle}")
_MSG_SIN_MOTOR = N_("No se pudo iniciar el motor {nombre}: {detalle}")


class MotorPrism:
    """Un motor de Prism con la interfaz que usa la aplicación.

    NO es seguro entre hilos: la regla de Prism es que un backend lo crea y lo
    usa un solo hilo. La interfaz debe crear su propia instancia (por ejemplo
    con `listar_voces`) para no tocar la del hilo de voz.
    """

    def __init__(self, motor, fabrica_contexto=None):
        if motor not in _IDS:
            raise MotorNoDisponible(_(_MSG_DESCONOCIDO).format(
                motor=repr(motor), validos=", ".join(_IDS)))
        try:
            from prism import BackendId
            from prism.common import (
                PrismAlreadyPausedError,
                PrismNotPausedError,
            )
            # Importación perezosa: Prism puede no estar instalado y eso debe
            # llegar como MotorNoDisponible, no como ImportError al importar
            # este módulo.
            if fabrica_contexto is None:
                from prism import Context as fabrica_contexto
        except Exception as exc:
            raise MotorNoDisponible(_(_MSG_SIN_PRISM).format(
                nombre=_(_NOMBRES[motor]), detalle=exc)) from exc
        try:
            self._ctx = fabrica_contexto()
            self._backend = self._ctx.create(getattr(BackendId, _IDS[motor]))
        except Exception as exc:
            raise MotorNoDisponible(_(_MSG_SIN_MOTOR).format(
                nombre=_(_NOMBRES[motor]), detalle=exc)) from exc
        self._ya_pausado = PrismAlreadyPausedError
        self._no_pausado = PrismNotPausedError
        self.motor = motor
        self._cerrado = False

    def _vivo(self) -> bool:
        return not self._cerrado and getattr(self, "_backend", None) is not None

    def voces(self) -> list[str]:
        """Refresca y devuelve los nombres de las voces del motor."""
        if not self._vivo():
            return []
        try:
            self._backend.refresh_voices()
            return [self._backend.get_voice_name(i)
                    for i in range(self._backend.voices_count)]
        except Exception as exc:
            logger.warning("Listar voces de %s: %s", self.motor, exc)
            return []

    def elegir_voz(self, idx) -> bool:
        """Cambia la voz activa. False si el índice está fuera de rango o falla."""
        if not self._vivo():
            return False
        try:
            idx = int(idx)
            if not 0 <= idx < self._backend.voices_count:
                return False
            self._backend.voice = idx
            return True
        except Exception as exc:
            logger.warning("Elegir voz %s en %s: %s", idx, self.motor, exc)
            return False

    def hablar(self, texto) -> bool:
        """Lanza la frase sin interrumpir lo que suene. False si no habló."""
        if not self._vivo():
            return False
        limpio = (texto or "").replace("\x00", "")
        if not limpio:
            return False
        try:
            self._backend.speak(limpio, interrupt=False)
            return True
        except Exception as exc:
            logger.warning("Hablar en %s: %s", self.motor, exc)
            return False

    def hablando(self) -> bool:
        if not self._vivo():
            return False
        try:
            return bool(self._backend.speaking)
        except Exception as exc:
            logger.warning("Consultar estado en %s: %s", self.motor, exc)
            return False

    def parar(self):
        if not self._vivo():
            return
        try:
            self._backend.stop()
        except Exception as exc:
            logger.warning("Parar en %s: %s", self.motor, exc)

    def pausar(self):
        if not self._vivo():
            return
        try:
            self._backend.pause()
        except self._ya_pausado:
            pass
        except Exception as exc:
            logger.warning("Pausar en %s: %s", self.motor, exc)

    def reanudar(self):
        if not self._vivo():
            return
        try:
            self._backend.resume()
        except self._no_pausado:
            pass
        except Exception as exc:
            logger.warning("Reanudar en %s: %s", self.motor, exc)

    def fijar_velocidad(self, pct):
        if not self._vivo():
            return
        try:
            self._backend.rate = escala_voz.velocidad_a_prism(self.motor, pct)
        except Exception as exc:
            logger.warning("Velocidad en %s: %s", self.motor, exc)

    def fijar_volumen(self, pct):
        if not self._vivo():
            return
        try:
            self._backend.volume = escala_voz.porcentaje_a_prism(pct)
        except Exception as exc:
            logger.warning("Volumen en %s: %s", self.motor, exc)

    def fijar_tono(self, pct):
        if not self._vivo():
            return
        try:
            self._backend.pitch = escala_voz.porcentaje_a_prism(pct)
        except Exception as exc:
            logger.warning("Tono en %s: %s", self.motor, exc)

    def cerrar(self):
        """Para el motor y suelta el backend y el contexto.

        Después de cerrar, todo método es no-op y `hablando()` devuelve False.
        """
        if getattr(self, "_cerrado", True):
            return
        try:
            if self._backend is not None:
                self._backend.stop()
        except Exception as exc:
            logger.debug("Parar al cerrar %s: %s", self.motor, exc)
        self._backend = None
        self._ctx = None
        self._cerrado = True


def crear_sapi(clave_elevenlabs=None):
    return MotorPrism("sapi")


def crear_onecore(clave_elevenlabs=None):
    return MotorPrism("onecore")


def _listar_voces(motor, fabrica_contexto) -> list[str]:
    try:
        instancia = MotorPrism(motor, fabrica_contexto)
    except MotorNoDisponible:
        return []
    try:
        return instancia.voces()
    finally:
        instancia.cerrar()


def listar_voces_sapi(fabrica_contexto=None) -> list[str]:
    return _listar_voces("sapi", fabrica_contexto)


def listar_voces_onecore(fabrica_contexto=None) -> list[str]:
    return _listar_voces("onecore", fabrica_contexto)


_CAPACIDADES = Capacidades(streaming=False, tono=True, nube=False)

PROVEEDOR_SAPI = Proveedor(
    id="sapi",
    nombre=_NOMBRES["sapi"],
    licencia=_LICENCIA,
    capacidades=_CAPACIDADES,
    crear=crear_sapi,
    listar_voces=listar_voces_sapi,
)

PROVEEDOR_ONECORE = Proveedor(
    id="onecore",
    nombre=_NOMBRES["onecore"],
    licencia=_LICENCIA,
    capacidades=_CAPACIDADES,
    crear=crear_onecore,
    listar_voces=listar_voces_onecore,
)
