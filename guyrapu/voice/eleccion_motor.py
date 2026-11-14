# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Qué motor y qué voz leen cada mensaje, y a dónde cae si fallan.

`EleccionMotor` es dueña del respaldo de Windows, de la voz secundaria y de la
caída de ElevenLabs. El worker le pasa el gestor del motor principal, la
función con la que avisa al usuario, la que lee una frase (vive en el worker
porque depende de su pausa y su purga) y la que devuelve los ajustes base.
"""

from __future__ import annotations

from guyrapu.core.idioma import _
from guyrapu.core.ini_tipado import a_entero
from guyrapu.voice import caida_elevenlabs
from guyrapu.voice import caida_motor
from guyrapu.voice import elevenlabs
from guyrapu.voice import motores
from guyrapu.voice import respaldo_windows
from guyrapu.voice import voz_secundaria


class EleccionMotor:
    """Decide el motor y la voz de un mensaje y su respaldo."""

    def __init__(self, config, fabrica_motor, gestor, avisar, leer_frase,
                 ajustes):
        self._gestor = gestor
        self._avisar = avisar
        self._leer_frase = leer_frase
        self._ajustes = ajustes
        # Respaldo de Windows: el objeto guarda su voz y sus ajustes; el motor
        # se crea perezoso, en el hilo del worker.
        self.respaldo = respaldo_windows.Respaldo(
            fabrica_motor, config.get("voz_respaldo") or "")
        self.voz_secundaria = voz_secundaria.VozSecundaria(
            fabrica_motor, config, config.get("tono"))
        self.caida = caida_elevenlabs.CaidaElevenLabs(
            a_entero(config.get("elevenlabs_tope"), 0),
            config.get("elevenlabs_solo_importantes"))
        self._caida_motor = caida_motor.CaidaMotor()
        self._caida_secundaria = caida_motor.CaidaMotor()

    @property
    def sonando_secundaria(self) -> bool:
        return self.voz_secundaria.sonando

    def hablar(self, texto: str, voz=None, importante=False,
               secundaria=False) -> None:
        """Lee el mensaje con el motor y la voz que le corresponden."""
        rate, volumen, tono = self._ajustes()
        if secundaria:
            propio = self.voz_secundaria.preparar(
                self._gestor.motor.motor, tono, self._avisar)
            if propio is not None:
                self.voz_secundaria.sonando = True
                try:
                    self._leer_local(propio, texto, secundaria=True)
                finally:
                    self.voz_secundaria.sonando = False
                return
        # Secundaria con sus ajustes si el mensaje la pide y existe, si no la del mensaje o la base.
        ajuste = self.voz_secundaria.indice(self._gestor.voces, secundaria)
        self._gestor.aplicar_voz(self.voz_secundaria.voz if ajuste else voz)
        self._gestor.fijar_velocidad(ajuste[1] if ajuste else rate)
        self._gestor.fijar_volumen(ajuste[2] if ajuste else volumen)
        self.voz_secundaria.sonando = ajuste is not None
        if self._gestor.motor.motor == "elevenlabs":
            self._hablar_elevenlabs(texto, importante, ajuste is not None)
        else:
            self._leer_local(self._gestor.motor, texto,
                             secundaria=ajuste is not None)
        self.voz_secundaria.sonando = False

    def _leer_local(self, motor, texto: str, secundaria: bool) -> None:
        """Lee en un motor local y cae a Windows si falla.

        Un motor SAPI no tiene a dónde caer. Una purga (Alt+D) llega como
        lectura terminada, no como fallo."""
        try:
            sono = self._leer_frase(motor, texto)
        except Exception:
            if motor.motor == "sapi":
                raise
            self._caer_a_windows(texto, motor.motor, secundaria)
            return
        if not sono and motor.motor != "sapi":
            self._caer_a_windows(texto, motor.motor, secundaria)
        elif sono:
            caida = (self._caida_secundaria if secundaria
                     else self._caida_motor)
            caida.exito()

    def _caer_a_windows(self, texto: str, nombre: str,
                        secundaria: bool) -> None:
        caida = self._caida_secundaria if secundaria else self._caida_motor
        aviso = caida.fallo(_(motores.NOMBRES.get(nombre, nombre)))
        if aviso:
            self._avisar(aviso)
        respaldo = self._conseguir_respaldo(secundaria)
        if respaldo is not None:
            self._leer_frase(respaldo, texto)

    def _hablar_elevenlabs(self, texto: str, importante: bool,
                           secundaria: bool = False) -> None:
        """Lee con ElevenLabs y cae al respaldo según el estado de la sesión."""
        elegido = self._elegir_motor_elevenlabs(texto, importante, secundaria)
        if elegido is None:
            return
        if elegido is not self._gestor.motor:
            # Ya se avisó al elegir (tope) o no corresponde aviso (solo
            # importantes): el mensaje va derecho al respaldo.
            self._leer_frase(elegido, texto)
            return
        try:
            sono = self._leer_frase(elegido, texto)
        except elevenlabs.ElevenLabsError as exc:
            aviso = self.caida.fallo(exc)
            if aviso:
                self._avisar(aviso)
            respaldo = self._conseguir_respaldo(secundaria)
            if respaldo is not None:
                self._leer_frase(respaldo, texto)
            return
        if sono:
            # Un mensaje bien leído por ElevenLabs cierra la racha: el próximo
            # fallo vuelve a avisar.
            self.caida.exito()

    def _elegir_motor_elevenlabs(self, texto: str, importante: bool,
                                 secundaria: bool = False):
        """Motor para este mensaje: el principal o el respaldo de Windows."""
        usar, aviso = self.caida.elegir(
            importante, self._caracteres_elevenlabs(), len(texto))
        if aviso:
            self._avisar(aviso)
        return self._conseguir_respaldo(secundaria) if usar else self._gestor.motor

    def _caracteres_elevenlabs(self) -> int:
        try:
            return int(self._gestor.motor.caracteres_usados())
        except Exception:
            return 0

    def _conseguir_respaldo(self, secundaria=False):
        """Crea (una sola vez) la voz de Windows del respaldo, o None si falla."""
        rate, volumen, tono = self._ajustes()
        if secundaria:
            return self.voz_secundaria.conseguir_respaldo(self.respaldo.voz, tono)
        return self.respaldo.conseguir(rate, volumen, tono)

    def configurar_elevenlabs(self, tope, solo_importantes,
                              voz_respaldo) -> None:
        """Aplica los ajustes de ElevenLabs leídos de Preferencias, ya dentro
        del hilo del worker (el respaldo y sus ajustes le pertenecen)."""
        self.caida.configurar(tope, solo_importantes)
        self._elegir_voz_respaldo(voz_respaldo or "")

    def _elegir_voz_respaldo(self, voz) -> None:
        """Cambia la voz del respaldo sin recrearlo."""
        self.respaldo.cambiar_voz(voz)
        self.voz_secundaria.seguir_respaldo(voz)

    def configurar_voz_secundaria(self, voz, velocidad, volumen,
                                  respaldo, motor=None) -> None:
        """Aplica en caliente la voz secundaria, su respaldo y su motor."""
        _rate, _volumen, tono = self._ajustes()
        self.voz_secundaria.configurar(
            voz, velocidad, volumen, respaldo, self.respaldo.voz, tono, motor)

    def cerrar(self) -> None:
        """Cierra el respaldo y la voz secundaria."""
        self.respaldo.cerrar()
        self.voz_secundaria.cerrar()
