# Copyright (C) 2026 Miguel Ángel Insfrán Caballero. Condiciones adicionales en NOTICE.
# SPDX-License-Identifier: GPL-3.0-only
"""Motor de voz principal del worker: cuál está abierto y con qué voz y ajustes.

Prism no es seguro entre hilos: el motor se crea y se usa DENTRO del hilo del
worker. Por eso el gestor se crea y se usa en ese mismo hilo; la interfaz lee
`voces` solo después de `esperar_inicio`.
"""

from __future__ import annotations

from guyrapu.core import diagnostico
from guyrapu.voice import escala_voz
from guyrapu.voice import motores

logger = diagnostico.obtener_logger(__name__)


class GestorMotores:
    """Motor principal, su lista de voces y la voz base y la activa."""

    def __init__(self, fabrica_motor):
        self._fabrica = fabrica_motor
        self._motor = None
        self._voces: list[str] = []
        self._voz_base = 0        # índice de la voz del menú/preferencias
        self._voz_actual = None   # índice de la voz activa, o None antes de abrir

    @property
    def motor(self):
        return self._motor

    @property
    def voces(self) -> list[str]:
        return list(self._voces)

    @property
    def voz_base(self) -> int:
        return self._voz_base

    @property
    def voz_actual(self):
        return self._voz_actual

    def abrir(self, pedido, voz_guardada, velocidad, volumen, tono) -> None:
        """Crea el motor pedido (con respaldo a SAPI), carga las voces y aplica
        velocidad, volumen y tono. Lanza si no hay ningún motor con voces."""
        try:
            self._motor = self._fabrica(pedido)
        except motores.MotorNoDisponible as exc:
            if pedido == "sapi":
                raise
            logger.warning("El motor de voz %r no está disponible (%s); "
                           "se usa Windows SAPI 5.", pedido, exc)
            self._motor = self._fabrica("sapi")

        self._voces = list(self._motor.voces())
        if not self._voces:
            raise RuntimeError("El motor de voz no tiene voces instaladas.")

        idx = escala_voz.resolver_voz(voz_guardada, self._voces)
        if idx is None:
            if voz_guardada:
                # Voz guardada que ya no está instalada: avisar con la lista
                # numerada. Vacío significa «la primera» y no es un problema.
                nombres = "\n".join(f"  [{i}] {n}" for i, n in enumerate(self._voces))
                logger.warning("Voz '%s' no encontrada; se usa la primera "
                               "disponible.\n%s", voz_guardada, nombres)
            idx = 0
        self._voz_base = idx
        if self._motor.elegir_voz(idx):
            self._voz_actual = idx

        self.fijar_velocidad(velocidad)
        self.fijar_volumen(volumen)
        self.fijar_tono(tono)
        logger.info("Voz: %s | Velocidad: %d | Volumen: %d%% | Tono: %d",
                    self._voces[idx], velocidad, volumen, tono)

    def cambiar(self, motor, voz, velocidad, volumen, tono) -> None:
        """Reemplaza el motor activo dentro del hilo del worker.

        Prism exige un motor por hilo: el nuevo se crea aquí, se para y se
        cierra el anterior solo si el nuevo se pudo crear y tiene voces. Si la
        fábrica falla se conserva el motor viejo sin tocarlo, para no dejar al
        worker mudo."""
        try:
            nuevo = self._fabrica(motor)
        except motores.MotorNoDisponible as exc:
            logger.warning("El motor de voz %r no está disponible (%s); "
                           "se conserva %s.", motor, exc, self._activo())
            return
        voces = list(nuevo.voces())
        if not voces:
            logger.warning("El motor de voz %r no tiene voces; se conserva %s.",
                           motor, self._activo())
            nuevo.cerrar()
            return
        if self._motor is not None:
            self._motor.parar()
            self._motor.cerrar()
        self._motor = nuevo
        self._voces = voces
        idx = escala_voz.resolver_voz(voz, voces)
        if idx is None:
            idx = 0
        self._voz_base = idx
        self._voz_actual = None
        if self._motor.elegir_voz(idx):
            self._voz_actual = idx
        self.fijar_velocidad(velocidad)
        self.fijar_volumen(volumen)
        self.fijar_tono(tono)
        logger.info("Motor de voz: %s | Voz: %s", motor, self._voces[idx])

    def cambiar_voz_base(self, val) -> None:
        idx = escala_voz.resolver_voz(val, self._voces)
        if idx is None:
            logger.debug("Voz base %r no resuelta.", val)
            return
        self._voz_base = idx
        if idx != self._voz_actual and self._motor.elegir_voz(idx):
            self._voz_actual = idx
        logger.info("Voz base: %s", self._voces[idx])

    def aplicar_voz(self, voz) -> None:
        """Cambia la voz activa si el mensaje pide otra (o vuelve a la base)."""
        if voz is None:
            idx = self._voz_base
        else:
            idx = escala_voz.resolver_voz(voz, self._voces)
            if idx is None:
                idx = self._voz_base
        if idx != self._voz_actual and self._motor.elegir_voz(idx):
            self._voz_actual = idx

    def fijar_velocidad(self, pct) -> None:
        self._motor.fijar_velocidad(pct)

    def fijar_volumen(self, pct) -> None:
        self._motor.fijar_volumen(pct)

    def fijar_tono(self, pct) -> None:
        self._motor.fijar_tono(pct)

    def cerrar(self) -> None:
        if self._motor is not None:
            self._motor.cerrar()

    def _activo(self) -> str:
        """Nombre del motor activo, para los avisos de cambio."""
        return self._motor.motor if self._motor is not None else ""
