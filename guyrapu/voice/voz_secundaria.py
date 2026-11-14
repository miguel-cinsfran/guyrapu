# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""La voz secundaria por evento: su motor, su voz, sus ajustes y su respaldo.

`VozSecundaria` guarda la voz de los eventos en modo secundaria, con su
velocidad y su volumen, y es dueña de su instancia de `Respaldo` para cuando
un motor cae a Windows. Si se le da otro motor, abre y usa un `GestorMotores`
propio; si no, usa el principal. El worker le pasa los valores y el motor
principal; la clase no lee atributos del worker.
"""

from __future__ import annotations

from guyrapu.core import diagnostico
from guyrapu.core.idioma import _
from guyrapu.core.ini_tipado import a_decimal, a_entero
from guyrapu.voice import escala_voz
from guyrapu.voice import gestor_motores
from guyrapu.voice import motores
from guyrapu.voice.respaldo_windows import Respaldo

logger = diagnostico.obtener_logger(__name__)


class VozSecundaria:
    """Voz, velocidad, volumen y respaldo de los eventos secundarios."""

    def __init__(self, fabrica_motor, config, tono=50):
        self.voz = config.get("voz_secundaria") or ""
        self.motor = config.get("motor_secundaria") or ""
        self.velocidad = escala_voz.ajustar_velocidad(
            a_entero(config.get("velocidad_secundaria"),
                     escala_voz.VELOCIDAD_NORMAL), 0)
        self.volumen = max(0, min(100, int(round(
            a_decimal(config.get("volumen_secundaria"), 1.0) * 100))))
        self.tono = max(0, min(100, a_entero(tono, 50)))
        self.sonando = False
        self._fabrica_motor = fabrica_motor
        self._gestor = None
        self._respaldo_propio = config.get("voz_respaldo_secundaria") or ""
        self._respaldo = Respaldo(fabrica_motor, self._respaldo_propio)

    def preparar(self, principal, tono, avisar):
        """Abre (una sola vez) el gestor propio si el motor es otro.

        Devuelve el motor secundario, o None para que el mensaje siga con el
        motor principal. `abrir` ya cae a SAPI si el motor pedido no está."""
        if not self.motor or self.motor == principal:
            return None
        if self._gestor is None and not self._abrir_gestor(tono, avisar):
            return None
        self._aplicar(tono)
        return self._gestor.motor

    def _abrir_gestor(self, tono, avisar) -> bool:
        gestor = gestor_motores.GestorMotores(self._fabrica_motor)
        try:
            gestor.abrir(self.motor, self.voz, self.velocidad,
                         self.volumen, tono)
        except Exception as exc:
            logger.warning(
                "La voz secundaria no pudo abrir %s (%s); se usa el "
                "motor principal.", self.motor, exc)
            gestor.cerrar()
            return False
        self._gestor = gestor
        self._avisar_si_cayo(avisar)
        return True

    def _avisar_si_cayo(self, avisar) -> None:
        if self._gestor.motor.motor == self.motor:
            return
        avisar(_("{nombre} no está disponible: la voz secundaria usa "
                 "la voz de Windows.").format(
            nombre=_(motores.NOMBRES.get(self.motor, self.motor))))

    def _aplicar(self, tono) -> None:
        self._gestor.aplicar_voz(self.voz)
        self._gestor.fijar_velocidad(self.velocidad)
        self._gestor.fijar_volumen(self.volumen)
        self._gestor.fijar_tono(tono)

    def indice(self, voces, secundaria):
        """Índice, velocidad y volumen si el mensaje pide la secundaria.

        Devuelve None para que el mensaje use la principal. También devuelve
        None si la voz secundaria está vacía o no existe en `voces`."""
        if not secundaria:
            return None
        idx = escala_voz.resolver_voz(self.voz, voces)
        if idx is None:
            return None
        return idx, self.velocidad, self.volumen

    def conseguir_respaldo(self, voz_principal="", tono=None):
        """Devuelve el motor de Windows de la secundaria, o None si falla."""
        if tono is not None:
            self.tono = max(0, min(100, a_entero(tono, self.tono)))
        if not self._respaldo_propio:
            self._respaldo.cambiar_voz(voz_principal)
        return self._respaldo.conseguir(
            self.velocidad, self.volumen, self.tono)

    def seguir_respaldo(self, voz) -> None:
        """Sigue la voz de respaldo principal si no tiene una propia."""
        if not self._respaldo_propio:
            self._respaldo.cambiar_voz(voz)

    def configurar(self, voz, velocidad, volumen, respaldo,
                   voz_principal="", tono=None, motor=None) -> None:
        """Aplica en caliente la voz, la velocidad, el volumen y el respaldo."""
        self.voz = voz or ""
        self.velocidad = escala_voz.ajustar_velocidad(
            a_entero(velocidad, self.velocidad), 0)
        self.volumen = max(0, min(100, int(round(
            a_decimal(volumen, self.volumen / 100.0) * 100))))
        if tono is not None:
            self.tono = max(0, min(100, a_entero(tono, self.tono)))
        self._cambiar_motor(motor)
        self._ajustar_respaldo(respaldo, voz_principal)

    def _cambiar_motor(self, motor) -> None:
        if motor is not None and motor != self.motor:
            self._cerrar_gestor()
            self.motor = motor

    def _ajustar_respaldo(self, respaldo, voz_principal) -> None:
        self._respaldo_propio = respaldo or ""
        self._respaldo.cambiar_voz(self._respaldo_propio or voz_principal)
        self._respaldo.fijar_ajustes(
            self.velocidad, self.volumen, self.tono)

    def cerrar(self) -> None:
        """Cierra el respaldo y el gestor propio de la secundaria."""
        self._respaldo.cerrar()
        self._cerrar_gestor()

    def _cerrar_gestor(self) -> None:
        if self._gestor is not None:
            self._gestor.cerrar()
            self._gestor = None
