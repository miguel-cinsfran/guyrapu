# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Hilo TTS con Prism (SAPI 5 u OneCore) y sanitización de texto.

Prism unifica los motores de voz de Windows bajo una API. El motor se crea,
se usa y se cierra DENTRO del hilo: Prism no es seguro entre hilos. Hablar es
asíncrono y `hablando()` dice si el motor sigue sonando; eso permite
interrumpir un mensaje en curso (Alt+D) sin cortar el siguiente por error.

La subida y la bajada del estado no son simétricas: en SAPI `hablando()` tarda
entre 14 y 18 ms en pasar a True tras `hablar`, y en OneCore la pausa lo deja
en False mientras está en pausa. Por eso se espera la subida y la pausa se
mira antes que el estado.
"""

from __future__ import annotations

import queue
import threading
import time

from guyrapu.core import diagnostico
from guyrapu.core.lectura_eventos import (
    construir_tts, quitar_emojis, sanitizar,  # noqa: F401
)
from guyrapu.voice import eleccion_motor
from guyrapu.voice import escala_voz
from guyrapu.voice import gestor_motores
from guyrapu.voice import motores

logger = diagnostico.obtener_logger(__name__)

_STOP = object()

# Máximo de espera a que `hablando()` pase a True, y ritmo con que se lo mira.
_ESPERA_SUBIDA = 1.0
_PASO_SUBIDA = 0.005
# Ritmo con que se mira la bajada mientras el motor suena.
_PASO_ESPERA = 0.05


def _entero(valor, defecto: int) -> int:
    try:
        return int(valor)
    except (TypeError, ValueError):
        return defecto


def _volumen_inicial(valor) -> int:
    try:
        return max(0, min(100, int(float(valor) * 100)))
    except (TypeError, ValueError):
        return 100


# ── Hilo TTS ─────────────────────────────────────────────────────────────────

class TTSWorker(threading.Thread):

    def __init__(self, cola: queue.Queue, config: dict, fabrica_motor=None):
        super().__init__(daemon=True, name="TTSWorker")
        self.cola   = cola
        self.config = config
        # Por defecto, la fábrica real (Prism o ElevenLabs según el motor).
        # Un doble permite probar el worker sin abrir un motor de verdad.
        self._fabrica_motor = fabrica_motor or motores.crear_motor
        # Aviso al usuario (lo conecta la GUI con `anunciar`). Con None solo
        # queda el registro en el log.
        self.al_avisar = None
        # Motor que está sonando ahora (principal o respaldo), para que la
        # pausa, la purga, la velocidad y el volumen lleguen al correcto.
        self._sonando = None
        self._ready  = threading.Event()
        self._error  = None
        self._active = threading.Event()
        self._active.set()
        self._paused = False
        self._cmds   = queue.Queue()
        # El contador de velocidad es el porcentaje propio (0..100, pasos de 5).
        self._rate   = escala_voz.ajustar_velocidad(
            _entero(config.get("velocidad_voz"), escala_voz.VELOCIDAD_NORMAL), 0)
        self._volume = _volumen_inicial(config.get("volumen", 1.0))
        self._tono   = max(0, min(100, _entero(config.get("tono"), 50)))
        self._purge_pending = threading.Event()
        # Autor del último mensaje que la voz empezó a leer, para anunciarlo
        # con F3 sin volver a la lista. Se registra en run() justo antes de
        # hablar; asignar una cadena es atómico en CPython y no lleva lock.
        self._ultimo_autor = ""
        # Motor principal, voces y voz activa. Todo se crea y se usa en el hilo
        # del worker; la interfaz lee `voces()` solo después de `esperar_inicio`.
        self._gestor = gestor_motores.GestorMotores(self._fabrica_motor)
        self._eleccion = eleccion_motor.EleccionMotor(
            config, self._fabrica_motor, self._gestor, self._avisar,
            self._leer_frase, self._ajustes)

    def run(self):
        try:
            self._abrir_motor()
        except Exception as exc:
            self._error = exc
            self._ready.set()
            logger.error("TTSWorker: %s", exc)
            self._cerrar_motor()
            return
        self._ready.set()
        logger.info("TTSWorker listo (motor %s).", self.motor_activo())
        _err = 0
        try:
            while True:
                self._active.wait()
                self._procesar_comandos()
                try:
                    item = self.cola.get(timeout=0.3)
                except queue.Empty:
                    continue
                if item is _STOP:
                    break
                texto = (item.get("texto_tts") or "").strip()
                if not texto:
                    continue
                self._active.wait()
                try:
                    # El autor viaja en el item y se guarda al empezar a leerlo,
                    # no al encolar: entre medias hay cola y descartes. Un item
                    # sin autor (avisos internos) no borra el anterior.
                    autor = item.get("autor") or ""
                    if autor:
                        self._ultimo_autor = autor
                    self._hablar(texto, item.get("voz"),
                                 item.get("importante", False), item.get("secundaria"))
                    _err = 0
                except Exception as exc:
                    _err += 1
                    if _err <= 5:
                        logger.warning("TTS error: %s", exc)
                    elif _err == 6:
                        logger.error("TTS: demasiados errores seguidos.")
        finally:
            self._cerrar_motor()
        logger.info("TTSWorker terminado.")

    # ── Arranque y cierre del motor ──────────────────────────────────────────

    def _abrir_motor(self) -> None:
        self._gestor.abrir(
            self.config.get("motor") or "sapi", self.config.get("voz"),
            self._rate, self._volume, self._tono)

    def _cerrar_motor(self) -> None:
        self._gestor.cerrar()
        self._eleccion.cerrar()

    def _ajustes(self):
        """Velocidad, volumen y tono base del worker."""
        return self._rate, self._volume, self._tono

    # ── Voz y habla ──────────────────────────────────────────────────────────

    def _hablar(self, texto: str, voz=None, importante=False, secundaria=False) -> None:
        # Una purga pedida con la voz callada (p. ej. detener_actual() al
        # reconectar) quedaba armada y cortaba el SIGUIENTE mensaje: el primer
        # mensaje de cada reconexión se oía a medias. No había nada que cortar,
        # así que se descarta antes de hablar.
        self._purge_pending.clear()
        self._eleccion.hablar(texto, voz, importante, secundaria)

    def _leer_frase(self, motor, texto: str) -> bool:
        """Manda la frase a `motor` y espera a que termine. True si sonó."""
        self._sonando = motor
        try:
            if not motor.hablar(texto):
                return False
            # La subida del estado es asíncrona: hay que verla pasar a True o
            # el bucle de abajo daría el mensaje por terminado antes de sonar.
            limite = time.monotonic() + _ESPERA_SUBIDA
            while not motor.hablando() and time.monotonic() < limite:
                self._procesar_comandos()
                if self._purge_pending.is_set():
                    self._purge_pending.clear()
                    motor.parar()
                    return True
                time.sleep(_PASO_SUBIDA)
            # Bajada: mientras suene, se atienden comandos y purgas. La pausa
            # se mira ANTES que `hablando()`: en OneCore la pausa deja el
            # estado en False y mirarlo primero arrancaría el siguiente en pausa.
            while True:
                self._procesar_comandos()
                if not self._active.is_set():
                    self._esperar_pausa()
                if self._purge_pending.is_set():
                    self._purge_pending.clear()
                    motor.parar()
                    return True
                if not motor.hablando():
                    return True
                time.sleep(_PASO_ESPERA)
        finally:
            self._sonando = None

    def _avisar(self, mensaje: str) -> None:
        """Avisa al usuario (o solo al log) una vez por racha."""
        logger.warning("TTS: %s", mensaje)
        llamar = self.al_avisar
        if llamar is None:
            return
        try:
            llamar(mensaje)
        except Exception as exc:
            logger.debug("El aviso al usuario falló: %s", exc)

    def _esperar_pausa(self) -> None:
        """Pausa a mitad de frase sin dejar de atender comandos ni purgas.

        Antes el hilo quedaba en wait() pero la voz seguía sonando hasta acabar
        la frase; ahora se pausa el motor de verdad y los comandos (voz,
        velocidad, volumen, purga) se siguen atendiendo."""
        motor = self._motor_de_comandos()
        motor.pausar()
        try:
            while not self._active.wait(0.1):
                self._procesar_comandos()
                if self._purge_pending.is_set():
                    break   # Alt+D en pausa: se reanuda para poder purgar
        finally:
            motor.reanudar()

    def _motor_de_comandos(self):
        """Motor que recibe los ajustes: el que suena, o el principal si no hay."""
        return self._sonando or self._gestor.motor

    def _procesar_comandos(self):
        while not self._cmds.empty():
            try:    cmd, val = self._cmds.get_nowait()
            except queue.Empty: break
            try:
                if cmd == "voice":
                    self._gestor.cambiar_voz_base(val)
                elif cmd == "motor":
                    self._gestor.cambiar(val[0], val[1], self._rate,
                                         self._volume, self._tono)
                elif cmd == "elevenlabs":
                    self._eleccion.configurar_elevenlabs(*val)
                elif cmd == "voz_secundaria":
                    self._eleccion.configurar_voz_secundaria(*val)
                elif cmd == "rate":
                    if not self._eleccion.sonando_secundaria:
                        self._motor_de_comandos().fijar_velocidad(val)
                elif cmd == "volume":
                    if not self._eleccion.sonando_secundaria:
                        self._motor_de_comandos().fijar_volumen(val)
                elif cmd == "tono":
                    self._motor_de_comandos().fijar_tono(val)
                elif cmd == "purge":
                    self._purge_pending.set()
            except Exception as exc:
                logger.warning("Comando %s: %s", cmd, exc)

    # ── API pública ──────────────────────────────────────────────────────────

    def esperar_inicio(self, timeout=10.0):
        if not self._ready.wait(timeout=timeout): return False
        if self._error:
            logger.error(str(self._error)); return False
        return True

    def voces(self) -> list[str]:
        """Nombres de voz del motor activo. Válida tras `esperar_inicio`."""
        return self._gestor.voces

    def motor_activo(self) -> str:
        """Motor que quedó activo de verdad: 'sapi' u 'onecore'."""
        return self._gestor.motor.motor if self._gestor.motor is not None else ""

    def pausar(self):
        if not self._paused:
            self._paused = True; self._active.clear()

    def reanudar(self):
        if self._paused:
            self._paused = False; self._active.set()

    def toggle_pausa(self):
        self.reanudar() if self._paused else self.pausar()

    def esta_pausado(self):
        return self._paused

    def vaciar_cola(self):
        n = 0
        while not self.cola.empty():
            try:    self.cola.get_nowait(); n += 1
            except queue.Empty: break
        if n: logger.info("Cola vaciada: %d mensaje(s).", n)

    def detener(self):
        if self._paused: self._active.set()
        try:    self.cola.put(_STOP)
        except Exception as error: logger.debug("no se pudo pedir la detención: %s", error)
        self.join(timeout=5.0)

    def detener_actual(self):
        """Interrumpe el mensaje en curso y vacía la cola (Alt+D)."""
        self.vaciar_cola()
        self._cmds.put(("purge", None))

    def cambiar_voz(self, idx: int):
        self._cmds.put(("voice", idx))

    def cambiar_motor(self, motor: str, voz) -> None:
        """Pide cambiar de motor en caliente (SAPI u OneCore).

        El trabajo real ocurre en el hilo del worker: Prism no admite que un
        motor se cree en un hilo y se use en otro."""
        self._cmds.put(("motor", (motor, voz)))

    def configurar_elevenlabs(self, tope, solo_importantes, voz_respaldo) -> None:
        """Pide aplicar en caliente el tope, el «solo lo importante» y la voz
        de respaldo de ElevenLabs.

        El trabajo real ocurre en el hilo del worker, dueño del respaldo y de
        sus ajustes; llamarlo desde la interfaz no toca la red ni el motor."""
        self._cmds.put(("elevenlabs", (tope, solo_importantes, voz_respaldo)))

    def configurar_voz_secundaria(self, voz, velocidad, volumen, respaldo,
                                  motor=None) -> None:
        """Pide aplicar en caliente la voz secundaria, su respaldo y su motor."""
        self._cmds.put(("voz_secundaria",
                        (voz, velocidad, volumen, respaldo, motor)))

    def cambiar_rate(self, pasos: int) -> None:
        # El contador se actualiza AQUÍ (en el hilo del llamador) y al hilo TTS
        # va el valor absoluto: así get_rate() devuelve el valor nuevo al
        # instante y pulsar rápido no desfasa lo anunciado/persistido.
        self._rate = escala_voz.ajustar_velocidad(self._rate, pasos)
        self._cmds.put(("rate", self._rate))

    def cambiar_volumen(self, delta: int) -> None:
        self._volume = max(0, min(100, self._volume + int(delta)))
        self._cmds.put(("volume", self._volume))

    def cambiar_tono(self, pct: int) -> None:
        self._tono = max(0, min(100, _entero(pct, self._tono)))
        self._cmds.put(("tono", self._tono))

    def fijar_rate(self, pct: int) -> None:
        """Fija la velocidad en un valor absoluto (0..100, múltiplo de 5)."""
        self._rate = escala_voz.ajustar_velocidad(_entero(pct, self._rate), 0)
        self._cmds.put(("rate", self._rate))

    def fijar_volumen_pct(self, pct: int) -> None:
        """Fija el volumen en un porcentaje absoluto (0..100)."""
        self._volume = max(0, min(100, _entero(pct, self._volume)))
        self._cmds.put(("volume", self._volume))

    def get_rate(self) -> int:
        return self._rate

    def get_volume(self) -> int:
        return self._volume

    def get_tono(self) -> int:
        return self._tono

    def ultimo_autor(self) -> str:
        """Autor del último mensaje que la voz empezó a leer.

        Cadena vacía si todavía no se leyó nada."""
        return self._ultimo_autor
